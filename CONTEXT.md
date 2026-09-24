# Federated Oncology Collaboration

This context covers synthetic regional and cross-border collaboration between
hospital-owned oncology workspaces. It defines the clinical and collaboration
terms used throughout the demonstration.

## People and workspaces

**Referring clinician**:
The clinician who selects the patient, states the referral question, approves evidence sharing, and sends updates from the originating hospital. In this demonstration, this is Dr Luca Bianchi in Milan.
_Avoid_: Sender, operator

**Receiving specialist**:
The clinician who reviews the referral at the expert centre, requests missing evidence, records a specialist opinion, and accepts the case for multidisciplinary review. In this demonstration, this is Dr Eva van Dijk in Utrecht.
_Avoid_: Reviewer, recipient

**Institutional workspace**:
The hospital-owned view in which a clinician sees local patients, permitted evidence, incoming referrals, and assigned actions.
_Avoid_: Dashboard, portal

**Regional exchange**:
An approved exchange between separate nearby hospitals in the same care region.
It uses the same source ownership, provenance, and clinician-approval rules as
cross-border collaboration.
_Avoid_: Internal transfer, shared database

**Collaboration scale**:
The geographic scope across which the same exchange pattern operates: nearby
hospitals, a national network, or an international network. Scale does not
change source ownership or clinician responsibility.
_Avoid_: Product tier, deployment size

## Storyline

**Storyline**:
The fixed, backend-owned sequence of 14 scenes grouped into three chapters:
two hospitals in Utrecht (steps 1–4), the European network (step 5), and Milan
to Utrecht (steps 6–14). The backend decides the current scene, whether it may
advance, and the label of the advance button; the frontend only renders it.
_Avoid_: Wizard, flow, tab

**Scene**:
One screen of the storyline with one responsible actor, one clinical purpose,
and one advance action. Completed scenes can be reopened read-only.
_Avoid_: Page, phase

**Handover**:
The visible transfer of responsibility when consecutive scenes have different
actors, stating who handed over and what was carried.
_Avoid_: Role switch, login as

**Audit log**:
The drawer listing every hospital-system request made by the exchange agent,
with the owning system and endpoint.
_Avoid_: Debug console, API panel

## Referral and evidence

**Federated data check**:
A set of authorized requests to hospital-owned systems that reports which evidence is available without first centralizing every source record.
_Avoid_: Import, synchronization

**Source evidence**:
A hospital-owned clinical record, document, image, or observation that remains identifiable by institution, format, date, and source location.
_Avoid_: Raw data, attachment

**Referral package**:
The approved information sent to the expert centre. It contains structured clinical context and provenance while large source files may remain at the originating hospital for authorized retrieval.
_Avoid_: Case dump, complete patient record

**Referral assessment**:
The referring clinician's account of the clinical question, relevant context, and reason for requesting specialist input.
_Avoid_: Human opinion, final opinion

**Specialist opinion**:
The receiving specialist's considered clinical response after reviewing the referral package and available source evidence.
_Avoid_: AI conclusion, automated recommendation

## State and responsibility

**Case version**:
An immutable referral package state created when approved evidence or clinical context changes.
_Avoid_: Latest record, overwrite

**Sharing approval**:
A deliberate action by the referring clinician that authorizes a defined referral package or update to cross the institutional boundary.
_Avoid_: Checkbox consent, automatic send

**Receiving acknowledgement**:
The receiving specialist's confirmation that a specific case version arrived and is the version under review.
_Avoid_: Sync complete

**Evidence request**:
A request from the receiving specialist for evidence that is needed to continue review.
_Avoid_: Missing-data condition

**MDO acceptance**:
The receiving specialist's decision that a named case version is ready to enter multidisciplinary review.
_Avoid_: Handoff manifest, MDO checkbox

**Next responsibility**:
The named person or team and concrete action that must happen next.
_Avoid_: Workflow state, owner field

**Activity timeline**:
The ordered record of data requests, approvals, transfers, acknowledgements, evidence requests, and clinical decisions across both institutions.
_Avoid_: System log, audit console
