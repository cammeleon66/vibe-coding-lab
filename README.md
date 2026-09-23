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
clinical workspace**, and inspect any provenance link. The referral and prepared
case are restored from `data/demo-state.json` after restart.

Relevant local API routes:

- `GET /api/referrals/current`
- `POST /api/cases/current/prepare`
- `GET /api/cases/current`
- `GET /api/cases/current/sources/{evidence_id}`

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

Current verified result (2026-09-23): backend formatting, lint, strict mypy, and
11 pytest tests pass with 97% statement coverage; frontend lint, 5 Vitest
behavior tests, and the production build pass.

## Current limitations

- All people, institutions, identifiers, evidence, and workflows are synthetic.
- The PDF fixture is deterministic extracted text; no PDF layout/OCR processing
  occurs.
- DICOM is represented by source metadata only; no pixel viewing or clinical
  image interpretation occurs in INC-002.
- FHIR is deliberately FHIR-like and is not validated against a production
  profile.
- Conflict resolution, molecular evidence arrival, imaging updates, human
  opinion, MDO handoff, research projection, and cloud adapters remain later
  approved increments.

Azure provisioning, Fabric changes, deployment, and live model usage require
separate approval.
