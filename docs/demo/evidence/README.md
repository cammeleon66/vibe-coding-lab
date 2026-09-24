# Visual evidence

Full-page captures from `frontend/tests/federation.spec.ts`, run against the
three local services (UMC Utrecht, Heidelberg, federation hub), for the
`desktop-chromium` and `mobile-chromium` projects:

| File | Role / moment |
| --- | --- |
| `01-nl-chart-*` | NL oncologist: Maria's chart at UMC Utrecht |
| `02-nl-sent-*` | NL oncologist: minimised peer-review request delivered |
| `03-de-evidence-*` | Heidelberg expert: local cohort evidence and structured opinion |
| `04-nl-opinion-*` | NL oncologist: opinion received |
| `05-control-room-*` | Control room: activity, boundary inspector, package check |
| `06-research-*` | Researcher: federated query, aggregates only |
| `07-disconnect-*` | Heidelberg taken offline; network degrades gracefully |

Regenerate them with:

```powershell
Set-Location frontend
npm run build
$env:CAPTURE_EVIDENCE = '1'
npx playwright test federation.spec.ts
```
