# Implementation plan: European oncology collaboration demo

**Status:** Approved architecture; implementation may proceed locally
**Date:** 2026-09-23
**Cloud provisioning:** Approved baseline attempted; blocked on revised private-networking cost

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

**Status:** Complete

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

### Validation evidence

- A typed `EvidenceArrivalEvent` and `EvidenceArrivalSource` form the local
  delivery boundary intended for a later Event Grid adapter; the implemented
  local endpoint does not provision or call Azure.
- One synthetic delivery adds source-linked baseline CT and restaging liver MRI
  metadata, including original lesion sites, changed lesion visibility and
  size, and a new vessel relationship.
- Successful delivery creates prepared case v2 from v1 exactly once. The
  persisted event fingerprint makes repeated delivery of the same event ID
  idempotent and rejects reuse of that ID for different content.
- Prepared-case versions are retained as immutable snapshots. Version and
  version-specific source endpoints keep earlier evidence inspectable.
- The deterministic case delta explicitly lists added evidence, before/after
  findings, human conclusions requiring reassessment, remaining uncertainty,
  and affected human questions. It makes no treatment or resectability
  decision and invokes no AI runtime.
- The UI presents before/after versions, “what changed” categories,
  source links for new and prior evidence, and the retained-version cue.
- Refresh errors retain the current valid version, persist an update-error
  record when possible, and are shown without replacing the workspace.
- Backend formatting and Ruff lint pass; strict mypy passes.
- Twenty-one backend tests pass with 96% statement coverage.
- Frontend lint, seven Vitest behavior tests, and the production build pass.
- Local evidence-event transitions are serialized across the complete
  idempotency check and persistence operation; concurrent duplicate deliveries
  produce one new version and one duplicate response.
- Real source parsing failures are translated into visible update errors while
  preserving the prior valid case.

### Known limitations carried forward

- Imaging uses synthetic DICOM metadata JSON only. No pixels, rendered
  derivative, DICOMweb integration, or clinical image interpretation is
  included.
- The Event Grid-shaped seam is exercised locally; Azure delivery,
  authentication, retries, dead-letter handling, and monitoring remain
  INC-007 after separate approval.
- Browser screenshots, responsive visual evidence, accessibility automation,
  and clinical-fidelity review remain INC-006.

## INC-004: Human responsibility and MDO handoff

**Status:** Complete

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

### Validation evidence

- Human opinions are typed and persisted with reviewer, considered opinion,
  explicit condition decisions, next responsible actor/action, timestamp, case
  ID, and prepared-case version.
- Required evidence findings and source conflicts become explicit review
  conditions. The backend rejects omitted conditions and resolved conditions
  without a resolution note.
- Review state is recalculated against the current immutable prepared-case
  version. Evidence arrival leaves the earlier opinion in history but marks it
  stale, removes handoff readiness, and requires a new review for the new case
  version.
- Handoff creation uses optimistic case-version and opinion-ID checks and is
  blocked until every required evidence/review condition is resolved.
- Persisted manifests are independently versioned and preserve case ID, clinical
  question, prepared evidence version, source-evidence inventory, unresolved
  evidence and review issues, human responsibility, timestamp, and synthetic/not-for-
  clinical-use labels.
- The controlled launch URL contains only case ID, evidence version, and
  manifest ID. The UI and manifest state that the autonomous MDO uses a separate
  backend in version one; no MDO API or private state is accessed.
- Success and failure tests cover missing/blank conditions, explicit
  responsibility, stale review after evidence arrival, wrong-version rejection,
  continuity fields, manifest versioning/persistence, gated UI behavior, and the
  separate-backend launch notice.
- Backend formatting and Ruff lint pass; strict mypy passes.
- Twenty-seven backend tests pass with 96% statement coverage.
- Frontend lint, nine Vitest behavior tests, and the production build pass.
- Independent review findings were fixed: stale manifests are not restored as
  launchable for newer case versions, missing source evidence remains in the
  handoff, and whitespace-only reviewer/opinion values are rejected.

### Known limitations carried forward

- Condition resolution is a human workflow disposition and does not add or
  modify source evidence. The synthetic molecular gaps remain visible in the
  immutable prepared case.
- The default MDO target is `http://localhost:5174`; the separate application's
  availability and matching-case rehearsal must be checked before presentation.
- No shared backend, authenticated transfer, receipt acknowledgement, or live
  MDO integration is included in version one.
