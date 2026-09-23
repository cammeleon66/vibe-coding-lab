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

## Run locally

Prerequisites: Python 3.12+, Node.js and npm.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location frontend
npm install
npm run build
Set-Location ..
.\.venv\Scripts\uvicorn.exe collab.app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>.

For frontend development, run `npm run dev` in `frontend`; Vite proxies `/api`
to the FastAPI application on port 8000.

The presenter flow is: find expertise, create the referral, select **Prepare
clinical workspace**, inspect any provenance link, then select **Receive late
imaging evidence**. The case advances from version 1 to version 2 without an AI
prompt and displays the version comparison. Referral state, immutable case
versions, processed event IDs, and update errors are restored from
`data/demo-state.json` after restart.

Relevant local API routes:

- `GET /api/referrals/current`
- `POST /api/cases/current/prepare`
- `GET /api/cases/current`
- `GET /api/cases/current/versions`
- `GET /api/cases/current/versions/{version}`
- `GET /api/cases/current/update-error`
- `GET /api/cases/current/sources/{evidence_id}`
- `POST /api/evidence-arrivals`

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
```

Current verified result (2026-09-23): backend formatting, Ruff lint, strict
mypy, and 19 pytest tests pass with 96% statement coverage; frontend lint,
7 Vitest behavior tests, and the production build pass.

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
- Conflict resolution, molecular evidence arrival, human opinion, MDO handoff,
  research projection, browser visual evidence, and cloud adapters remain later
  approved increments.

Azure provisioning, Fabric changes, deployment, and live model usage require
separate approval.
