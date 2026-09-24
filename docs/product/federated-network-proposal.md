# Proposal: federated European oncology network (v0.5)

**Status:** Proposed — awaiting product-owner approval. Does not replace the
approved brief (v0.4) until approved.
**Date:** 2026-09-24
**Source:** product owner's demo flow (`federated_oncology_demo_flow.md`,
shared 2026-09-24) and feedback on the live storyline build.

## Feedback being addressed

> "It does look better, but it feels really like a scripted demo too much. I
> can click myself through things, I don't need 'Show what Utrecht receives',
> but at the top have a button with current role to look at different
> screens."

The current build (ADR-016) forces a linear 14-scene storyline with a scripted
advance button. The new flow asks for a product that feels like a real
European oncology network a clinician could use.

## Restated intent

- **Core message:** *One patient. Europe's expertise.* **Data stays. Insights
  travel.**
- **Hierarchy:** Federation → Clinical collaboration → Federated evidence →
  Autonomous MDO → AI. Federation is the hero; AI is a layer on top.
- **Audience outcome:** a clinician can reach the right European expert and
  query relevant European evidence without any hospital surrendering its data;
  the audience sees *what the clinician did → what the platform did → what
  crossed the boundary*.
- **Two modes, visibly distinct:** **Care sharing** (approved, minimised case
  package to a named clinician) and **Federated analytics** (question travels,
  local computation, only an aggregate returns).
- **Principle:** real infrastructure with synthetic clinical content.

## Story (10 minutes)

| Time | Beat | Role / screen |
| --- | --- | --- |
| 0:00 | Difficult case: Maria Janssen, 57F, mCRC, KRAS G12C, progression after FOLFOX + FOLFIRI. Tabs: Overview, Timeline, Pathology, Imaging, Molecular, Treatment, MDO. CTA **Request European peer review**. | NL treating oncologist |
| 1:00 | Search `KRAS G12C colorectal cancer` in the federated expertise catalogue (metadata only): Heidelberg, Milan, Antwerp. Select Heidelberg. | NL oncologist |
| 2:00 | Governed sharing checklist (diagnosis, treatment history, pathology, molecular, relevant imaging; not full EHR or identifiers). **Send secure case**. | NL oncologist |
| 3:00 | Activity monitor, side by side: authorized → policy check → minimisation 27→9 → identifiers removed → FHIR bundle → routing → delivery → received, one correlation ID. | Control room |
| 4:00 | Heidelberg environment (`SECURE CLINICAL ENVIRONMENT`), inbox, approved case package, expert opinion. | Heidelberg expert |
| 5:00 | **Compare with our patients**: cohort query runs locally in Heidelberg; aggregate only. *38 queried locally · 0 transferred.* | Heidelberg expert + control room |
| 6:00 | Peer review completed with supporting local evidence; received back in NL. | Both |
| 7:00 | **Run Autonomous MDO** over patient + peer review + federated evidence. | NL oncologist |
| 8:30 | Optional: **Turn this case into a research question**; European cohort counts per site, no central database. | Researcher view |
| 10:00 | Closing loop visual. | — |
| any | "This is actually real": **Disconnect Heidelberg** → *Heidelberg unavailable — federated result incomplete*; reconnect and rerun. | Control room |

## Proposed decisions (defaults chosen while the product owner was unavailable)

| ID | Decision | Proposed default | Alternatives |
| --- | --- | --- | --- |
| DEC-017 | Story | Replace Milan→Utrecht with Maria Janssen NL → Heidelberg. Drop the Utrecht opener (the new flow starts with the case). | Keep the Utrecht opener; keep both cases. |
| DEC-018 | Navigation | Role switcher in the top bar (NL oncologist · Heidelberg expert · Control room · later Researcher). Each role has an inbox/worklist and patient tabs; free clicking. Backend enforces **rules** (nothing crosses unapproved, opinion needs a received case), not **screen order**. A collapsible presenter checklist shows progress but never drives navigation. Supersedes ADR-016's linear storyline. | No checklist at all. |
| DEC-019 | Infrastructure (first increment) | Three Container Apps in the existing subscription: **NL hospital**, **Heidelberg hospital**, **federation hub**, each with its own storage account and managed identity; hospitals only reachable through the hub; Heidelberg's app can really be stopped for the disconnect test. | Single app simulating separation (no cost change); full two-subscription build with Entra, APIM, FHIR service and PostgreSQL OMOP (high cost/effort, separate approval). |
| DEC-020 | First-increment scope | Workstation + expert search, governed sharing with minimisation, activity monitor, Heidelberg peer review, local aggregate cohort query, disconnect failure mode. MDO and research cohort follow. | Everything at once. |

## Real vs simulated (first increment, DEC-019 default)

| Real | Synthetic / simplified |
| --- | --- |
| Separate hospital services, stores and identities | Patient, opinions, expertise catalogue, cohort numbers |
| HTTP calls hub ↔ hospitals with one correlation ID | Policy rules are code in the hub, not a policy product |
| Data minimisation producing a FHIR-shaped bundle (resource counts from the data) | FHIR-shaped JSON, not a FHIR service |
| Local cohort computation over a local OMOP-shaped table; aggregate only, small-cell suppression | OMOP-shaped SQLite/JSON, not a full CDM |
| Audit trail in the hub; real failure when Heidelberg is stopped | Access code for the demo, not Entra sign-in |

Deferred for separate approval: separate subscriptions, Entra ID sign-in,
API Management, Azure Health Data Services FHIR, PostgreSQL OMOP.

## Acceptance criteria (first increment)

1. There is no scripted "next" button; every beat is reachable by switching role and clicking the clinical action.
2. The role switcher always shows the current role and institution; switching never changes backend state.
3. Nothing reaches Heidelberg until the NL oncologist sends an approved checklist; unchecked items and identifiers never leave NL (verified by tests on the delivered bundle).
4. The activity monitor shows each event with timestamp, source, destination, correlation ID and status, and opens the actual request and response.
5. The cohort query executes inside the Heidelberg service and returns aggregates only; the UI shows records queried locally and records transferred (0).
6. With Heidelberg stopped, NL shows *Heidelberg unavailable — federated result incomplete*; after reconnecting, a rerun succeeds.
7. Reset restores a clean state across all three services.
8. Desktop and mobile, keyboard and axe checks pass; clinical UI avoids "demo patient", agent-grid and chat-first patterns.

## Risks and open questions

- **Name clash:** the flow uses patient *Maria Janssen* and clinician *Dr Janssen*. Proposed: rename the clinician (e.g. Dr Pieter de Boer) so the monitor never looks like the patient is the requester.
- **Real institution names** (Heidelberg, Milan, Antwerp, Oxford, UMC) with fictional clinicians and numbers: keep the visible *synthetic* labelling and the existing "no endorsement" wording.
- **Clinical claims:** response rates and "treatment A/B" must stay generic and marked synthetic; the MDO output must not read as a treatment recommendation. The word "Autonomous" needs clinical review; it conflicts with the brief's "clinicians decide" rule.
- **Cost:** three Container Apps scaling to zero plus two small storage accounts is expected to add under €20/month (estimate; verify with the Azure pricing calculator before provisioning). Existing budget alert (€35) and expiry tag (2026-10-07) apply.
- **Deadline unknown:** it decides whether MDO and research ship in the same release.
- **Rework:** the frontend scene renderer and the 14-scene backend storyline are largely replaced; the federated query, approval, audit, Event Grid and deployment pieces are reused.

## Approval requested

Approve or amend DEC-017 to DEC-020, then implementation starts with INC-017
(see `docs/implementation/plan.md`).