- Browser screenshots, responsive visual evidence, accessibility automation,
  and clinical-fidelity review remain INC-006.

## INC-005: Research authorization epilogue

**Status:** Complete

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

### Implementation evidence

- `collab.research.ResearchProjectionModule` owns the projection purpose,
  versioning, exact allowlist, exclusions, source-linked lineage, and
  publication behavior behind one small interface.
- `OneLakeProjectionAdapter` is the future publication seam. The only current
  adapter is `LocalFabricAdapterFake`; it performs no network or Fabric
  operation and has an explicit failure mode.
- `GET` and `POST /api/research/projection` require the separately simulated
  `synthetic-researcher` role. Missing or clinical roles receive `403`; clinical
  workspace access does not imply research access.
- The published record contains only synthetic case ID, diagnosis, histology,
  and systemic treatment. Workflow notes, direct source documents, patient
  identifiers, human opinions, and handoff responsibility are explicitly
  excluded.
- Publication receipts and approved projections persist in local demo state.
  Failed publication returns `503` and does not persist or display an
  unconfirmed projection.
- The React epilogue shows clinical-role denial and separately authorized
  loading, empty, success, lineage, exclusion, and failure states.

### Validation evidence

- Ruff format check and lint pass.
- Strict mypy passes for all 14 source files.
- All 34 backend tests pass with 96% statement coverage, including authorization,
  exact allowlisting, exclusions, lineage, persistence, missing-case behavior,
  and failed publication.
- Frontend lint passes; all 13 Vitest behavior tests and the production build
  pass.
- Independent review findings were fixed: research authorization now uses a
  separately configured code and HTTP-only session rather than a caller-minted
  role header; publication is staged and idempotent for reconciliation; and the
  UI explicitly offers a new projection after the clinical case advances.

### Known limitations carried forward

- `X-Demo-Role` is a deterministic demonstration header, not production
  authentication, consent, or authorization.
- The adapter fake does not contact Fabric or OneLake. Implementing a cloud
  adapter, workspace, identity, or role assignment remains gated under INC-007.
- Cohort feasibility intentionally contains one synthetic case and is not a
  statistical, clinical, or governance claim.

## INC-006: Demonstration and quality

**Status:** Complete locally; external clinical-fidelity approval pending

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

### Implementation evidence

- `GET /api/preflight` returns a typed report for deterministic mode, all eight
  required source fixtures parsed through the real preparation and late-arrival
  adapters, state-store load/write readiness, the production frontend build,
  the MDO narrative boundary, and optional research authorization. It performs
  no Azure, Fabric, MDO, or live-AI request.
- A presenter can reset from every application stage. Reset clears the complete
  local `DemoState`, presenter-edited inputs, and every issued local research
  session, then returns visible confirmation that is cleared when work resumes.
- The UI now has explicit restore-loading, bounded empty-match, error,
  evidence-update, and completed clinical-path states.
- The five-step journey is an ordered progress region with current/completed
  semantics. The source inspector is a modal dialog with initial focus and
  Escape close, keyboard focus containment, inert background content, and
  trigger-focus restoration.
- Playwright drives the public UI from a clean state through expertise,
  referral, preparation, provenance inspection, late imaging, human review, and
  MDO manifest creation at 1440×960 and Pixel 7 widths.
- The planned presenter beats total 90 seconds. The automated path verifies the
  same actions complete well below the 120-second upper bound.
- axe automation covers WCAG 2 A/AA and WCAG 2.1 A/AA on opening and prepared
  states at desktop and mobile widths.
- Loading, empty, error, update, completed, desktop, and mobile JPEG evidence is
  stored under `docs/demo/evidence/`; the set remains below 1 MB.
- `docs/demo/presenter-guide.md` provides the timed visual story, exact bounded
  language, preflight/reset sequence, and recovery paths.
- `docs/reviews/inc-006-quality-review.md` records intent, code, security,
  visual, accessibility, and requirements-to-evidence review.
- `docs/reviews/clinical-fidelity-review-package.md` defines the external
  oncology review dossier and makes clear that fidelity approval is still
  pending.

### Validation evidence

- Ruff format check and lint pass.
- Strict mypy passes for all 14 source files.
- All 40 backend tests pass with 96% statement coverage.
- Frontend lint passes; all 13 Vitest tests and the production build pass.
- Five Playwright checks pass across desktop and mobile Chromium; the
  desktop-only state-capture case is intentionally skipped on mobile.
