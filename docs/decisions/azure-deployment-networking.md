# Azure deployment networking decision

**Decision ID:** DEC-007  
**Status:** Awaiting re-approval  
**Date:** 2026-09-23  
**Related issue:** GitHub #6 / INC-007

## Approved baseline

The user approved a West Europe deployment in subscription
`ME-MngEnvMCAP670682-simonecammel-1` with:

- three Blob Storage accounts for Milan, Utrecht, and shared collaboration
  state;
- a scale-to-zero Container App and Basic Azure Container Registry;
- managed identity, presenter Entra authentication, Event Grid, and bounded
  monitoring;
- a EUR 10 monthly budget alert;
- no Azure OpenAI or Fabric deployment;
- teardown after 14 days.

The deployment approval followed the durable recommendation in GitHub issue #6
and the user response, “ok lets fix this.” It covered the Entra application and
managed-identity role assignments described in that recommendation.

## Evidence from the deployment attempt

The subscription created the approved base resources but forced
`publicNetworkAccess=Disabled` on every storage account, overriding the Bicep
request for an enabled endpoint. Reapplying the setting did not change the
effective configuration. The deployer and the future Container App therefore
could not reach Blob data through the approved public-endpoint design.

No application became live. The base resources and budget were submitted for
deletion immediately after the constraint was confirmed.

## Options requiring a new decision

| Option | Consequence | Estimated low-traffic monthly cost |
| --- | --- | --- |
| Three private endpoints | Preserves the approved three-account isolation; adds a VNet-integrated Container Apps environment, three Blob private endpoints, and private DNS. | Approximately EUR 27–35 |
| One storage account/private endpoint | Reduces private-link cost but changes account-level source isolation to container-level isolation. | Approximately EUR 12–15 |
| Different subscription | Preserves the original architecture and approximate EUR 5–10 estimate if that subscription permits public Blob endpoints. | Subscription dependent |
| Stop | Keep the local deterministic rehearsal only. | No Azure demo spend |

The estimates are planning ranges, not guarantees. Private endpoint and
registry charges are the primary predictable drivers; monitoring remains
bounded.

## Recommendation

Approve the three-private-endpoint option with a EUR 35 budget alert if the
account-level isolation is important to the demonstration. Otherwise, select a
different explicitly approved development subscription that permits public
Blob endpoints. Do not silently consolidate storage accounts.

## Re-approval required

The user must select an option and approve its subscription, budget, identity,
networking, and teardown impact before another deployment attempt.
