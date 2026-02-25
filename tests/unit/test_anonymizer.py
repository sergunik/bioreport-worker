from unittest.mock import patch

import pytest

from app.anonymization.anonymizer import Anonymizer
from app.anonymization.exceptions import AnonymizationError


class TestAnonymizeEmptyAndTrivial:
    def test_empty_text_returns_empty(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("")
        assert result.anonymized_text == ""
        assert result.artifacts == []

    def test_no_pii_returns_text_unchanged(self) -> None:
        anonymizer = Anonymizer()
        text = "The cat sat on the mat."
        result = anonymizer.anonymize(text)
        assert result.anonymized_text == text
        assert result.artifacts == []

    def test_no_pii_returns_transliteration_mapping(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("hello")
        assert len(result.transliteration_mapping) > 0


class TestDictionaryDetection:
    def test_replaces_single_dictionary_word(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Patient ivan visited.", sensitive_words=["ivan"])
        assert "ivan" not in result.anonymized_text.lower()
        assert "PERSON_1" in result.anonymized_text
        assert len(result.artifacts) == 1
        assert result.artifacts[0].type == "PERSON"

    def test_replaces_multiple_dictionary_words(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Patient Ivan Petrov visited.",
            sensitive_words=["ivan", "petrov"],
        )
        assert "ivan" not in result.anonymized_text.lower()
        assert "petrov" not in result.anonymized_text.lower()
        assert len(result.artifacts) == 2

    def test_same_word_same_placeholder(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Ivan said hello. Ivan left.",
            sensitive_words=["ivan"],
        )
        # Both occurrences of Ivan should get the same placeholder
        person_artifacts = [a for a in result.artifacts if a.type == "PERSON"]
        replacements = {a.replacement for a in person_artifacts}
        assert len(replacements) == 1
        assert "PERSON_1" in replacements

    def test_dictionary_words_are_case_insensitive(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Patient IVAN visited.",
            sensitive_words=["ivan"],
        )
        assert "IVAN" not in result.anonymized_text
        assert "PERSON_1" in result.anonymized_text

    def test_respects_word_boundaries(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "The ivanovich came.",
            sensitive_words=["ivan"],
        )
        # "ivan" inside "ivanovich" should NOT match (word boundary check)
        assert all(a.original.lower() != "ivan" for a in result.artifacts)

    def test_empty_dictionary_no_detection(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Patient Ivan visited.", sensitive_words=[])
        # Only regex matches, not dictionary
        assert all(a.type != "PERSON" for a in result.artifacts)

    def test_none_dictionary_no_detection(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Patient Ivan visited.")
        assert all(a.type != "PERSON" for a in result.artifacts)


class TestCyrillicTransliteration:
    def test_replaces_cyrillic_name_from_dictionary(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Клієнт: Іван Петренко",
            sensitive_words=["ivan", "petrenko"],
        )
        assert "Іван" not in result.anonymized_text
        assert "Петренко" not in result.anonymized_text
        assert any(a.type == "PERSON" for a in result.artifacts)

    def test_replaces_ukrainian_text(self) -> None:
        anonymizer = Anonymizer()
        # ICU transliterates Шевченко -> "sevcenko" (Ш->s, ч->c)
        result = anonymizer.anonymize(
            "Пацієнт Олена Шевченко",
            sensitive_words=["olena", "sevcenko"],
        )
        assert "Олена" not in result.anonymized_text
        assert "Шевченко" not in result.anonymized_text

    def test_replaces_german_diacritics(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Patient Müller aus München",
            sensitive_words=["muller"],
        )
        assert "Müller" not in result.anonymized_text
        assert "PERSON_1" in result.anonymized_text

    def test_replaces_french_accents(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Patient René Lefèvre",
            sensitive_words=["rene", "lefevre"],
        )
        assert "René" not in result.anonymized_text
        assert "Lefèvre" not in result.anonymized_text

    def test_replaces_polish_characters(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Pacjent Łukasz Wójcik",
            sensitive_words=["lukasz", "wojcik"],
        )
        assert "Łukasz" not in result.anonymized_text
        assert "Wójcik" not in result.anonymized_text

    def test_replaces_czech_characters(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Pacient Jiří Dvořák",
            sensitive_words=["jiri", "dvorak"],
        )
        assert "Jiří" not in result.anonymized_text
        assert "Dvořák" not in result.anonymized_text

    def test_replaces_romanian_characters(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Pacientul Ștefan Ionescu",
            sensitive_words=["stefan", "ionescu"],
        )
        assert "Ștefan" not in result.anonymized_text
        assert "Ionescu" not in result.anonymized_text

    def test_replaces_spanish_characters(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Paciente José García",
            sensitive_words=["jose", "garcia"],
        )
        assert "José" not in result.anonymized_text
        assert "García" not in result.anonymized_text

    def test_replaces_portuguese_characters(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Paciente João Gonçalves",
            sensitive_words=["joao", "goncalves"],
        )
        assert "João" not in result.anonymized_text
        assert "Gonçalves" not in result.anonymized_text

    def test_replaces_italian_characters(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Paziente è stato visitato",
            sensitive_words=["visitato"],
        )
        assert "visitato" not in result.anonymized_text


class TestEmailDetection:
    def test_detects_simple_email(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Contact user@example.com for details.")
        assert "user@example.com" not in result.anonymized_text
        assert any(a.type == "EMAIL" for a in result.artifacts)
        assert "EMAIL_1" in result.anonymized_text

    def test_detects_email_with_dots(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Email: first.last@sub.domain.co.uk")
        assert "first.last@sub.domain.co.uk" not in result.anonymized_text
        assert any(a.type == "EMAIL" for a in result.artifacts)

    def test_detects_email_with_plus(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Email: user+tag@example.com")
        assert "user+tag@example.com" not in result.anonymized_text

    def test_detects_multiple_emails(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Send to a@b.com and c@d.com")
        email_artifacts = [a for a in result.artifacts if a.type == "EMAIL"]
        assert len(email_artifacts) == 2


class TestPhoneDetection:
    def test_detects_international_phone(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Call +380 44 123 4567")
        assert "+380 44 123 4567" not in result.anonymized_text
        assert any(a.type == "PHONE" for a in result.artifacts)

    def test_detects_us_phone(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Call +1-555-123-4567")
        assert "+1-555-123-4567" not in result.anonymized_text
        assert any(a.type == "PHONE" for a in result.artifacts)

    def test_detects_phone_with_parens(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Call (044) 123-45-67")
        assert "(044) 123-45-67" not in result.anonymized_text

    def test_detects_compact_phone(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Tel: 0441234567")
        assert "0441234567" not in result.anonymized_text


class TestIdDetection:
    def test_detects_numeric_id(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Passport: 12345678")
        assert "12345678" not in result.anonymized_text
        assert any(a.type in ("ID", "PHONE") for a in result.artifacts)

    def test_does_not_match_short_numbers(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Room 42 on floor 3.")
        # Short numbers should not be detected as IDs
        id_artifacts = [a for a in result.artifacts if a.type == "ID"]
        assert len(id_artifacts) == 0


class TestMixedDetection:
    def test_detects_dictionary_and_email(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Ivan sent email to ivan@example.com",
            sensitive_words=["ivan"],
        )
        assert "Ivan" not in result.anonymized_text
        assert "ivan@example.com" not in result.anonymized_text
        types = {a.type for a in result.artifacts}
        assert "PERSON" in types
        assert "EMAIL" in types

    def test_detects_dictionary_and_phone(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Іван Петренко, тел: +380 44 123 4567",
            sensitive_words=["ivan", "petrenko"],
        )
        assert "Іван" not in result.anonymized_text
        assert "Петренко" not in result.anonymized_text
        assert "+380 44 123 4567" not in result.anonymized_text


class TestReplacementConsistency:
    def test_unique_counters_per_type(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Ivan at ivan@test.com, Petrov at petrov@test.com",
            sensitive_words=["ivan", "petrov"],
        )
        person_replacements = {a.replacement for a in result.artifacts if a.type == "PERSON"}
        email_replacements = {a.replacement for a in result.artifacts if a.type == "EMAIL"}
        # Each type should have its own counter sequence
        assert "PERSON_1" in person_replacements
        assert "PERSON_2" in person_replacements
        assert "EMAIL_1" in email_replacements
        assert "EMAIL_2" in email_replacements

    def test_artifacts_in_text_order(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Ivan wrote to Petrov",
            sensitive_words=["ivan", "petrov"],
        )
        if len(result.artifacts) >= 2:
            # First artifact should be the one appearing earlier in text
            first_pos = result.anonymized_text.find(result.artifacts[0].replacement)
            second_pos = result.anonymized_text.find(result.artifacts[1].replacement)
            assert first_pos <= second_pos


class TestTransliterationMapping:
    def test_mapping_length_matches_transliterated_text(self) -> None:
        anonymizer = Anonymizer()
        source_text = "Hello world"
        result = anonymizer.anonymize(source_text)
        transliterated = anonymizer._transliterator.transliterate(source_text)
        assert len(result.transliteration_mapping) == len(transliterated)

    def test_mapping_values_within_original_range(self) -> None:
        anonymizer = Anonymizer()
        text = "Клієнт: Іван"
        result = anonymizer.anonymize(text, sensitive_words=["ivan"])
        for idx in result.transliteration_mapping:
            assert 0 <= idx < len(text)

    def test_mapping_is_monotonically_nondecreasing(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Hello Мир world")
        mapping = result.transliteration_mapping
        for i in range(1, len(mapping)):
            assert mapping[i] >= mapping[i - 1]

    def test_mapping_length_matches_full_transliteration_for_context_case(self) -> None:
        anonymizer = Anonymizer()
        source_text = "Євген"
        result = anonymizer.anonymize(source_text)
        transliterated = anonymizer._transliterator.transliterate(source_text)
        assert len(result.transliteration_mapping) == len(transliterated)


class TestContextAwareTransliteration:
    def test_dictionary_match_uses_full_string_transliteration(self) -> None:
        anonymizer = Anonymizer()
        class ContextAwareStubTransliterator:
            def transliterate(self, text: str) -> str:
                if text == "AB":
                    return "cb"
                if text == "A":
                    return "a"
                if text == "B":
                    return "b"
                return text.lower()

        anonymizer._transliterator = ContextAwareStubTransliterator()  # type: ignore[assignment]

        result = anonymizer.anonymize("AB", sensitive_words=["cb"])
        person_artifacts = [artifact for artifact in result.artifacts if artifact.type == "PERSON"]
        assert len(person_artifacts) == 1
        assert person_artifacts[0].original == "AB"

    def test_ukrainian_context_sensitive_letters_regression(self) -> None:
        anonymizer = Anonymizer()
        candidate_words = [
            "Євген",
            "єнот",
            "Юрій",
            "юнак",
            "Яна",
            "ящірка",
            "Підємець",
        ]

        selected_word: str | None = None
        selected_transliteration: str | None = None
        for word in candidate_words:
            full_transliterated = anonymizer._transliterator.transliterate(word)
            per_char_transliterated = "".join(
                anonymizer._transliterator.transliterate(ch) for ch in word
            )
            if full_transliterated != per_char_transliterated:
                selected_word = word
                selected_transliteration = full_transliterated
                break

        if selected_word is None or selected_transliteration is None:
            pytest.skip("Current ICU build shows no context difference for selected words")

        result = anonymizer.anonymize(
            f"Пацієнт {selected_word}",
            sensitive_words=[selected_transliteration],
        )
        person_artifacts = [artifact for artifact in result.artifacts if artifact.type == "PERSON"]
        assert len(person_artifacts) == 1
        assert person_artifacts[0].original == selected_word

    def test_ukrainian_name_marian_with_apostrophe(self) -> None:
        anonymizer = Anonymizer()
        marian = "\u041c\u0430\u0440'\u044f\u043d"
        source_text = f"Пацієнт {marian}"
        dictionary_word = anonymizer._transliterator.transliterate(marian)

        result = anonymizer.anonymize(source_text, sensitive_words=[dictionary_word])

        person_artifacts = [artifact for artifact in result.artifacts if artifact.type == "PERSON"]
        assert len(person_artifacts) == 1
        assert person_artifacts[0].original == marian


class TestArtifactFields:
    def test_artifact_has_type_original_replacement(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Contact user@example.com")
        assert len(result.artifacts) >= 1
        artifact = result.artifacts[0]
        assert artifact.type
        assert artifact.original
        assert artifact.replacement

    def test_original_is_from_source_text(self) -> None:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Клієнт Іван",
            sensitive_words=["ivan"],
        )
        person_artifacts = [a for a in result.artifacts if a.type == "PERSON"]
        assert len(person_artifacts) >= 1
        # The original should be from the original text (Cyrillic), not transliterated
        assert person_artifacts[0].original == "Іван"


class TestErrorHandling:
    def test_wraps_unexpected_error_as_anonymization_error(self) -> None:
        anonymizer = Anonymizer()
        with patch.object(
            anonymizer, "_transliterate_with_mapping", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(AnonymizationError, match="Anonymization failed"):
                anonymizer.anonymize("some text", sensitive_words=["test"])

    def test_does_not_double_wrap_anonymization_error(self) -> None:
        anonymizer = Anonymizer()
        with patch.object(
            anonymizer,
            "_transliterate_with_mapping",
            side_effect=AnonymizationError("original error"),
        ):
            with pytest.raises(AnonymizationError, match="original error"):
                anonymizer.anonymize("text")


class TestUnicodeNormalization:
    def test_normalizes_nfc(self) -> None:
        anonymizer = Anonymizer()
        # U+00E9 (é precomposed) vs U+0065 U+0301 (e + combining accent)
        # NFC composes decomposed form back, so both should match "rene"
        text_precomposed = "Ren\u00e9"
        text_decomposed = "Rene\u0301"
        result1 = anonymizer.anonymize(text_precomposed, sensitive_words=["rene"])
        result2 = anonymizer.anonymize(text_decomposed, sensitive_words=["rene"])
        # Both should detect and replace "René"
        assert any(a.type == "PERSON" for a in result1.artifacts)
        assert any(a.type == "PERSON" for a in result2.artifacts)


class TestMedicalStaffNames:
    def test_replaces_doctor_name_from_dictionary(self) -> None:
        """Per plan: even medical staff names must be replaced."""
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(
            "Client: Ivan Petrov\nReferred by: Dr. Ivanov",
            sensitive_words=["ivan", "petrov", "ivanov"],
        )
        assert "Ivan" not in result.anonymized_text
        assert "Petrov" not in result.anonymized_text
        assert "Ivanov" not in result.anonymized_text
        assert "Dr." in result.anonymized_text  # Title preserved
