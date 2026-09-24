# Azure deployment evidence

**Deployed:** 24 September 2026  
**Application:** `oncology-collab-demo`  
**Resource group:** `oncology-collab-demo-platform-rg`  
**URL:** `https://oncology-collab-demo.wittyrock-0461f613.westeurope.azurecontainerapps.io`

## Reviewed deployment

- Active image:
  `ocdpscufetxrykg6.azurecr.io/oncology-collab-demo:5b051ba`
- Active revision: `oncology-collab-demo--0000012`
- Revision mode: single
- Preserved expiry: `2026-10-07`
- Preserved access-code configuration; the code is not recorded in this
  repository.
- Fabric and Azure OpenAI remain disabled.
- No paid service or trust-boundary change was introduced.
- The three approved private Blob endpoints remain:
  - `ocdmilanpscufetxrykg6-blob-pe`
  - `ocdutrechtpscufetxrykg6-blob-pe`
  - `ocdsharedpscufetxrykg6-blob-pe`
- The existing Milan storage system topic was reused. Event subscription
  `late-evidence` is provisioned and points to the protected application Event
  Grid endpoint.

## Live verification

The cookie-aware verifier passed:

```json
{
  "status": "pass",
  "mode": "azure-synthetic-rehearsal",
  "protected_access": "pass",
  "regional_sources": 2,
  "international_sources": 3,
  "prepared_versions": [1, 2],
  "event_grid_event": "azure-event-grid-imaging-001",
  "mdo_case_version": 2,
  "timeline_events": 29,
  "final_state": "clean"
}
```

Live Playwright then passed six checks against the protected URL:

- persistent regional and international API activity at desktop and Pixel 7;
- complete desktop closed-loop referral;
- desktop keyboard and axe checks;
- complete Pixel 7 closed-loop referral;
- Pixel 7 keyboard and axe checks.

After presenter feedback, a persistent federated API activity panel was added.
Targeted protected-live checks passed at desktop and Pixel 7 sizes and confirmed
that source-system method, path, status, and result details remain visible after
the workflow advances beyond the local-data screen.

The live screenshots are:

- [`evidence/live-regional-proof-desktop-chromium.png`](evidence/live-regional-proof-desktop-chromium.png)
- [`evidence/live-regional-proof-mobile-chromium.png`](evidence/live-regional-proof-mobile-chromium.png)
- [`evidence/live-scale-reveal-desktop-chromium.png`](evidence/live-scale-reveal-desktop-chromium.png)
- [`evidence/live-scale-reveal-mobile-chromium.png`](evidence/live-scale-reveal-mobile-chromium.png)
- [`evidence/live-closed-loop-desktop-chromium.png`](evidence/live-closed-loop-desktop-chromium.png)
- [`evidence/live-closed-loop-mobile-chromium.png`](evidence/live-closed-loop-mobile-chromium.png)

## Rollback

The previous stable image remains in ACR:

`ocdpscufetxrykg6.azurecr.io/oncology-collab-demo:bef999a`

Rollback does not require an infrastructure change:

```powershell
az containerapp update `
  --resource-group oncology-collab-demo-platform-rg `
  --name oncology-collab-demo `
  --image ocdpscufetxrykg6.azurecr.io/oncology-collab-demo:bef999a
```

After rollback, rerun the protected health and access checks appropriate to that
older interface.
