"""Deterministic, multilingual anonymizer using ICU transliteration.

Processing flow:
1. Normalize Unicode (NFC) to ensure precomposed characters.
2. Transliterate full text to Latin-ASCII-lowercase via ICU.
3. Build character-level position mapping (transliterated → original).
4. Detect PII on transliterated text:
   a. Exact user-dictionary matching (token-level).
   b. Regex patterns (emails, phones, numeric IDs).
5. Map detected spans back to original text.
6. Replace PII in original text with deterministic placeholders.
7. Return anonymized text + structured artifacts.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar

import icu  # type: ignore[import-untyped]

from app.anonymization.base import BaseAnonymizer
from app.anonymization.exceptions import AnonymizationError
from app.anonymization.models import AnonymizationResult, Artifact
from app.logging.logger import Log


@dataclass
class _Detection:
    """A detected PII span in the transliterated text."""

    entity_type: str
    trans_start: int
    trans_end: int


class Anonymizer(BaseAnonymizer):
    """Deterministic anonymizer — no AI, no heuristic guessing.

    Supports 10 alphabet-based languages via ICU transliteration:
    English, Ukrainian, Polish, German, French, Spanish,
    Italian, Portuguese, Czech, Romanian.
    """

    _ICU_TRANSFORM: ClassVar[str] = "Any-Latin; Latin-ASCII; Lower"

    _EMAIL_RE: ClassVar[re.Pattern[str]] = re.compile(
        r"[\w.\-+]+@[\w.\-]+\.\w{2,}",
    )
    _PHONE_RE: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<!\w)"
        r"\+?\d[\d\s\-().]{5,18}\d"
        r"(?!\w)",
    )
    _ID_RE: ClassVar[re.Pattern[str]] = re.compile(
        r"\b\d{6,20}\b",
    )

    _REGEX_RULES: ClassVar[list[tuple[str, re.Pattern[str]]]] = [
        ("EMAIL", _EMAIL_RE),
        ("PHONE", _PHONE_RE),
        ("ID", _ID_RE),
    ]

    def __init__(self) -> None:
        self._transliterator: icu.Transliterator = icu.Transliterator.createInstance(
            self._ICU_TRANSFORM
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def anonymize(
        self,
        text: str,
        sensitive_words: list[str] | None = None,
    ) -> AnonymizationResult:
        """Replace PII in *text* with labeled placeholders.

        Args:
            text: Plain text (output from PDF extractor).
            sensitive_words: User-defined sensitive words (lowercase, space-separated
                             tokens already split by caller).

        Returns:
            AnonymizationResult with anonymized text, artifacts, and
            transliteration mapping.
        """
        try:
            return self._run(text, sensitive_words or [])
        except AnonymizationError:
            raise
        except Exception as exc:
            raise AnonymizationError(f"Anonymization failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    def _run(self, text: str, dictionary: list[str]) -> AnonymizationResult:
        if not text:
            return AnonymizationResult(anonymized_text="", artifacts=[])

        # Step 1 — Unicode normalization (NFC: precomposed form).
        # NFC ensures characters like ü stay as single codepoints so
        # per-character ICU transliteration handles them correctly.
        normalized = unicodedata.normalize("NFC", text)

        # Step 2 — Transliterate + build char mapping
        transliterated, trans_to_orig = self._transliterate_with_mapping(normalized)

        Log.debug(
            f"Transliterated {len(normalized)} chars → {len(transliterated)} chars"
        )

        # Step 3 — Detect PII in transliterated text
        detections: list[_Detection] = []
        detections.extend(self._detect_dictionary(transliterated, set(dictionary)))
        detections.extend(self._detect_regex(transliterated))

        if not detections:
            return AnonymizationResult(
                anonymized_text=normalized,
                artifacts=[],
                transliteration_mapping=trans_to_orig,
            )

        # Step 4 — Map to original positions, merge overlapping
        original_spans = self._map_to_original(detections, trans_to_orig, normalized)

        # Step 5 — Replace + generate artifacts
        result = self._replace(normalized, original_spans)
        result.transliteration_mapping = trans_to_orig

        Log.info(f"Anonymized: {len(result.artifacts)} PII entities replaced")
        return result

    # ------------------------------------------------------------------
    # Step 2 — Transliteration with char mapping
    # ------------------------------------------------------------------

    def _transliterate_with_mapping(self, text: str) -> tuple[str, list[int]]:
        """Transliterate *text* character-by-character via ICU.

        Returns:
            (transliterated_text, trans_to_orig) where trans_to_orig[j]
            is the index in *text* that produced transliterated char j.
        """
        parts: list[str] = []
        trans_to_orig: list[int] = []

        for orig_idx, ch in enumerate(text):
            t = self._transliterator.transliterate(ch)
            parts.append(t)
            trans_to_orig.extend([orig_idx] * len(t))

        return "".join(parts), trans_to_orig

    # ------------------------------------------------------------------
    # Step 3a — Dictionary detection
    # ------------------------------------------------------------------

    def _detect_dictionary(
        self,
        transliterated: str,
        dictionary: set[str],
    ) -> list[_Detection]:
        """Find exact user-dictionary matches in tokenized transliterated text."""
        if not dictionary:
            return []

        detections: list[_Detection] = []
        for word in dictionary:
            if not word:
                continue
            start = 0
            while True:
                idx = transliterated.find(word, start)
                if idx == -1:
                    break
                end = idx + len(word)
                # Ensure word boundaries (not part of a larger word)
                before_ok = idx == 0 or not transliterated[idx - 1].isalnum()
                after_ok = end == len(transliterated) or not transliterated[end].isalnum()
                if before_ok and after_ok:
                    detections.append(_Detection("PERSON", idx, end))
                start = idx + 1

        return detections

    # ------------------------------------------------------------------
    # Step 3b — Regex detection
    # ------------------------------------------------------------------

    def _detect_regex(self, transliterated: str) -> list[_Detection]:
        """Find emails, phones, and numeric IDs via regex."""
        detections: list[_Detection] = []
        for entity_type, pattern in self._REGEX_RULES:
            for m in pattern.finditer(transliterated):
                detections.append(_Detection(entity_type, m.start(), m.end()))
        return detections

    # ------------------------------------------------------------------
    # Step 4 — Map spans to original text + merge overlaps
    # ------------------------------------------------------------------

    def _map_to_original(
        self,
        detections: list[_Detection],
        trans_to_orig: list[int],
        original: str,
    ) -> list[tuple[str, int, int]]:
        """Map transliterated spans to original-text spans, merge overlaps.

        Returns sorted, non-overlapping (entity_type, orig_start, orig_end).
        """
        raw: list[tuple[str, int, int]] = []

        for d in detections:
            if d.trans_start >= len(trans_to_orig) or d.trans_end < 1:
                continue
            orig_start = trans_to_orig[d.trans_start]
            # trans_end is exclusive; map the last inclusive char
            orig_end_idx = min(d.trans_end - 1, len(trans_to_orig) - 1)
            orig_end_char = trans_to_orig[orig_end_idx]
            # Make orig_end exclusive (one past the last original char)
            orig_end = orig_end_char + 1
            # Extend to cover the full original character span
            while orig_end < len(original) and orig_end < len(original) and (
                d.trans_end < len(trans_to_orig)
                and orig_end <= trans_to_orig[d.trans_end - 1]
            ):
                orig_end += 1

            raw.append((d.entity_type, orig_start, orig_end))

        # Sort by start, then by end descending (prefer longer spans)
        raw.sort(key=lambda x: (x[1], -x[2]))

        # Merge overlapping spans — keep the longer / first-seen type
        merged: list[tuple[str, int, int]] = []
        for entity_type, start, end in raw:
            if merged and start < merged[-1][2]:
                # Overlapping — extend if longer
                prev_type, prev_start, prev_end = merged[-1]
                merged[-1] = (prev_type, prev_start, max(prev_end, end))
            else:
                merged.append((entity_type, start, end))

        return merged

    # ------------------------------------------------------------------
    # Step 5 — Replacement + artifact generation
    # ------------------------------------------------------------------

    def _replace(
        self,
        original: str,
        spans: list[tuple[str, int, int]],
    ) -> AnonymizationResult:
        """Replace PII in *original* with deterministic placeholders.

        Same PII value (case-insensitive) → same placeholder everywhere.
        """
        counters: dict[str, int] = {}
        entity_map: dict[tuple[str, str], str] = {}

        # First pass — assign unique placeholders per (type, value)
        for entity_type, start, end in spans:
            value = original[start:end].strip().lower()
            key = (entity_type, value)
            if key not in entity_map:
                counter = counters.get(entity_type, 0) + 1
                counters[entity_type] = counter
                entity_map[key] = f"{entity_type}_{counter}"

        # Second pass — replace in reverse order to preserve positions
        artifacts: list[Artifact] = []
        result = original

        for entity_type, start, end in reversed(spans):
            original_value = original[start:end]
            key = (entity_type, original_value.strip().lower())
            placeholder = entity_map[key]
            result = result[:start] + placeholder + result[end:]
            artifacts.append(
                Artifact(
                    type=entity_type,
                    original=original_value,
                    replacement=placeholder,
                )
            )

        # Reverse so artifacts appear in text order
        artifacts.reverse()

        return AnonymizationResult(anonymized_text=result, artifacts=artifacts)
