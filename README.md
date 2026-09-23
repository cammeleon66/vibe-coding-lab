# European oncology collaboration demo

A synthetic demonstration of how an Italian oncologist could discover suitable
European expertise, initiate a cross-border referral, and prepare a source-linked
case for multidisciplinary review.

**Demonstration system. Not for clinical use. No real patient data, clinician
directory, credential verification, or hospital integration.**

The approved product, architecture, reviews, and implementation plan live under
[`docs/`](docs/).

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

Azure provisioning, Fabric changes, deployment, and live model usage require
separate approval.
