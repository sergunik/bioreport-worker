# Task 06 — Medical Data Normalization (Product Specification)

## 1. Problem

After PDF extraction and anonymization, the system contains plain anonymized medical text.
This text must be transformed into a **structured, machine-readable JSON document** containing:

* Person information (anonymized)
* Date of diagnostic
* A list of medical markers
* Each marker normalized into a strict domain format

The result must be suitable for database persistence and further domain processing.

---

## 2. Goal

Transform anonymized medical text into a strictly validated JSON object:

* Extract **all laboratory markers present in the text**
* Normalize their values into a structured format
* Enforce domain invariants
* Guarantee deterministic-like structure
* Fail safely on structural violations

This step is a **domain normalization layer**, not an AI wrapper.

---

## 3. Scope

### In Scope

* Extraction of:

    * Person placeholder (e.g., `PERSON_1`)
    * Date of diagnostic (global document-level date)
    * Medical markers and their values
    * Reference ranges (if present)
* Normalization of marker values:

    * Numeric
    * Boolean
    * Text
* Validation of result structure (Step 5.5)
* Hard limit of 100 markers
* Debug logging of prompt (debug mode only)
* Fully provider-agnostic interface
* Configurable prompt template
* Configurable AI parameters (model, timeout, etc.)

---

### Out of Scope (MVP)

* Mapping to `standard_biomarkers`
* Status evaluation (high/low/normal)
* Deduplication
* Caching
* Token usage logging
* Fallback providers
* Chunking large documents
* Detection of missed markers
* Compliance audit trail

---

## 4. High-Level Behavior

### Input

Anonymized plain text from Step 4.

### Output

Strict JSON object.

### External Dependency

An AI provider is used internally, but externally the system exposes:

```python
normalization_result = normalizer.normalize(text)
```

No provider-specific details are exposed.

---

## 5. JSON Contract (Strict Output)

The result MUST be a valid JSON object matching this structure.

```json
{
  "person": {
    "name": "PERSON_1",
    "dob": "1990-01-01"
  },
  "diagnostic_date": "2025-01-10",
  "markers": [
    {
      "code": "HBA1C",
      "name": "Hemoglobin A1c",
      "value": {
        "type": "numeric",
        "number": 6.2,
        "unit": "%"
      },
      "reference_range": {
        "min": 4.0,
        "max": 5.6,
        "unit": "%"
      }
    }
  ]
}
```

---

## 6. Field Definitions

### person

* `name` — anonymized placeholder (e.g., `PERSON_1`)
* `dob` — ISO date string or `null`

System knows which PERSON_n belongs to the main user.

AI is also used to cross-check if additional real names were missed.

---

### diagnostic_date

* Global examination date
* ISO date string
* `null` if not present

---

### markers

Array of marker objects.

Maximum length: **100**

Each marker represents **one measurement**.

If the same marker appears multiple times in the document:

```
Glucose 5.1
Glucose 5.8
```

→ This is a **validation error** (violates single-value-per-marker invariant).

---

## 7. Marker Structure

### Required Fields

* `code` — non-empty short identifier
* `name` — full readable name
* `value` — polymorphic object

### Optional Fields

* `reference_range` — object or `null`

---

## 8. Value Model (Polymorphic)

`value.type` MUST be one of:

* `"numeric"`
* `"boolean"`
* `"text"`

---

### Numeric Example

```json
"value": {
  "type": "numeric",
  "number": 6.2,
  "unit": "%"
}
```

---

### Boolean Example

```json
"value": {
  "type": "boolean",
  "value": true
}
```

---

### Text Example

```json
"value": {
  "type": "text",
  "text": "Positive"
}
```

---

## 9. Reference Range

```json
"reference_range": {
  "min": 4.0,
  "max": 5.6,
  "unit": "%"
}
```

May be `null`.

---

## 10. Domain Invariants (Hard Rules)

Validation Step 5.5 MUST enforce:

1. Result must be valid JSON
2. Top-level object must contain:

    * `person`
    * `diagnostic_date`
    * `markers`
3. `markers` must be a list
4. `len(markers) <= 100`
5. Each marker must have:

    * non-empty `code`
    * non-empty `name`
    * valid `value`
6. `value.type` must be exactly one of:

    * numeric
    * boolean
    * text
7. Value cannot be multiple types simultaneously
8. Duplicate marker codes → validation failure
9. If parsing fails → immediate failure (no retry at this level)

---

## 11. Error Model

### AI Network Error

* Raise infrastructure-level failure
* Job retry mechanism handles retry

### Invalid JSON Response

* Immediate failure
* Logged
* No retry inside Step 5

### Validation Failure (Step 5.5)

Examples:

* > 100 markers
* Missing required fields
* Duplicate markers
* Invalid value type

→ Fail normalization step

---

## 12. Prompt Template

Prompt MUST:

* Be stored externally
* Support placeholders
* Be configurable
* Not hardcoded

Example placeholders:

* `{anonymized_text}`
* `{known_person_placeholder}`
* `{json_schema}`

The JSON schema template MUST also be externally configurable.

---

## 13. Configuration Requirements

All AI-related parameters must be configurable:

* model name
* timeout
* temperature
* rate limit (if enabled)
* prompt template path
* system prompt

No hardcoded API keys.
No hardcoded model names.

---

## 14. Logging Requirements

* Prompt must be logged in DEBUG mode only
* No token usage logging (MVP)
* No raw response persistence (MVP)

---

## 15. Non-Functional Requirements

* Clean code
* Small focused functions
* SRP (Single Responsibility Principle)
* Follow SOLID principles
* No business logic inside adapters
* Provider-agnostic interface
* Docker-friendly execution
* All commands executed inside container

---

## 16. Testing Requirements

Must include:

* Unit tests for:

    * Value validation
    * Marker validation
    * JSON parsing
    * Overflow (>100 markers)
    * Duplicate detection
* Integration tests for:

    * Full normalization pipeline
* Validation failure scenarios
* Network failure simulation

Before completion:

```
make lint
make test
make int-test
```

All must pass.

All commands executed inside Docker container.

---

## 17. Acceptance Criteria (AC)

* [ ] Valid JSON is returned for correct input
* [ ] Empty marker list is allowed
* [ ] >100 markers → validation failure
* [ ] Duplicate marker codes → validation failure
* [ ] Invalid JSON → immediate failure
* [ ] Missing required fields → validation failure
* [ ] Debug mode logs prompt
* [ ] No hardcoded config values
* [ ] Prompt template externally editable
* [ ] Provider-agnostic interface
* [ ] `make lint`, `make test`, `make int-test` pass inside Docker

---

## 18. Future Extensions

* Mapping to `standard_biomarkers`
* Status evaluation (high/low/normal)
* Reference range interpretation
* Deterministic output tuning
* Fallback provider
* Rule-based extractor
* Compliance audit trail