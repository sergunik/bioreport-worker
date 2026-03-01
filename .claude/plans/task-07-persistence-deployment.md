# Task — Finalize Normalization Output & Job Completion

## Goal

Finalize the document processing after receiving the normalized JSON from the API.

The worker must:
- persist normalized data
- de-anonymize the result
- store the final output
- update job state
- extend normalization schema with `pii`
- ensure full test coverage and code quality

## Technical Requirements
- Use dockerized environment for calling commands and running tests.
- In Makefile stored commands must be used for some operations (lints, tests, etc.).

## Scope

### 1. Persist & Finalize Results

After the worker receives the normalized JSON:

#### 1.1 Step: Persist Normalized Result
- Store the raw normalized JSON exactly as returned by the API.
- This must be saved in the database as a separate step.

#### 1.2 Step: De-anonymize JSON
- Replace all placeholders (`PERSON_*`, etc.) with original values.
- Placeholders must not remain in the final result.

#### 1.3 Step: Persist Final Result
- Store the fully de-anonymized JSON as the final output.
- Ensure data consistency (no partial writes).

### 2. DB missing fields
- Ensure all required fields are present in the database schema.
- Otherwise, provide a SQL-query to add missing fields, and it will be executed before deployment manually.


### 2. Extend Normalization Prompt with `pii`

Add a new field to the normalization schema:

```
"pii": ["string", "string"]
````

#### Requirements:

* AI must detect sensitive words in the text (names, surnames, dates, etc.).
* Markers are ignored.
* `PERSON_*` placeholders are ignored.
* Only real sensitive values are included.

#### 2.1 Update Schema & Artifacts

* Update JSON schema to include `pii`.
* Update stored artifacts structure.
* Ensure backward compatibility if needed.

> Note: This data will later be used to extend the user's personal sensitive word collection (out of scope for this task).

---

### 3. Job Finalization

After successful processing:

* Update job status → `done`
* Set `processed_at`
* Clear error fields (if any)
* Unlock DB row (if locking is used)

Ensure no inconsistent states remain.

---

### 4. Tests

Add or update tests to cover:

* Normalized JSON persistence
* De-anonymization correctness
* `pii` field handling
* Job state transitions
* No retry after `failed`
* No partial DB writes
* others

Integration tests must validate end-to-end behavior.

---

### 5. Refactoring & Cleanup

* Refactor related logic if necessary
* Remove duplicated code
* Ensure separation of concerns
* Keep persistence atomic
* Ensure clear error handling and logging
* Document code and logic where needed
* Ensure code readability and maintainability

---

### 6. Quality Checks

All must pass:

* Linting
* Static typing
* Unit tests
* Integration tests

No warnings. No failing checks.
