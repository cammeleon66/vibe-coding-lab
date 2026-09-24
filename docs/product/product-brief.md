# Product brief: European oncology collaboration foundation

**Status:** Approved
**Version:** 0.3
**Date:** 2026-09-24
**Approval required before:** Architecture

## Decision requested

Build a five-minute, presenter-led demonstration of a closed-loop referral from Milan to Utrecht. The platform should assemble a trustworthy referral with little manual data chasing by calling hospital-owned APIs, preserving source ownership and provenance, and requiring clinicians to approve what crosses each institutional boundary.

## Problem

Specialist oncology collaboration across European hospitals begins with a discovery problem: the referring clinician must identify where the right expertise exists, whether the centre and clinician are appropriate for the case, and which referral path or evidence conditions apply. Europe has expert networks and directories, but no universal authoritative catalogue proving that every doctor is eligible, authorized, compatible, and available for a specific case.

After an expert is found, collaboration remains constrained by fragmented records, inconsistent formats, missing evidence, manual coordination, and unclear responsibility. Clinicians may receive summaries without the original evidence needed to verify them, while new information can trigger more chasing, reconciliation, and rework.

For a patient with metastatic colorectal cancer and liver metastases, deciding whether conversion therapy has made liver-directed treatment feasible requires longitudinal imaging, pathology, molecular status, treatment history, response, clinical fitness, and expert judgement. The information may exist across institutions without arriving as one trustworthy, review-ready case.

## Target audience and users

- **Primary audience:** Professor Miriam Koopman and oncology stakeholders attending the presentation.
- **Primary in-product users:** A fictional Milan referring oncologist and a fictional UMC Utrecht colorectal oncologist.
- **Supporting actors:** Milan source-system owners, Utrecht referral and MDO services, radiology and hepatobiliary expertise, and the collaboration platform.
- **Affected party:** A wholly synthetic patient whose case illustrates the workflow without implying real clinical use.

The product does not impersonate Professor Koopman or imply her endorsement.

## Desired outcome

The audience should conclude:

> Cross-border specialist referrals can become faster and more trustworthy without centralizing every hospital record.

The demonstration succeeds when the audience can see that:

- the platform uses authorized API calls to work with hospital-owned data;
- the audience can see what stays in Milan, what enters the referral package, and why;
- source provenance, missing evidence, approvals, transfers, and acknowledgements remain visible;
- platform automation prepares the package while clinicians make the clinical and sharing decisions;
- Utrecht can request missing evidence and receive an approved immutable update;
- the process closes with a specialist opinion, MDO acceptance, and a returned next action in Milan.

## Product concept

The demonstration starts with a role picker. The presenter enters Dr Luca Bianchi's Milan workspace, sees three synthetic active patients, and selects the patient whose care plan calls for external expertise.

The platform runs a visible federated data check against the Milan EHR, document repository, and PACS. A split view keeps the clinical purpose and the technical API activity visible together. The results show available evidence, missing evidence, provenance, and which large source files remain in Milan.

Dr Bianchi confirms the clinical question. The platform calls the European expert directory and Utrecht referral-requirements service, explains the match, and supports selection of Utrecht and Dr Eva van Dijk. It then assembles case version 1 using the approved hybrid sharing model: structured context and provenance enter the package while large source files remain available through authorized retrieval.

Dr Bianchi reviews the package, records his referral assessment, approves what will be shared, and sends case version 1. The story then moves through a clear role handoff to Dr van Dijk's Utrecht inbox.

Dr van Dijk acknowledges case version 1, records a provisional specialist opinion, and requests the missing imaging. When the evidence becomes available in Milan, the platform prepares case version 2. Dr Bianchi approves the update, and Dr van Dijk acknowledges the new version, finalizes the specialist opinion, and accepts the case into the Utrecht MDO.

The final Milan view shows the returned opinion, MDO acceptance, and next responsibility. A persistent activity timeline records the API calls, approvals, transfers, acknowledgements, evidence request, and clinical decisions.

## Requirements

### REQ-001: Expertise discovery

Start from the Milan clinician's active-patient worklist, then allow the clinician to confirm a clinical need and find suitable European expert centres and teams.

