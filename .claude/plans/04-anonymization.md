# Anonymizer Module – Implementation Plan

## 1. Goal

Build a deterministic, multilingual anonymization module that:

- Removes all identifiable PII before sending documents to a public AI API.
- Works without LLM-based detection.
- Is predictable, testable, and extensible.
- Is designed for B2C usage.
- Targets near-GDPR-level safety (without formal certification at this stage).

The system must guarantee:
- All user-defined PII is removed.
- All regex-detectable PII is removed.
- The final output contains no direct personal identifiers.
- Architecture allows future extension (fuzzy, morphology, AI-token mode).


## 2. Final Objective

Given a document:

1. Extract text from PDF (already implemented).
2. Transliterate full text into Latin.
3. Detect PII using:
   - Exact user dictionary
   - Regex patterns
4. Replace PII in the original text (not the transliterated one).
5. Produce:
   - An anonymized version
   - Internal structured metadata (future-ready)
6. Forward anonymized text to public AI API.

No raw PII leaves the system.



## 3. Multilingual Scope (MVP)

The system must support 10 widely used alphabet-based languages (no ideographic scripts at this stage):

- English
- Ukrainian
- Polish
- German
- French
- Spanish
- Italian
- Portuguese
- Czech
- Romanian

All processing must be language-agnostic and based on deterministic transliteration.


## 4. Core Architectural Principles

- Deterministic logic only.
- No AI-based PII detection.
- No heuristic guessing beyond defined rules.
- Clean, modular design.
- Extensible pipeline.
- Position-safe replacements.
- Unicode normalization required.

Code cleanliness and modular separation are critical.

Illustrative structure:

```

class Anonymizer:
def **init**(self, profile):
...
def transliterate()
def tokenize()
def detect_sensitive()
def replace()
def generate_artifacts()

```

Each method must be isolated, testable, and independently extendable.


## 5. High-Level Processing Flow

### STEP 1 – Input

- Receive plain text extracted from PDF.
- Validate encoding (UTF-8).
- Normalize Unicode (NFKD or equivalent).


### STEP 2 – Transliteration (Full Text)

Purpose:
- Normalize all supported languages into Latin ASCII
- use ICU Transliteration (via PyICU)
- Remove diacritics.
- Convert to lowercase.

Flow:
```

ICU:
Any-Latin;
Latin-ASCII;
Lower();

```

Example:

Original:
```

Клієнт: Іван Петренко
München Labor

```

Transliterated:
```

kliient: ivan petrenko
munchen labor

```

Requirements:
- Store mapping: original_char_index → transliterated_char_index in DB (uploaded_documents table).
- Preserve ability to map token spans back to original text.

This mapping is mandatory.


### STEP 3 – Tokenization

Tokenization rules (MVP):

- Split by whitespace.
- trim punctuation.
- Normalize to lowercase.
- Preserve token positions.

Example:

```

"Client: Ivan-Petrov"

```

Tokens:
```

["client", "ivan-petrov"]

```

Position tracking is required.



### STEP 4 – PII Detection

Detection runs on transliterated text only.

#### 4.1 Exact User Dictionary Matching

User profile contains:
- Space-separated words
- Stored in DB (accounts table, sensitive_words field)
- Lowercase

If token matches exactly → mark as PII.

All occurrences must be replaced.

Goal:
Remove every dictionary-defined name everywhere (including doctors, nurses, etc.).


#### 4.2 Regex Detection

Implement deterministic regex rules for:

- Emails
- Phone numbers
- Basic numeric IDs (passport, national ID, etc.)

Examples:

- `[\w\.-]+@[\w\.-]+\.\w+`
- International phone formats

All regex matches must be replaced.


#### 4.3 Fuzzy Matching (Stub for MVP)

Not implemented yet.

Planned parameters:

- Levenshtein distance ≤ 1
- AND token length > 4
- AND not matching regex numeric patterns

Structure must allow easy insertion later.


#### 4.4 Morphology (Stub for MVP)

Planned logic:

- starts_with(user_word)
- AND suffix_length ≤ 3

Not implemented in MVP.
Pipeline must allow plugging in this rule later.


## 6. Replacement Strategy

Replacement must occur in original text using stored position mapping.

Replacement format:

- Each unique detected entity → PERSON_1
- Next → PERSON_2
- Emails → EMAIL_1
- Phones → PHONE_1

Consistency rule:
Same token → same placeholder everywhere.

Example:

Original:
```

Client: Ivan Petrov
Referred by: Dr. Ivanov

```

Output:
```

Client: PERSON_1 PERSON_2
Referred by: Dr. PERSON_3

```

Even medical staff names must be replaced.


## 7. Artifact Generation

System must produce:

- anonymized_text
- anonymized_artifacts (replaced entities with original values, types, and positions)

Propper logging is required.


## 8. AI Forwarding (Stub)

Future step:

- Token-based segmentation
- Safe forwarding to public AI API

For MVP:
- Only send anonymized full text.

No PII must remain.


## 9. Non-Goals (MVP)

- No AI-based detection.
- No medical whitelist.
- No entropy heuristics.
- No probabilistic scoring.
- No GDPR certification yet.
- No ideographic language support.


## 10. Extensibility Requirements

Architecture must allow adding:

- Fuzzy matching
- Morphological rules
- Confidence scoring
- Strict mode
- Token-based AI PII detection
- Logging & audit layer

Without refactoring core structure.


## 11. Acceptance Criteria (AC)

### AC-1
Given a document containing user dictionary words,
All occurrences must be replaced.

### AC-2
Given emails and phone numbers,
All must be replaced via regex.

### AC-3
Transliteration must normalize:
- Diacritics
- Mixed case
- Unicode variants

### AC-4
Replacement must occur in original text, not transliterated version.

### AC-5
No raw PII may appear in final output.

### AC-6
Mapping between original and transliterated indices must be preserved.

### AC-7
System must support at least 10 alphabet-based languages listed above.

### AC-8
Pipeline must remain modular and extendable.


## 12. Definition of Done

- Module is deterministic.
- Fully unit tested.
- Position-safe replacement implemented.
- Clean, readable architecture.
- No AI used for PII detection.
- Multilingual support working.
- All AC satisfied.
- Documentation complete.
- Linting and code quality checks passed (via `make lint`).
- Tests passing (via `make test`).



## 13. Core Philosophy

Simplicity first.
Determinism over intelligence.
Control over automation.
Privacy before convenience.
Extensibility without complexity.
Dockerized, testable, and maintainable codebase.
