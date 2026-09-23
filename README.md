# European oncology collaboration demo

A synthetic demonstration of how an Italian oncologist could discover suitable
European expertise, initiate a cross-border referral, and prepare a source-linked
case for multidisciplinary review.

**Demonstration system. Not for clinical use. No real patient data, clinician
directory, credential verification, or hospital integration.**

The approved product, architecture, reviews, and implementation plan live under
[`docs/`](docs/).

## Implemented local rehearsal

- Explainable expert discovery and a persisted synthetic Milan-to-Utrecht referral.
- Institution source seam with genuinely different Milan and Utrecht local adapters.
- CDA/XML, PDF-derived pathology text, local JSON, FHIR-like JSON, review-requirement
  JSON, and DICOM metadata fixtures.
- A prepared-case module that preserves source values, normalized values,
  transformations, provenance, warnings, unmapped values, missing molecular
  evidence, and deliberate identifier/date conflicts.
- Deterministic synthesis whose statements carry support identifiers from the
  prepared evidence package and never produce a treatment recommendation.
- A clinical workspace with source inspection and explicit source/normalized,
  missingness, conflict, and transformation cues.
- A local evidence-arrival endpoint shaped for the future Event Grid adapter,
  with idempotent delivery of synthetic baseline CT and restaging liver MRI
  metadata.
- Immutable prepared-case versions, source inspection by version, and a
  source-linked delta covering added evidence, changed findings, remaining
  uncertainty, and affected human questions.
- Before/after and “what changed” views that preserve the previous valid case
  and show an explicit update error if refresh fails.
- Typed human opinion, required evidence/review-condition decisions, and explicit
  next-actor/next-action responsibility bound to one prepared-case version.
- Stale-review protection: a case update never carries an older opinion or
  handoff readiness forward to the newer evidence version.
- Persisted, versioned MDO handoff manifests preserving the synthetic case ID,
  clinical question, evidence version, evidence inventory, unresolved issues,
  responsibility, and demonstration labels.
- A gated narrative deep link to the autonomous MDO demonstration. Version one
  explicitly uses a separate backend and does not synchronize runtime state.
- A deep research-projection module with an exact synthetic field allowlist,
  visible purpose, schema/projection version, field-level source lineage, and
  explicit exclusions for workflow notes, direct source documents, identifiers,
  human opinions, and handoff responsibility.
- A separately authorized `synthetic-researcher` context, denied-by-default
  clinical access, a local Fabric adapter fake, and a future OneLake adapter
  seam without any Fabric or Azure resource changes.
- A short cohort-feasibility epilogue covering authorization, loading, empty,
  successful publication, and explicit publication-failure states.
- A typed presenter preflight covering deterministic mode, required fixtures,
  local state-store readiness, the production build, the narrative MDO boundary,
  and optional research authorization.
- A globally available reset that returns the rehearsal to a clean synthetic
  state with visible confirmation.
- Explicit restore-loading, bounded empty, error, evidence-update, and completed
  presenter states.
- Playwright acceptance at 1440×960 and Pixel 7 widths, axe accessibility
  automation, basic keyboard/dialog semantics, and a deterministic 90-second
  presenter beat plan.
- Durable visual evidence, a visual-storytelling presenter guide, structured
  quality review, requirements traceability, and a clinical-fidelity package
  ready for external oncology review.

## Run locally

Prerequisites: Python 3.12+, Node.js and npm.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location frontend
npm install
npm run build
Set-Location ..
$env:RESEARCH_DEMO_AUTHORIZATION_CODE = "choose-a-local-rehearsal-code"
.\.venv\Scripts\uvicorn.exe collab.app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>.

Before presenting, select **Preflight**, require all mandatory checks to pass,
then select **Reset**. The complete 90-second visual story and recovery language
are in [`docs/demo/presenter-guide.md`](docs/demo/presenter-guide.md).

For frontend development, run `npm run dev` in `frontend`; Vite proxies `/api`
to the FastAPI application on port 8000.

