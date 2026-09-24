# Azure deployment evidence

**Deployed:** 24 September 2026  
**Application:** `oncology-collab-demo`  
**Resource group:** `oncology-collab-demo-platform-rg`  
**URL:** `https://oncology-collab-demo.wittyrock-0461f613.westeurope.azurecontainerapps.io`

## Reviewed deployment

- Active image:
  `ocdpscufetxrykg6.azurecr.io/oncology-collab-demo:7e5a942`
- Active revision: `oncology-collab-demo--0000008`
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
  "federated_sources": 3,
  "prepared_versions": [1, 2],
  "event_grid_event": "azure-event-grid-imaging-001",
  "mdo_case_version": 2,
  "timeline_events": 23,
  "final_state": "clean"
}
```

Live Playwright then passed four checks against the protected URL:

- complete desktop closed-loop referral;
- desktop keyboard and axe checks;
- complete Pixel 7 closed-loop referral;
- Pixel 7 keyboard and axe checks.

The live screenshots are:

- [`evidence/live-closed-loop-desktop-chromium.png`](evidence/live-closed-loop-desktop-chromium.png)
- [`evidence/live-closed-loop-mobile-chromium.png`](evidence/live-closed-loop-mobile-chromium.png)

## Rollback

The previous stable image remains in ACR:

`ocdpscufetxrykg6.azurecr.io/oncology-collab-demo:6ded4aa`

Rollback does not require an infrastructure change:

```powershell
az containerapp update `
  --resource-group oncology-collab-demo-platform-rg `
  --name oncology-collab-demo `
  --image ocdpscufetxrykg6.azurecr.io/oncology-collab-demo:6ded4aa
```

After rollback, rerun the protected health and access checks appropriate to that
older interface.