### REQ-002: Explainable matching

For every result, show why it may fit: disease and treatment expertise, centre or network context, available referral pathway, accepted evidence types, geography or language where relevant, and synthetic availability. Do not claim exhaustive European coverage or real-time verification unless implemented and evidenced.

### REQ-003: Cross-border referral

Represent a referral from a synthetic Milan institution to a fictional UMC Utrecht colorectal oncologist, with a clear clinical question, urgency, sender, recipient, and responsibility state.

### REQ-004: Federated data check

Call the simulated Milan EHR, document repository, and PACS through separate APIs. Show each request, its result, available evidence, missing evidence, and source ownership.

### REQ-005: Heterogeneous sources

Use two genuinely different source shapes and levels of completeness. Preserve source records and avoid presenting an unrealistically clean warehouse.

### REQ-006: Hybrid referral package

Assemble approved structured context and provenance into the referral package while keeping large source files in Milan for authorized retrieval.

### REQ-007: Provenance

Every important extracted or summarized clinical claim must link to its source, date, institution, and transformation status.

### REQ-008: Missingness and conflict

Show missing, inconsistent, outdated, or unmapped information explicitly. Do not silently resolve discrepancies.

### REQ-009: Automation boundaries

Distinguish source facts, normalized values, platform-prepared summaries, uncertainty, referral assessments, and specialist opinions. The product must not prescribe treatment or claim clinical validation.

### REQ-010: Milan sharing approval

Require Dr Bianchi to approve the defined referral package and every later update before it crosses from Milan to Utrecht.

### REQ-011: Utrecht receiving workflow

Give Dr van Dijk an incoming-referral view in which she acknowledges a case version, reviews source-linked evidence, records a specialist opinion, and requests missing evidence.

### REQ-012: Versioned evidence update

When requested imaging becomes available, prepare an immutable case version 2, show the change from version 1, require Milan approval, and require Utrecht acknowledgement.

### REQ-013: Closed-loop MDO outcome

Allow Dr van Dijk to finalize the specialist opinion and accept the named case version into MDO. Return the opinion, MDO state, and next responsibility to Milan.

### REQ-014: Activity timeline

Keep a persistent timeline of API calls, approvals, transfers, acknowledgements, evidence requests, and clinical decisions.

### REQ-015: Guided navigation

Use six plain-language stages. Completed and current stages may be revisited; future stages show the exact prerequisite instead of appearing broken.

### REQ-016: Demonstration reliability

Provide a deterministic, presenter-controlled path that can be rehearsed and completed without relying on unpredictable live AI behavior. Any live AI capability must be clearly labeled and may not silently replace the rehearsal path.

## Scope

### Must have

- One synthetic metastatic colorectal-cancer case.
- A Milan role, patient worklist, and Utrecht receiving role.
- Visible API calls to separate hospital-owned source systems.
- A clinical-need-driven European expert-centre and clinician discovery experience.
- Explainable, bounded matching that does not claim universal directory coverage.
- Two simulated institutional data sources with different formats.
- A hybrid referral package with a clear source-data boundary.
- Visible missingness, conflicts, and transformation status.
- A Utrecht evidence request and approved case-version update.
- Separate Milan referral assessment and Utrecht specialist opinion.
- Closed-loop MDO acceptance and returned next responsibility.
- A persistent cross-institution activity timeline.
- Presenter-led narrative.
- Explicit demonstration and synthetic-data boundaries.

### Should have

- A compact view of source geography and access context.
- A comparison of the case before and after new imaging arrives.
- A reusable case schema that does not hard-code every screen to one source format.
- An optional research appendix outside the primary journey.

### Non-goals

- Production clinical use or medical-device claims.
- Real patient data.
- Real hospital-system integration.
- A real or exhaustive directory of European doctors.
- Real-time professional credentialing, availability, referral authorization, or interoperability certification.
- Automated treatment decisions.
- Full EHDS, MyHealth@EU, GDPR, or hospital-governance implementation.
- A complete European identity, consent, or research platform.
- Production integration with a real MDO system.
- A research workflow in the primary demonstration journey.
- Provisioning Azure resources before architecture, cost review, and explicit approval.