The presenter flow is: find expertise, create the referral, select **Prepare
clinical workspace**, inspect any provenance link, then select **Receive late
imaging evidence**. The case advances from version 1 to version 2 without an AI
prompt and displays the version comparison. Record the fictional Utrecht
clinician's opinion, explicitly resolve every required evidence/review condition,
assign the next actor and action, and create the MDO handoff manifest. The
controlled launch defaults to `http://localhost:5174` (override with
`MDO_DEMO_URL`) and carries only narrative continuity query fields; it does not
call or share state with the private MDO backend. Referral state, immutable case
versions, reviews, manifests, processed event IDs, and update errors are restored
from `data/demo-state.json` after restart.

The research epilogue requires the separately configured local rehearsal code.
The server exchanges it for an HTTP-only session cookie; the clinical UI cannot
grant itself research access with a caller-controlled role header.

Relevant local API routes:

- `GET /api/referrals/current`
- `POST /api/cases/current/prepare`
- `GET /api/cases/current`
- `GET /api/cases/current/versions`
- `GET /api/cases/current/versions/{version}`
- `GET /api/cases/current/update-error`
- `GET /api/cases/current/review`
- `POST /api/cases/current/reviews`
- `GET /api/cases/current/reviews`
- `POST /api/cases/current/handoffs`
- `GET /api/cases/current/handoffs`
- `GET /api/cases/current/sources/{evidence_id}`
- `POST /api/evidence-arrivals`
- `POST /api/research/authorize`
- `GET /api/research/projection` (authorized research session)
- `POST /api/research/projection` (authorized research session)

## Validate

```powershell
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe
.\.venv\Scripts\pytest.exe --cov=collab
Set-Location frontend
npm run lint
npm run test
npm run build
npm run test:browser
```

Current verified result (2026-09-23): backend formatting, Ruff lint, strict
mypy, and 38 pytest tests pass with 96% statement coverage; frontend lint,
13 Vitest behavior tests, the production build, and five Playwright checks pass
across desktop and mobile Chromium (one desktop-only visual-capture case is
skipped on mobile). Axe reports no critical or serious WCAG A/AA violations in
the automated opening and prepared-workspace scans.

Review evidence:

- [`docs/reviews/inc-006-quality-review.md`](docs/reviews/inc-006-quality-review.md)
- [`docs/reviews/clinical-fidelity-review-package.md`](docs/reviews/clinical-fidelity-review-package.md)
- [`docs/demo/evidence/`](docs/demo/evidence/)

## Current limitations

- All people, institutions, identifiers, evidence, and workflows are synthetic.
- The PDF fixture is deterministic extracted text; no PDF layout/OCR processing
  occurs.
- DICOM is represented by source metadata only; no pixel viewing, rendered
  derivative, or clinical image interpretation occurs.
- FHIR is deliberately FHIR-like and is not validated against a production
  profile.
- The local evidence-arrival interface mirrors the application seam intended
  for Event Grid, but no Event Grid subscription or cloud adapter exists yet.
- Review-condition resolution records a typed human disposition; it does not
  manufacture missing molecular evidence or alter immutable prepared evidence.
- The MDO launch target is a configurable narrative deep link. Availability and
  matching-case readiness of the separate MDO application remain presentation
  preflight responsibilities; no private MDO backend integration exists.
- Research authorization is a labeled local simulation using a configured code
  exchanged for an HTTP-only localhost session cookie, not production identity,
  consent, or workspace security.
- The local Fabric adapter stores no external data. The OneLake interface is
  only a future adapter seam; no cloud adapter or Fabric workspace integration
  exists.
- Browser automation is Chromium-only and does not replace screen-reader,
  cross-browser, or clinical-user usability testing.
- The clinical-fidelity package is ready, but external oncology review and
  presentation approval remain unresolved.

Azure provisioning, Fabric changes, deployment, and live model usage require
separate approval.
