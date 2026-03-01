# Task: Refactor Processor into Isolated Pipeline Steps

## Goal

Refactor the current `Processor` implementation into a clean, isolated pipeline architecture based on sequential steps.

The new design must ensure:
- Strict step isolation
- Single responsibility per step
- Explicit data flow via a shared typed context
- No hidden side effects inside computation steps
- Clear persistence boundaries

---

## Target Architecture

Processor becomes a pure orchestrator:

```

Processor
└── list[PipelineStep]
├── MarkProcessingStep
├── LoadDocumentStep
├── ExtractTextStep
├── PersistParsedStep
├── AnonymizeStep
├── PersistAnonymizedStep
├── ExtractArtifactsStep
├── PersistArtifactsStep
├── NormalizeStep
├── PersistNormalizedStep

```

---

## Core Requirements

### 1. Pipeline Context

- Introduce a single `PipelineContext`
- Implemented as `@dataclass(slots=True)`
- Contains all intermediate and final processing data
- All steps read/write only via this context
- No step stores internal state

### 2. Step Interface

- Introduce a base `PipelineStep` interface
- Each step implements a single `run(context) -> context` method
- Steps must be stateless
- Steps must have one clear responsibility

### 3. Persistence Rules

- Computation steps must NOT persist data
- Persistence must be handled by dedicated `Persist*Step` classes
- All intermediate results must be persisted via explicit steps

### 4. Job Lifecycle

- At the beginning of processing, job status must be set to `processing`
- If any step fails, job status must be set to `failed`
- Status changes must be handled explicitly via dedicated steps

---

## Non-Goals

- No business logic rewrite
- No new features
- No async refactor

---

## Acceptance Criteria (AC)

- `Processor.process()` contains no business logic
- Each step is implemented as an isolated class
- All data exchange happens only through `PipelineContext`
- No step mixes computation and persistence
- Job status is correctly updated to:
  - `processing` at start
  - `failed` on error
- Steps are independently unit-testable and integration-testable
- The system allows adding/removing/reordering steps without rewriting `Processor`
- After refactoring linter and tests pass without issues (`make lint`, `make test`, `make int-test`)

---

## Expected Outcome

A clean, extensible, testable processing pipeline architecture suitable for production workloads and future scaling.