## Success measures

### Audience evidence

- The audience can explain how the referral uses hospital-owned APIs without first centralizing every source record.
- The audience understands why Utrecht was selected and what makes the expert match credible.
- The audience can distinguish what stays in Milan from what enters the referral package.
- The audience can identify the original source for an important clinical claim.
- The audience notices what is missing or conflicting without presenter explanation.
- The audience sees Utrecht request missing evidence and Milan approve a versioned update.
- The audience can identify the separate decisions made by Dr Bianchi and Dr van Dijk.
- The final state clearly shows MDO acceptance, the returned specialist opinion, and the next responsibility.

### Demonstration quality

- The primary walkthrough is repeatable and bounded.
- Failure or unavailable evidence remains visible rather than producing a false success.
- The UI supports the story without generic dashboard clutter.
- The full narrative can be presented in about five minutes.

## Assumptions

| ID | Assumption | What must be true |
| --- | --- | --- |
| ASM-001 | A prepared collaboration workspace is a compelling precursor to autonomous MDO. | The audience recognizes current coordination and evidence-reconciliation pain. |
| ASM-002 | Heterogeneous source data strengthens the story. | The differences remain understandable and clinically relevant rather than becoming an integration demo. |
| ASM-003 | Conversion and resectability is authentic for the audience. | The synthetic case and evidence are reviewed for clinical plausibility before presentation. |
| ASM-004 | A presenter-led experience is appropriate. | The event does not require unscripted hands-on clinician operation. |
| ASM-005 | A simulated Utrecht receiving and MDO workflow is sufficient for this demonstration. | The audience values the closed-loop behavior without interpreting it as production integration. |
| ASM-006 | Showing both Milan and Utrecht roles strengthens the trust story. | The role changes remain clear and do not make the five-minute path feel fragmented. |
| ASM-007 | Finding an expert centre is a meaningful part of the current problem. | The target audience recognizes fragmented discovery and referral pathways as a real barrier. |

## Risks and constraints

- Clinical inaccuracy would undermine the entire demonstration.
- Synthetic data may appear too curated unless missingness and contradictions are credible.
- The experience may become an Azure integration showcase instead of a clinician workflow.
- A loose MDO handoff may feel disconnected if the visual and case continuity are weak.
- Naming real hospitals while simulating their data requires careful labeling.
- A synthetic expertise directory may be mistaken for a real, exhaustive, or endorsed network.
- Real Azure services introduce cost, deployment, identity, and reliability considerations requiring later approval.
- The exact source formats and Azure services remain architecture decisions.

## Evidence

- Professor Koopman's public profiles establish a focus on colorectal cancer, biomarkers, treatment optimization, and real-world outcomes.
- CAIRO5 establishes centralized multidisciplinary reassessment of initially unresectable colorectal liver metastases as a relevant clinical workflow.
- Cross-border tumor-board literature identifies benefits for complex cases and persistent problems in preparation, interoperability, governance, and provenance.
- Microsoft Research reports that tumor-board case preparation is time-consuming and that transparent source grounding matters for AI-assisted collaboration.
- Azure Health Data Services documents FHIR and DICOM capabilities relevant to later architecture analysis.
- The autonomous MDO repository demonstrates effective presenter patterns and explicit clinical boundaries.

## Approval record

**Status:** Approved
**Approved scope:** Product brief version 0.3, including role-based Milan and Utrecht workspaces, a three-patient Milan worklist, visible federated API calls, hybrid referral sharing, separate referral and specialist opinions, a Utrecht evidence request, an approved immutable update, MDO acceptance, and a closed-loop return to Milan.
**Rejected alternatives:** A cumulative single-page interface; technical review-condition checkboxes; an unexplained status-only journey rail; centralizing all source records; a research workflow in the main story; slogan-like or generic AI copy.
**Approver:** User
**Approval date:** 2026-09-24
**Accepted conditions:** Keep clinical and technical evidence visible together, use plain clinical language, and avoid generic AI claims or marketing-style headings.
**Re-approval conditions:** Material changes to expertise discovery, clinical use case, audience, core journey, MDO relationship, clinical/research boundary, or success measures.
