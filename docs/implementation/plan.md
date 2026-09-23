# Implementation plan: European oncology collaboration demo

**Status:** Approved architecture; implementation may proceed locally
**Date:** 2026-09-23
**Cloud provisioning:** Not approved

## Implementation strategy

Build one vertical story in small increments. Keep the application runnable and demonstrable after every increment. Use the same broad technology family as the autonomous MDO demonstration—Python/FastAPI and React/TypeScript/Vite—so the handoff can feel coherent and the repository can reuse proven testing and presentation patterns without copying its application design.

The first useful milestone is a complete deterministic local rehearsal. Azure adapters follow only after the same interfaces work against local fixtures. This keeps the approved Blob architecture real while preventing cloud setup from blocking product validation.

## Traceability

| Increment | Requirements | Evidence |
| --- | --- | --- |
| INC-001 | REQ-001, REQ-002, REQ-003 | Expert discovery and referral acceptance tests |
| INC-002 | REQ-004, REQ-005, REQ-006, REQ-007, REQ-008 | Source-adapter, provenance, preparation, conflict, and AI-boundary tests |
| INC-003 | REQ-009 | Evidence-arrival and case-delta tests plus presenter walkthrough |
| INC-004 | REQ-010, REQ-011 | Human opinion, responsibility, and MDO handoff tests |
| INC-005 | REQ-012 | Separate research-projection authorization tests |
| INC-006 | REQ-013 | Browser acceptance, visual review, rehearsal timing, and failure-path evidence |
| INC-007 | Approved architecture | Azure adapter verification and deployment evidence after separate approval |

## INC-001: Expert discovery and referral

**Status:** Complete

### Outcome

A presenter can begin as the synthetic Italian oncologist, enter or select the clinical need, inspect explainable European expert-centre matches, select the fictional Utrecht clinician, and initiate a versioned referral.

### Scope

- Establish FastAPI and React/TypeScript application shells.
- Define typed domain contracts for clinical need, expert centre, clinician, match explanation, referral requirements, and referral.
- Create a small, explicitly synthetic expert directory fixture.
- Implement the expert discovery module behind one interface.
- Implement deterministic ranking and explanation.
- Build a presenter-led discovery and referral flow.
- Persist local demo state without cloud dependencies.

### Acceptance criteria

- Utrecht is selected for explainable clinical reasons, not hard-coded UI navigation.
- Results state that coverage, credentials, permissions, availability, and interoperability are simulated.
- Referral requirements are carried into the created referral.
- Refreshing the application preserves the referral.
- Unknown centre or clinician identifiers are rejected.
- Automated tests cover ranking, explanation, referral creation, validation, and persistence.

### Validation evidence

- Python formatting, linting, and strict type checking pass.
- Four backend tests pass with 96% statement coverage.
- Three frontend behavior tests, frontend lint, and the production build pass.
- A live local rehearsal returned Utrecht as the top match, created a referral,
  served the built frontend, and restored the same referral after an application
  restart.

## INC-002: Heterogeneous evidence and prepared workspace

**Status:** Complete

### Outcome

The referral becomes a source-linked prepared case assembled from two genuinely different local source fixtures.

### Scope

- Define the institution source seam and evidence envelope.
- Implement Milan and Utrecht local adapters.
- Add CDA/XML, PDF-derived text, local JSON, FHIR-like JSON, and DICOM metadata fixtures.
- Implement the case preparation module.
- Preserve original evidence, transformation state, missingness, conflicts, and unmapped values.
- Add deterministic source-linked synthesis.
- Build the clinical workspace and source inspection experience.

### Acceptance criteria

- Every important prepared claim links to an original fixture.
- A deliberate date or identifier conflict remains visible.
- Missing molecular evidence remains visible.
- Source facts and normalized values are visually distinguishable.
- The deterministic synthesis cannot introduce facts absent from evidence.
- Tests cover every adapter, transformation warning, conflict, missing field, and provenance link.

### Validation evidence

- The institution source protocol is implemented by structurally different
  Milan and Utrecht local adapters.
- Local fixtures cover CDA/XML, PDF-derived text, local treatment JSON,
  DICOM metadata JSON, FHIR-like JSON, and Utrecht review-requirement JSON.
- The prepared case preserves raw values, normalized values, transformation
  descriptions, content hashes, source pointers, warnings, unmapped values,
  deliberate identifier/date conflicts, and the missing molecular profile.
- Every prepared claim has a source envelope and pointer; the presenter can
  retrieve and inspect that envelope through the HTTP API and UI.
- Deterministic synthesis is built only from prepared claims, conflicts, and
  missingness findings; support identifiers are validated against the package
  and no treatment or resectability conclusion is emitted.
