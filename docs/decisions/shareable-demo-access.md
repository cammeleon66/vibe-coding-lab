# Shareable demo access decision

**Decision ID:** DEC-008  
**Status:** Approved  
**Date:** 2026-09-24  
**Supersedes:** Presenter-access portions of the approved architecture and DEC-007

## Context

The deployed application was healthy, but Microsoft Entra authentication
redirected every browser visitor into the deployment tenant. That prevented the
owner from opening the demo naturally and prevented sharing it with external
participants.

The user requested a simpler secret-key-style mechanism so the demo can be
shared. The data remains entirely synthetic, but the application includes
state-changing presenter actions and should not be exposed as an unrestricted
public link.

## Decision

Replace presenter Entra authentication with an application-level shared access
code:

- store the access code and an independent session-signing secret only as Azure
  Container App secrets;
- present a dedicated access-code page rather than putting a secret in the URL;
- issue a signed, HttpOnly, SameSite session cookie valid for 12 hours;
- require the session for the UI and application APIs;
- keep `/api/health` anonymous;
- keep the Event Grid callback outside the presenter session while retaining
  its separate delivery secret;
- remove the no-longer-needed Entra application registration and disable
  Container Apps built-in authentication.

## Consequences

- The owner can share one demo URL and one revocable code with external
  participants.
- The code is appropriate only for this synthetic, time-limited demonstration;
  it is not clinician identity, authorization, or a production authentication
  design.
- Anyone holding the code receives the same presenter capability, so it should
  be shared only with intended demo participants and rotated if disclosed.
- No Azure service, private endpoint, or meaningful cost is added.
- Real patient data remains prohibited.

## Re-approval conditions

Reconsider the identity model before using real data, supporting distinct users
or permissions, retaining the environment beyond the approved demo period, or
moving toward production.
