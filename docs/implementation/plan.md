# Implementation plan: European oncology collaboration demo

**Status:** Local-to-European collaboration journey complete and live
**Date:** 2026-09-24
**Cloud deployment:** The closed-loop referral is live on the approved private
Azure baseline. The local-first opening reuses that baseline without new
services or trust-boundary changes.

## Closed-loop redesign plan

### Proposed: federated European oncology network (INC-017 to INC-024)

**Status:** Proposed — awaiting approval of DEC-017 to DEC-020 in
[`docs/product/federated-network-proposal.md`](../product/federated-network-proposal.md).
Nothing below is implemented or approved.

| Increment | Outcome | Depends on | Validation |
| --- | --- | --- | --- |
| INC-017 Role-based workspace shell | Role switcher (NL oncologist, Heidelberg expert, Control room); per-role inbox and patient tabs; advance toolbar removed; backend keeps rules, not screen order; optional presenter checklist. Supersedes ADR-016 navigation. | Approval | Vitest per role, Playwright free-navigation walk, axe |
| INC-018 Maria's case and expert search | Maria Janssen workstation (Overview, Timeline, Pathology, Imaging, Molecular, Treatment, MDO); metadata-only expertise catalogue search; select Heidelberg. | INC-017 | Backend catalogue tests; UI tests |
| INC-019 Governed sharing and activity monitor | Sharing checklist → policy check → minimisation (27→9) → identifier removal → FHIR-shaped bundle; one correlation ID; control-room monitor with request/response details. | INC-018 | Tests prove unchecked items and identifiers never leave NL |
| INC-020 Heidelberg peer review | Secure environment banner, inbox, approved package, expert opinion returned to NL. | INC-019 | Round-trip tests; Playwright |
| INC-021 Local cohort query | "Compare with our patients": signed query → Heidelberg local computation over OMOP-shaped data → aggregate only with small-cell suppression; "38 queried locally · 0 transferred". | INC-020 | Tests that no row-level data leaves Heidelberg |
| INC-022 Disconnect Heidelberg | Control-room disconnect/reconnect; NL shows incomplete federated result; rerun succeeds. | INC-021 | Failure-path tests, live check after INC-023 |
| INC-023 Separate hospital deployments | NL, Heidelberg and hub as separate Container Apps with own storage and identity (DEC-019). **Azure cost gate.** | INC-022 + cost approval | Live verifier, live Playwright |
| INC-024 MDO synthesis and research cohort | MDO synthesis over the platform APIs; research question → per-site cohort counts; closing visual. | INC-023 | Clinical wording review, tests |

### ADR-016: Backend-owned storyline with a clinical EHR-style scene renderer