- Backend formatting and Ruff lint pass; strict mypy passes.
- Twelve backend tests pass with 97% statement coverage.
- Frontend lint, five Vitest behavior tests, and the production build pass.
- Source inspection exposes the preserved synthetic original record, not only
  the derived evidence envelope, and partial molecular panels retain each
  still-missing component.
- Covered failure paths include preparation without a referral, source
  inspection without a prepared case, restore failure, and preparation failure
  while preserving the referral view.

### Known limitations carried forward

- PDF input is represented by deterministic extracted text, not OCR or layout
  interpretation.
- DICOM pixels and late restaging imaging remain INC-003; INC-002 preserves
  baseline DICOM metadata only.
- FHIR is intentionally FHIR-like and not production-profile validated.
- Clinical-fidelity review and browser visual evidence remain part of INC-006.

## INC-003: Imaging update and change detection

### Outcome

Baseline imaging and restaging MRI arrive after referral and automatically create a new prepared-case version with a clear delta.

### Scope

- Add a local evidence-arrival mechanism that uses the same interface planned for Event Grid.
- Add small synthetic DICOM fixtures or safely rendered derivatives with source links.
- Track original lesion sites and new anatomical evidence.
- Implement case-version comparison and changed-conclusion flags.
- Build before/after and “what changed” views.

### Acceptance criteria

- Evidence arrival requires no new AI prompt.
- The case version increments exactly once.
- The delta identifies added evidence, changed findings, remaining uncertainty, and affected human questions.
- Earlier evidence remains inspectable.
- Duplicate delivery is idempotent.
- Failure leaves the previous valid case visible and reports the update error.

## INC-004: Human responsibility and MDO handoff

### Outcome

The fictional Utrecht clinician records an opinion and next action, then creates a versioned narrative handoff to the existing MDO.

### Scope

- Add human opinion, conditions, and responsibility state.
- Require review against the current case version.
- Generate a handoff manifest.
- Preserve matching case ID, question, evidence version, unresolved issues, and synthetic labels.
- Add a controlled launch or deep link to the MDO.

### Acceptance criteria

- An opinion against an older case version cannot silently approve a newer version.
- The next responsible actor and action are explicit.
- The handoff cannot be created while required evidence or review conditions are unresolved.
- The UI states that the MDO uses a separate backend in version one.
- Manifest tests cover versioning, missing conditions, and continuity fields.

## INC-005: Research authorization epilogue

### Outcome

The presenter can show that a separately authorized research role sees an approved synthetic projection rather than the clinical workspace.

### Scope

- Define the research projection module.
- Create a local Fabric adapter fake and a future OneLake adapter seam.
- Publish only explicitly approved synthetic cohort fields.
- Show a short cohort-feasibility view.
- Demonstrate denied access from the clinical role.

### Acceptance criteria

- Clinical access does not imply research access.
- Projection purpose, version, fields, and lineage are visible.
- Workflow notes and direct source documents are excluded unless explicitly approved.
- Tests cover authorization, field allowlisting, lineage, and failed publication.

## INC-006: Demonstration and quality

### Outcome

The local product is visually compelling, deterministic, accessible, reviewable, and ready for clinical-fidelity review.

### Scope

- Create the 60–120 second presenter path.
- Add preflight and reset behavior.
- Cover responsive, loading, empty, error, update, and completed states.
- Run accessibility and browser acceptance checks.
- Perform structured code, security, intent, and visual review.
- Prepare a final clinical-fidelity review package.

### Acceptance criteria

- The complete rehearsal succeeds repeatedly from a clean state.
- The interface has a distinctive clinical-collaboration identity rather than generic SaaS cards.
- Important provenance, missingness, and responsibility cues are visible at presentation distance.
- All required states have visual evidence.
- Product requirements map to passing tests or demo evidence.
- Known limitations are presented explicitly.

## INC-007: Azure and Fabric deployment

### Gate

Do not begin until the user approves:

- the region-specific cost estimate;
- resource names and subscription;
- Entra application and role assignments;
- use of the existing Fabric capacity;
- monitoring limits;
- any Azure OpenAI model and token budget;
- deployment and teardown plan.

### Outcome

Replace local adapters with Azure adapters through existing seams, verify the deployed rehearsal, and record cost and operational evidence.

## Technical quality gates

The exact commands will be established with the application scaffold. At minimum:

- Python formatting, linting, type checking, and tests;
- TypeScript type checking, unit tests, and production build;
- browser acceptance tests at mobile and desktop widths;
- dependency and security review;
- deterministic demo rehearsal;
- source-provenance and intent-traceability verification.

## Next action

INC-002 is complete locally. The next planned increment is `INC-003`, but it has
not been started by this change. No Azure or Fabric resources were provisioned
or modified.