- Complete presenter rehearsal passes repeatedly from a clean state on both
  configured viewports.

### Known limitations carried forward

- External oncology review is not complete. `RT-002` remains a mandatory gate
  before presenting the case as clinically plausible.
- Browser automation covers Chromium only and does not replace assistive-
  technology or clinician usability testing.
- The MDO target is not health-checked; the manifest is a narrative deep link
  with no private state integration.
- DICOM remains metadata-only, and the research adapter remains a local fake.

## INC-007: Azure and Fabric deployment

**Status:** In progress; three-private-endpoint deployment approved

### Original gate

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

### Prepared implementation evidence

- Azure Blob institution-source adapters preserve original source content and
  replace local retrieval references with Blob references.
- Azure Blob collaboration-state persistence implements the existing state-store
  seam and rejects stale writes with Blob ETag preconditions.
- A Blob trigger publisher and authenticated Event Grid webhook preserve the
  idempotent late-evidence flow.
- The runtime identity reads Milan and Utrecht source accounts, writes shared
  collaboration state, and writes only a separate Milan `events` container;
  source evidence remains read-only.
- Azure Monitor auto-instrumentation records request latency, while structured
  content-free events record source reads, case-version transitions, failed
  refreshes, accepted Event Grid deliveries, and MDO handoff creation.
- The Azure runtime keeps deterministic synthesis, excludes Azure OpenAI, and
  leaves the Fabric research adapter disabled.
- Bicep defines tagged resource groups, managed identity, least-privilege Blob
  roles, Container Apps, ACR, Event Grid, bounded Log Analytics/Application
  Insights, a budget alert, and teardown scripts.
- Forty-three backend tests pass with 92% statement coverage; Azure adapter,
  persistent state, trigger reset, Event Grid validation, secret rejection, and
  accepted delivery behavior are covered.

### Deployment finding

The approved subscription forces Blob `publicNetworkAccess=Disabled`, overriding
the original template. The app cannot use the three storage accounts without
private networking. The failed base deployment was cleaned up before an
application became live. See
[`../decisions/azure-deployment-networking.md`](../decisions/azure-deployment-networking.md).

The user selected the three-private-endpoint option with a EUR 35 budget alert.
Deployment may proceed with a VNet-integrated Container Apps environment, one
private endpoint per storage account, and linked Blob private DNS.

### Live deployment checkpoint

The approved base deployment completed on 2026-09-23 after registering the
subscription feature required by a VNet-integrated external Container Apps
environment. The durable checkpoint now contains:

- Container Apps environment `oncology-collab-demo-env-2`;
- all three storage accounts with public access disabled;
- exactly three approved Blob private endpoints and linked private DNS;
- ACR, managed identity, monitoring, least-privilege runtime roles, and the
  EUR 35 budget alert;
- application image `oncology-collab-demo:16c1cd8`, whose remote ACR build
  completed successfully.

The deployment stopped after the local Azure CLI failed to render a Unicode
checkmark while streaming the successful ACR build log through the Windows
code page. This was not an ACR or infrastructure failure. It exposed two
orchestration weaknesses: the script treated a presentation-layer log failure
as a build failure, and it could not resume after a completed base deployment.

The deployment script now supports resuming from the latest successful base
deployment, reusing a verified image tag, preserving the approved
`2026-10-07` expiry, and polling ACR build state without streaming logs. No
Container App, Event Grid system topic, or Entra presenter application has been
created yet. No live rehearsal has run.

## Technical quality gates

The exact commands will be established with the application scaffold. At minimum:

- Python formatting, linting, type checking, and tests;
- TypeScript type checking, unit tests, and production build;
- browser acceptance tests at mobile and desktop widths;
- dependency and security review;
- deterministic demo rehearsal;
- source-provenance and intent-traceability verification.

## Next action

INC-006 is complete locally and ready for external clinical-fidelity review.
That review remains a presentation gate. Resume `INC-007` from the successful
base and image checkpoints with:

```powershell
.\scripts\deploy-azure.ps1 -ResumeAfterBase -ReuseExistingImage -ApplicationImageTag 16c1cd8
```

Do not rerun the base deployment or image build. The remaining sequence is
Container App deployment and fixture seeding, removal of temporary write roles,
Event Grid creation, live rehearsal verification, and Entra presenter
authentication. Fabric remains deferred, Azure OpenAI remains disabled, and the
approved expiry remains 2026-10-07.