**Status:** Approved by the product owner (@cammeleon66) on 2026-09-24.
Scope: the backend-owned 14-scene storyline and EHR-style scene renderer as
implemented on branch `redesign/storyline-screens` (PR #15), including merge
to `master` and redeployment to the existing Azure Container App baseline
(approved 2026-09-24: "go now until we are live"). No new Azure services.
Re-approval is needed if the storyline becomes non-linear or changes trust
boundaries.
**Date:** 2026-09-24

**Context:** The previous single-page frontend decided screen order and
gating itself (≈2,000 lines in `App.tsx`), mixed several steps per screen, and
duplicated backend rules. Presenters found it hard to know which button to
press next, and role switches were implicit.

**Decision:** The backend owns a fixed 14-scene storyline in three chapters
(Utrecht, European network, Milan to Utrecht). `GET /api/journey` returns the
current scene, actor, handover, `can_advance`, `blocked_reason`, and
`advance_label`; the only way forward is the typed `advance_scene` action with
`from_scene` (a repeated advance from an earlier scene is a no-op; advancing
from a scene not yet open, or while blocked, is rejected). The frontend is a
scene renderer (`StoryShell` + `scenes/registry.ts`) in a neutral clinical EHR
layout: patient banner, workflow rail, one work area, assistant pane, bottom
advance toolbar, and an audit-log drawer.

**Options considered:**

1. Keep frontend-owned flow with more guards — rejected: rules stay
   duplicated and restore/reload stays fragile.
2. Backend storyline, frontend renderer — chosen.
3. Route-per-step frontend router — rejected: adds URL state that can
   disagree with persisted backend state.

**Consequences:** One source of truth for order and gating; reload restores
the exact scene; frontend tests can use captured backend snapshots. The
storyline is fixed and linear by design; branching would need a new decision.
This is a **breaking change** to `/api/journey` and `/api/journey/actions`:
the `enter_role`, `open_scale_reveal` and `open_international_referral`
actions, the snapshot fields `roles`, `stages` and `next_role`, and the state
fields `current_stage`, `regional_exchange.phase` and `regional_exchange.stage`
were removed (`scripts/verify_azure_rehearsal.py` was updated accordingly).
No change to trust boundaries, data handling, identity, Azure services, or
cost.

**Reversibility:** Moderate. Rolling back means reverting backend and frontend
together (redeploying the previous image) and selecting **Reset**, because
state persisted under the new schema has no phase/stage fields and would load
on the old code at the default regional phase.

#### INC-016: Storyline screens

**Status:** Complete, merged (PR #15) and live.

**Validation evidence:**

- 58 backend tests, Ruff, and mypy pass.
- 20 Vitest tests render every scene from real per-scene backend snapshots
  and cover advance, read-only review, locked future steps, error, and reset.
- Six desktop/mobile Playwright checks pass with axe (no serious/critical
  findings). Fixed a mobile defect where the collapsed workflow strip hid step
  titles with `display: none`, leaving the step buttons without accessible
  names.
- Fresh storyline screenshots in `docs/demo/evidence/`; outdated captures
  removed.
- Deployed 2026-09-24 by updating the existing Container App in place (no
  new Azure services; existing access code, secrets, managed identity, Event
  Grid and expiry preserved): image `oncology-collab-demo:39b3f45`, revision
  `oncology-collab-demo--story-39b3f45`. A first revision (`--0000015`)
  failed activation without pulling its image; traffic stayed on
  `--0000014`, and a forced new revision suffix resolved it.
- Protected live verifier passed (2 regional and 3 international sources,
  case versions 1 and 2 via Event Grid, MDO on version 2, 29 timeline
  events, clean reset). Six live desktop/mobile Playwright checks with axe
  passed; `live-*` captures stored in `docs/demo/evidence/`.
- Rollback image: `oncology-collab-demo:c610b49` (revert frontend and backend
  together, then select **Reset**).

### Local-to-European storyline extension

#### INC-015: Regional proof and European scale reveal

**Status:** Complete

**Depends on:** INC-014.

**Outcome:** The demonstration begins with a short Utrecht-to-Utrecht
missing-imaging exchange, proves the federated pattern locally, then zooms out
to the existing Milan-to-Utrecht international referral.

**Scope:**

- Add persisted local-exchange state and typed journey actions behind
  `ReferralJourney.apply(action)`.
- Show two clearly synthetic nearby Utrecht institutions and one concrete
  missing-imaging problem.
- Make patient-summary and imaging-system requests visible in the persistent
  API activity panel.
- Require explicit local clinician approval before the exchange completes.
- Add a Utrecht → Netherlands → Germany/Italy → Europe scale transition.
- Preserve the existing international referral without duplicating its rules.
- Update presenter guidance, browser tests, screenshots, and live verification.

**Acceptance criteria:**

- The opening problem is understandable without explaining European referral
  policy.
- Local source ownership, provenance, sharing approval, and next responsibility
  are explicit.
- The scale transition states that geography changes but trust rules do not.
- The international phase starts only after the local proof is complete.
- Reset and refresh preserve correct local/international phase state.
- Desktop/mobile, keyboard, axe, backend, frontend, and protected-live checks
  pass without adding Azure services.

**Validation evidence:**

- Persisted regional state, ordering, restore, reset, and international-entry
  guards pass in the backend suite.
- Desktop and mobile rehearsals complete the regional exchange, scale reveal,
  international closed loop, keyboard path, and axe checks.
- Container App image `oncology-collab-demo:5b051ba` is active in revision
  `oncology-collab-demo--0000012`.
- The protected verifier passed two regional sources, three international
  sources, immutable versions 1 and 2, 29 persisted timeline events, refresh
  restore, MDO closure, and final reset.
- The existing access code, managed identity, storage, Event Grid, private
  endpoints, monitoring, budget, and expiry were preserved.

### Outcome

Deliver a five-minute synthetic referral from Milan to Utrecht that proves:

- hospital-owned data can be used through authorized APIs without first centralizing every source record;
- the platform can prepare a useful referral package with little manual data chasing;
- the audience can see what remains in Milan and what crosses to Utrecht;
- clinicians approve sharing, record clinical judgement, request missing evidence, and accept responsibility;
- late evidence creates an immutable approved update;
- the process closes with a Utrecht specialist opinion, MDO acceptance, and a returned next action in Milan.

The approved journey and language are recorded in `docs/product/product-brief.md`
version 0.4 and `CONTEXT.md`.

### Current worktree rule

The uncommitted redesign code is an implementation spike, not an approved
increment. It must not be committed or deployed as one large change. After the
issues below exist, retain only code that belongs to the active issue and either
replace or remove the rest. Documentation that records the approved product
direction may remain.

### Architecture correction

The workflow must not be implemented as a set of shallow route handlers whose
ordering rules are spread across the frontend.

Create one deep **referral journey module** at the collaboration-state seam.
Its interface is:

```text
snapshot() -> ReferralJourneySnapshot
apply(action: ReferralJourneyAction) -> ReferralJourneySnapshot
```

The module owns:

- allowed action ordering;
- acting role and institution;
- immutable case-version rules;
- Milan sharing approvals;
- Utrecht acknowledgements;
- evidence requests;
- referral assessment and specialist opinion ownership;
- MDO acceptance;
- next responsibility;
- activity-timeline events;
- idempotency and invalid-transition errors;
- persistence of the complete collaboration state.

HTTP routes are adapters to this interface. The React application renders the
returned snapshot and submits typed actions; it does not reproduce transition
rules.

The existing institution-source seam remains separate because Milan EHR,
document, PACS, Utrecht requirements, and receiving-system adapters genuinely
vary. Source queries return evidence availability and append a journey activity
through the referral journey module.

### Data-sharing model

Use the approved hybrid model:

- Milan and Utrecht source systems remain the source of truth.
- Structured referral context and provenance enter the approved referral
  package.
- Large source files remain in Milan and are represented by authorized
  retrieval references.
- The shared collaboration store contains journey state, approved package
  snapshots, provenance, activities, opinions, and acknowledgements; it does
  not become a copy of every source record.
- Every package or update that crosses from Milan to Utrecht requires an
  explicit Milan approval.
- Utrecht acknowledges the exact immutable case version under review.

### Screen model

Use six stages with dedicated screens:

1. **Patient** — role picker and Milan active-patient worklist.
2. **Local data** — split clinical/API view for Milan EHR, document repository,
   and PACS checks.
3. **Referral** — clinical question, expert-centre directory, Utrecht
   requirements, package contents, Milan referral assessment, and send approval.
4. **Utrecht review** — receiving inbox, version acknowledgement, provisional
   specialist opinion, and evidence request.
5. **Evidence update** — requested imaging arrives in Milan, case version 2 is
   prepared, compared, approved, and sent.
6. **MDO outcome** — Utrecht acknowledges version 2, finalizes the specialist
   opinion, accepts the case into MDO, and returns the result to Milan.

Completed and current stages are navigable. Future stages remain visible but
show the exact prerequisite when selected. The activity timeline remains
visible beside the clinical screen. Clinical and technical information are
shown together without marketing-style headings or generic AI language.

### Implementation sequence

| Increment | GitHub issue | Depends on |
| --- | --- | --- |
| INC-008 | [#7](https://github.com/cammeleon66/vibe-coding-lab/issues/7) | Approved product brief and DEC-010 |
| INC-009 | [#8](https://github.com/cammeleon66/vibe-coding-lab/issues/8) | #7 |
| INC-010 | [#9](https://github.com/cammeleon66/vibe-coding-lab/issues/9) | #8 |
| INC-011 | [#10](https://github.com/cammeleon66/vibe-coding-lab/issues/10) | #9 |
| INC-012 | [#11](https://github.com/cammeleon66/vibe-coding-lab/issues/11) | #10 |
| INC-013 | [#12](https://github.com/cammeleon66/vibe-coding-lab/issues/12) | #11 |
| INC-014 | [#13](https://github.com/cammeleon66/vibe-coding-lab/issues/13) | #12 and explicit deployment approval |

#### INC-008: Referral journey foundation and role entry

**Status:** Complete

**Depends on:** Product brief 0.3 and DEC-010.

**Outcome:** A persisted journey snapshot and command interface drive the role
picker, Milan workspace, three-patient worklist, and activity timeline.

**Scope:**

- Define `ReferralJourneySnapshot`, typed actions, transition errors, and the
  referral journey module.
- Migrate existing `DemoState` fields behind the module without losing reset,
  restore, or Azure Blob-state compatibility.
- Add Milan and Utrecht synthetic role contexts.
- Add the three-patient worklist and select the referral candidate.
- Render the six-stage rail and activity timeline shell.

**Acceptance criteria:**

- Invalid action ordering is rejected by the module, not inferred by the UI.
- Existing persisted states load through backward-compatible defaults.
- The role picker explains responsibilities without acting as production
  authentication.
- One patient is a clear referral candidate; the other two remain realistic
  but cannot enter the referral flow.
- Future stages state their prerequisites.
- Unit, route, restore, reset, and frontend navigation tests pass.

**Validation evidence:**

- `ReferralJourney` exposes only `snapshot()` and `apply(action)`; action
  ordering and persisted activity are not implemented in React.
- The shared `DemoState` adds a defaulted journey state, and a legacy JSON state
  without journey fields restores safely.
- The HTTP adapter exposes `GET /api/journey` and
  `POST /api/journey/actions`.
- The role picker distinguishes the synthetic Milan and Utrecht roles and
  states that it is not production authentication.
- The Milan worklist contains three synthetic patients and allows only the
  approved referral candidate to advance.
- The six-stage rail shows the exact prerequisite for every locked stage.
- Six journey backend tests, the complete 52-test backend suite, five Vitest
  tests, frontend lint/build, strict mypy, and four desktop/mobile Playwright
  checks pass.
- Desktop and mobile accessibility scans report no serious or critical
  violations for the role and patient screens.

#### INC-009: Federated Milan data check

**Status:** Complete

**Depends on:** INC-008.

**Outcome:** The audience sees real demo calls to three hospital-owned source
adapters and understands what data exists without seeing a centralized import.

**Scope:**

- Add distinct Milan EHR, document-repository, and PACS query actions.
- Return available records, missing evidence, source ownership, and endpoint
  identity.
- Record each query and result in the activity timeline.
- Build the split clinical/API screen.

**Acceptance criteria:**

- The browser performs actual backend calls for all three sources.
- Each result identifies the source system and available or missing evidence.
- No source record is copied into shared state merely because it was queried.
- Failure of one source remains visible and does not produce a success-shaped
  package.
- The activity timeline is restored after refresh.

**Validation evidence:**

- Three local adapters implement one federated patient-source interface for the
  Milan EHR, document repository, and imaging archive.
- `query_source` actions run through `ReferralJourney`, which persists results
  and success or failure activity without moving original source records into
  collaboration state.
- The split patient/source screen shows the real journey-action request, source
  identity, available records, and missing evidence.
- A failed source remains persisted as failed and keeps the referral stage
  locked.
- The complete 54-test backend suite, strict mypy, changed-file Ruff checks,
  five Vitest tests, frontend lint/build, and four desktop/mobile Playwright
  checks pass.

#### INC-010: Expert destination and approved referral package

**Status:** Complete

**Depends on:** INC-009.

**Outcome:** Dr Bianchi confirms the question, selects Utrecht from bounded
matches, reviews the hybrid package, records his referral assessment, and
approves case version 1 for sharing.

**Scope:**

- Query the expert-centre directory and Utrecht requirements through separate
  adapters.
- Explain match reasons and directory limitations.
- Prepare case version 1 through the existing case-preparation module.
- Show exactly what enters the package and what remains in Milan.
- Preserve source inspection and provenance.
- Record the Milan referral assessment separately from the Utrecht specialist
  opinion.

**Acceptance criteria:**

- Utrecht is selected through explainable matching, not direct navigation.
- Referral requirements come from the Utrecht requirements adapter.
- The package contains structured context and provenance, not every source
  file.
- Sending requires an explicit Milan approval.
- Refresh restores the sent case version and next role.

**Validation evidence:**

- The journey confirms Dr Bianchi's clinical question before querying the
  bounded expert directory, and Utrecht is the highest explainable match rather
  than a direct navigation target.
- Utrecht requirements are queried after destination selection and remain
  visibly present or missing in clinical language.
- The existing referral and case-preparation modules produce immutable case
  version 1 with source provenance.
- The package screen distinguishes structured context and provenance shared
  after approval from original records and imaging retained in Milan.
- Dr Bianchi's referral assessment is persisted separately, and only his
  explicit approval makes Utrecht available as the next workspace.
- The complete 55-test backend suite, strict mypy, Ruff, five Vitest tests,
  frontend lint/build, and four desktop/mobile Playwright checks pass; the
  browser flow also restores the approved package after refresh.

#### INC-011: Utrecht receiving review and evidence request

**Status:** Complete

**Depends on:** INC-010.

**Outcome:** The story switches to Dr van Dijk, who acknowledges case version 1,
reviews the source-linked package, records a provisional specialist opinion,
and requests missing imaging.

**Scope:**

- Add the guided Milan-to-Utrecht role transition.
- Build the Utrecht incoming-referral screen.
- Add version acknowledgement.
- Add a prefilled but editable provisional specialist opinion.
- Replace technical condition checkboxes with plain evidence status and one
  evidence-request action.

**Acceptance criteria:**

- Utrecht cannot review a package that Milan has not approved and sent.
- The exact case version under review is visible and acknowledged.
- The provisional opinion is owned by Dr van Dijk and remains distinct from Dr
  Bianchi's referral assessment.
- The evidence request names the missing evidence and clinical reason.
- No raw workflow-condition identifiers appear in the UI.

**Validation evidence:**

- The approved Milan screen provides a guided handoff to Dr Eva van Dijk's
  Utrecht workspace.
- Utrecht displays the exact case version, source-linked package, clinical
  question, and Dr Bianchi's separate referral assessment.
- Dr van Dijk must acknowledge version 1 before recording her editable,
  persisted provisional specialist opinion.
- The evidence request names the original baseline liver CT and restaging liver
  MRI with a clinical reason; no workflow-condition identifiers are exposed.
- Requesting the imaging returns responsibility to Milan and advances the
  journey to Evidence update.
- The complete 56-test backend suite, strict mypy, Ruff, five Vitest tests,
  frontend lint/build, and four desktop/mobile Playwright checks pass,
  including refresh restore after the Utrecht request.

#### INC-012: Versioned update and closed-loop MDO outcome

**Status:** Complete

**Depends on:** INC-011.

**Outcome:** Milan approves case version 2, Utrecht acknowledges it, records the
final specialist opinion, accepts it into MDO, and Milan receives the result.

**Scope:**

- Keep the Event Grid evidence-arrival path and immutable case delta.
- Require an Utrecht evidence request before the update can enter the journey.
- Require Milan approval before version 2 crosses the institutional seam.
- Require Utrecht acknowledgement before final review.
- Record the final specialist opinion, MDO schedule, and next responsibility.
- Add the closed-loop Milan result screen.

**Acceptance criteria:**

- Case version 1 remains inspectable.
- Duplicate evidence delivery remains idempotent.
- Utrecht cannot acknowledge an unapproved update.
- The final opinion applies to the current case version.
- MDO acceptance names the version, clinician, date, and next responsibility.
- Milan can see the returned opinion and MDO state.

**Validation evidence:**

- The existing evidence-arrival module accepts the requested Milan imaging only
  after Utrecht has made an evidence request and prepares immutable case version
  2 with a visible delta; duplicate delivery remains idempotent.
- Dr Bianchi sees the requested evidence, added source records, and changed
  findings before explicitly approving version 2 for Utrecht.
- Utrecht cannot acknowledge version 2 before Milan approval and cannot record
  the final opinion before acknowledging the exact current version.
- Dr van Dijk's final opinion, the Utrecht MDO schedule, accepted case version,
  and next Milan responsibility are persisted in the journey timeline.
- The returned Milan screen closes the loop with the specialist opinion, MDO
  schedule, and Dr Bianchi's next action.
- The complete 57-test backend suite, strict mypy, Ruff, five Vitest tests,
  frontend lint/build, and four desktop/mobile Playwright checks pass, including
  duplicate evidence delivery and refresh restore of the closed-loop outcome.

#### INC-013: Demonstration quality and plain-language review

**Status:** Complete

**Depends on:** INC-012.

**Outcome:** The full journey is clear, accessible, visually reviewed, and
presentable in about five minutes.

**Scope:**

- Remove research from the primary journey while preserving its backend and
  optional appendix capability.
- Hide preflight from the clinical interface.
- Audit every heading, label, empty state, helper text, and error for direct
  clinical language.
- Add responsive desktop/mobile layouts, keyboard navigation, focus handling,
  loading/error states, and visual evidence.
- Rewrite the presenter guide for the new journey.

**Acceptance criteria:**

- No slogan-like, vague AI, or marketing copy remains.
- A presenter can complete the journey without explaining why a control is
  disabled.
- Completed stages can be revisited; locked stages state the prerequisite.
- Axe, keyboard, desktop, mobile, visual, Vitest, backend, lint, type, and build
  checks pass.
- The rehearsed path completes in approximately five minutes.

**Validation evidence:**

- The primary interface contains only the clinical referral journey; research
  and presenter preflight remain backend compatibility routes and are not shown
  to clinicians.
- Headings, actions, helper text, failures, and the access-code page use direct
  clinical language without AI, transformation, or marketing claims.
- Screen changes move keyboard focus to the new heading; the scrollable activity
  timeline is keyboard focusable; locked stages state their exact prerequisite.
- The presenter guide now rehearses the complete Milan-to-Utrecht-to-Milan path
  in seven timed beats over approximately five minutes.
- Desktop and mobile closed-loop screenshots are stored under
  `docs/demo/evidence/closed-loop-*.png`.
- The complete 57-test backend suite, strict mypy, Ruff format/lint, five Vitest
  tests, frontend lint/build, npm audit, and four desktop/mobile Playwright
  checks pass. Full-journey and opening-screen axe scans report no serious or
  critical findings.

#### INC-014: Azure deployment and live rehearsal

**Status:** Complete

**Depends on:** INC-013 and explicit deployment approval.

**Outcome:** The approved redesign runs on the existing private Azure baseline
and passes the complete live referral rehearsal.

**Scope:**

- Build and deploy one reviewed image.
- Preserve the current access code unless rotation is explicitly requested.
- Reuse the existing managed identity, storage, Event Grid, private endpoints,
  DNS, monitoring, budget, and expiry.
- Run the live Milan-to-Utrecht closed-loop rehearsal.

**Acceptance criteria:**

- No new paid Azure service or trust-boundary change is introduced.
- Access-code, health, protected API, Event Grid secret, and private-storage
  checks pass.
- The live activity timeline survives refresh.
- The complete role, referral, update, and MDO path passes on desktop and
  mobile.
- Deployment evidence and rollback image are recorded.

**Validation evidence:**

- ACR image `oncology-collab-demo:bef999a` is active in Container App revision
  `oncology-collab-demo--0000010`; the previous stable `7e5a942` tag remains
  available for rollback.
- The existing managed identity, three private Blob endpoints, storage
  accounts, Container Apps environment, monitoring, budget, expiry, access
  code, and Event Grid system topic were preserved.
- The cookie-aware live verifier passed protected access, Azure preflight,
  three federated source checks, Event Grid delivery, immutable versions 1 and
  2, all clinician approvals, MDO acceptance, 23 persisted timeline events,
  refresh restore, and final reset.
- Four live Playwright checks passed against the protected URL at desktop and
  Pixel 7 sizes, including the complete closed loop, keyboard focus, and axe
  accessibility scans.
- Deployment details, live screenshots, and the exact rollback image and
  command are recorded in `docs/demo/azure-deployment.md`.

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
- Forty-five backend tests pass; Azure adapter,
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
- application image `oncology-collab-demo:d6927c1`, whose remote ACR build
  completed successfully.

The deployment stopped after the local Azure CLI failed to render a Unicode
checkmark while streaming the successful ACR build log through the Windows
code page. This was not an ACR or infrastructure failure. It exposed two
orchestration weaknesses: the script treated a presentation-layer log failure
as a build failure, and it could not resume after a completed base deployment.

The deployment script now supports resuming from the latest successful base
deployment, reusing a verified image tag, preserving the approved
`2026-10-07` expiry, polling ACR build state without streaming logs, waiting
between readiness attempts, and reusing the storage account's Defender-managed
Event Grid system topic.

The live deployment completed on 2026-09-24:

- the fixed image serves the packaged frontend and passes Azure preflight;
- fixture seeding is disabled after initial synthetic-data creation;
- temporary Milan and Utrecht contributor assignments were removed;
- `late-evidence` is attached alongside Defender's antimalware subscription and
  filters only Blob-created events in the Milan `events` container;
- the live rehearsal passed referral, case version 1, Event Grid late evidence,
  case version 2, human review, MDO manifest, and clean reset;
- DEC-008 replaced tenant-bound Entra with a shareable access-code page backed
  by Azure secrets and a signed 12-hour Secure/HttpOnly/SameSite session cookie;
- browser navigation redirects to the access-code page, protected APIs reject
  anonymous requests, `/api/health` remains available, and the Event Grid
  callback still rejects requests without its independent shared secret;
- Container Apps built-in authentication is disabled and the obsolete Entra
  application registration was deleted;
- all three storage accounts keep public network access disabled and all three
  private endpoints are approved.

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
That review remains a presentation gate. `INC-007` and the DEC-008 shareable
access correction are deployed and technically verified. The next product step
is a presenter/clinical walkthrough, followed by prioritizing observed
comprehension and fidelity gaps rather than adding infrastructure. Teardown
remains scheduled for 2026-10-07 using `scripts/teardown-azure.ps1`. Fabric
remains deferred, Azure OpenAI remains disabled, and no private MDO backend was
integrated.
