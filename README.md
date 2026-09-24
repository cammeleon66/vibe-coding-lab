# European oncology collaboration demonstration

A synthetic five-minute demonstration that solves a nearby Utrecht hospital
exchange first, then applies the same federated pattern to a closed-loop
oncology referral from Milan to Utrecht. It shows how hospital-owned systems
can remain decentralized while clinicians approve what crosses institutional
boundaries and retain clear responsibility.

**Demonstration system. Not for clinical use. No real patient data, clinician
directory, credential verification, or hospital integration.**

## Demonstrated journey

The journey is a backend-owned **storyline** of 14 scenes in three chapters
(Utrecht, the European network, Milan to Utrecht). `GET /api/journey` returns
the current scene, its actor, handover, and advance label; the frontend is a
clinical EHR-style scene renderer that advances only via the
`advance_scene` action. See [`CONTEXT.md`](CONTEXT.md) and the step-by-step
[`presenter guide`](docs/demo/presenter-guide.md).

1. Two synthetic Utrecht hospitals resolve a missing-imaging problem through
   visible patient-summary and imaging-system requests.
2. A clinician approves the regional exchange; source files remain at the
   hospital that owns them and the next responsibility is explicit.
3. The interface zooms out through Utrecht, the Netherlands, Germany and Italy,
   and Europe while preserving the same trust rules.
4. Dr Luca Bianchi opens a Milan patient worklist and selects the one patient
   who needs external specialist review.
5. The application calls the Milan EHR, document repository, and imaging
   archive separately and keeps missing evidence visible.
6. Dr Bianchi confirms the clinical question, queries a bounded synthetic expert
   directory, selects UMC Utrecht, and checks Utrecht's referral requirements.
7. The application prepares immutable case version 1 with source provenance.
   Structured context can cross after approval; original documents, images, and
   the Milan record remain in Milan.
8. Dr Bianchi records his referral assessment and explicitly approves sharing.
9. Dr Eva van Dijk acknowledges version 1, records a separate provisional
   specialist opinion, and requests the missing baseline CT and liver MRI with a
   clinical reason.
10. The evidence-arrival path creates immutable case version 2 and a visible
   version delta. Dr Bianchi approves the update before Utrecht can acknowledge
   it.
11. Dr van Dijk records the final specialist opinion and accepts version 2 into
   the Utrecht MDO.
12. Milan receives the opinion, meeting schedule, and Dr Bianchi's next
   responsibility. A persistent timeline records source queries, approvals,
   acknowledgements, and responsibility changes.

Research projection and presenter preflight routes remain available in the
backend for compatibility, but they are not part of the primary clinical
journey.

## Run locally

Prerequisites: Python 3.12+, Node.js, and npm.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm --prefix frontend install
npm --prefix frontend run build
.\.venv\Scripts\uvicorn.exe collab.app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Use **Reset** before a rehearsal.

The complete presenter path and recovery wording are in
[`docs/demo/presenter-guide.md`](docs/demo/presenter-guide.md).

## Primary journey interface

- `GET /api/journey`
- `POST /api/journey/actions`
- `POST /api/evidence-arrivals`
- `POST /api/reset`
- `GET /api/cases/current/versions`
- `GET /api/cases/current/versions/{version}`
- `GET /api/cases/current/sources/{evidence_id}`

The application also retains the earlier typed referral, prepared-case, human
review, handoff, research, preflight, health, access-code, and Event Grid routes.

## Validate

```powershell
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src --strict
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:browser
```

Current local baseline: 58 backend tests, strict mypy, Ruff, 20 Vitest tests
(one per scene, driven by real per-scene backend snapshots in
`frontend/src/test/sceneSnapshots.json`), frontend lint/build, and six
desktop/mobile Playwright checks in `frontend/tests/storyline.spec.ts`.
Automated axe scans report no serious or critical WCAG A/AA findings on the
captured storyline screens.

Regenerate the Vitest snapshots after a backend storyline change:

```powershell
cd frontend
npm run build
$env:CAPTURE_SNAPSHOTS='1'; npx playwright test storyline.spec.ts --project=desktop-chromium -g "full storyline"
```

## Limits

- All people, institutions, identifiers, evidence, and workflows are synthetic.
- The directory is curated and bounded; it does not verify real credentials,
  availability, permissions, reimbursement, or interoperability.
- PDF evidence is deterministic extracted text. DICOM is represented by
  metadata; no pixels are displayed or interpreted.
- FHIR-shaped data is not validated against a production profile.
- Preparation and synthesis are deterministic and source-constrained. They do
  not diagnose, recommend treatment, or decide resectability.
- Browser automation is Chromium-only and does not replace screen-reader,
  cross-browser, clinical-user, privacy, or regulatory review.
