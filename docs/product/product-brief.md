# Product brief: European oncology collaboration foundation

**Status:** Approved
**Version:** 0.2
**Date:** 2026-09-23
**Approval required before:** Architecture

## Decision requested

Approve the product direction for a presenter-led, synthetic-data demonstration in which an Italian oncologist discovers suitable European expert centres and clinicians, initiates a cross-border colorectal-oncology collaboration, and prepares the case for a narrative handoff to the existing autonomous MDO demonstration.

## Problem

Specialist oncology collaboration across European hospitals begins with a discovery problem: the referring clinician must identify where the right expertise exists, whether the centre and clinician are appropriate for the case, and which referral path or evidence conditions apply. Europe has expert networks and directories, but no universal authoritative catalogue proving that every doctor is eligible, authorized, compatible, and available for a specific case.

After an expert is found, collaboration remains constrained by fragmented records, inconsistent formats, missing evidence, manual coordination, and unclear responsibility. Clinicians may receive summaries without the original evidence needed to verify them, while new information can trigger more chasing, reconciliation, and rework.

For a patient with metastatic colorectal cancer and liver metastases, deciding whether conversion therapy has made liver-directed treatment feasible requires longitudinal imaging, pathology, molecular status, treatment history, response, clinical fitness, and expert judgement. The information may exist across institutions without arriving as one trustworthy, review-ready case.

## Target audience and users

- **Primary audience:** Professor Miriam Koopman and oncology stakeholders attending the presentation.
- **Primary in-product user:** A fictional, role-based UMC Utrecht colorectal oncologist.
- **Supporting actors:** Referring Milan oncologist, radiology and hepatobiliary expertise, case coordinator, and shared-platform operator.
- **Affected party:** A wholly synthetic patient whose case illustrates the workflow without implying real clinical use.

The product does not impersonate Professor Koopman or imply her endorsement.

## Desired outcome

The audience should conclude:

> If this trusted collaboration foundation existed, European oncology teams could work differently—not merely process today's referrals faster.

The demonstration succeeds when the audience can see that:

- heterogeneous hospital data can become a source-linked clinical workspace without pretending the source systems are clean;
- missing, conflicting, and newly arrived information remains visible;
- AI prepares and updates evidence but does not manufacture certainty or take clinical responsibility;
- institutional access and responsibility are explicit;
- the prepared case can flow into multidisciplinary review;
- clinical collaboration creates a foundation for separately governed research use.

## Product concept

A presenter begins as a synthetic Italian oncologist with a patient who has initially unresectable colorectal liver metastases after conversion therapy. The oncologist describes the clinical need. The platform discovers suitable verified European expert centres and teams, explains the match, and reveals eligible clinicians within those contexts. The presenter selects a fictional UMC Utrecht colorectal oncologist and initiates the cross-border request.

The collaboration workspace then assembles differently formatted clinical, pathology, molecular, and imaging information from two simulated Azure-backed institutional sources.

The initial workspace is useful but incomplete. It shows:

- the clinical question;
- relevant history and treatment;
- available source evidence;
- normalized information with source links;
- conflicts and missing information;
- uncertainty requiring human judgement;
- access and responsibility.

Original baseline liver imaging and a high-quality restaging MRI then arrive. The workspace updates without a new prompt, connects current findings to original lesion sites, highlights disappearing or changed lesions and vessel relationships, and shows which resectability questions can now be reconsidered.

The fictional Utrecht oncologist records a considered opinion and assigns the next responsibility. The case becomes visibly ready for multidisciplinary review and hands off narratively to the existing autonomous MDO demonstration.

## Requirements

### REQ-001: Expertise discovery

Allow the referring Italian oncologist to search from a clinical need and find suitable European expert centres and teams before selecting an eligible clinician.

### REQ-002: Explainable matching

For every result, show why it may fit: disease and treatment expertise, centre or network context, available referral pathway, accepted evidence types, geography or language where relevant, and synthetic availability. Do not claim exhaustive European coverage or real-time verification unless implemented and evidenced.

### REQ-003: Cross-border referral

Represent a referral from a synthetic Milan institution to a fictional UMC Utrecht colorectal oncologist, with a clear clinical question, urgency, sender, recipient, and responsibility state.

### REQ-004: Heterogeneous sources

Use two genuinely different source shapes and levels of completeness. Preserve source records and avoid presenting an unrealistically clean warehouse.

### REQ-005: Prepared workspace

Present the relevant longitudinal history, treatment, pathology, molecular status, imaging, and clinical context in one reviewable workspace.

### REQ-006: Provenance

Every important extracted or summarized clinical claim must link to its source, date, institution, and transformation status.

### REQ-007: Missingness and conflict

Show missing, inconsistent, outdated, or unmapped information explicitly. Do not silently resolve discrepancies.

### REQ-008: AI boundaries

Distinguish source fact, normalized value, AI-generated synthesis, uncertainty, and human judgement. The product must not prescribe treatment or claim clinical validation.

### REQ-009: Evidence update

When baseline imaging and restaging MRI arrive, update the workspace automatically and identify what changed, what remains uncertain, and which human conclusions require reassessment.

### REQ-010: Human responsibility

Allow the clinician to record a considered opinion, unresolved conditions, and the owner of the next action.

### REQ-011: MDO handoff

Mark the case as ready for multidisciplinary review and provide a controlled narrative launch or deep link to the existing MDO demonstration without requiring initial backend integration.

### REQ-012: Research boundary

Show that research use is a separate authorization context. A brief second-horizon glimpse may demonstrate cohort feasibility without implying that clinical access grants research permission.

### REQ-013: Demonstration reliability

Provide a deterministic, presenter-controlled path that can be rehearsed and completed without relying on unpredictable live AI behavior. Any live AI capability must be clearly labeled and may not silently replace the rehearsal path.

## Scope

### Must have

- One synthetic metastatic colorectal-cancer case.
- A clinical-need-driven European expert-centre and clinician discovery experience.
- Explainable, bounded matching that does not claim universal directory coverage.
- Two simulated institutional data sources with different formats.
- Evidence-linked case preparation.
- Visible missingness, conflicts, and transformation status.
- Baseline and restaging imaging update.
- Human review and next-action ownership.
- Presenter-led narrative.
- Narrative handoff to the autonomous MDO.
- Explicit demonstration and synthetic-data boundaries.

### Should have

- A compact view of source geography and access context.
- A comparison of the case before and after new imaging arrives.
- A visible research authorization boundary.
- A reusable case schema that does not hard-code every screen to one source format.

### Non-goals

- Production clinical use or medical-device claims.
- Real patient data.
- Real hospital-system integration.
- A real or exhaustive directory of European doctors.
- Real-time professional credentialing, availability, referral authorization, or interoperability certification.
- Automated treatment decisions.
- Full EHDS, MyHealth@EU, GDPR, or hospital-governance implementation.
- A complete European identity, consent, or research platform.
- Backend integration with the autonomous MDO in the first version.
- Provisioning Azure resources before architecture, cost review, and explicit approval.

## Success measures

### Audience evidence

- The audience can explain why the platform is more than a document viewer or AI summary.
- The audience understands why Utrecht was selected and what makes the expert match credible.
- The audience can identify the original source for an important clinical claim.
- The audience notices what is missing or conflicting without presenter explanation.
- The imaging update visibly changes the review state without claiming an automatic clinical answer.
- The handoff makes the relationship to multidisciplinary review understandable.
- The distinction between clinical and research authorization is clear.

### Demonstration quality

- The primary walkthrough is repeatable and bounded.
- Failure or unavailable evidence remains visible rather than producing a false success.
- The UI supports the story without generic dashboard clutter.
- The full narrative can be presented within an agreed event time.

## Assumptions

| ID | Assumption | What must be true |
| --- | --- | --- |
| ASM-001 | A prepared collaboration workspace is a compelling precursor to autonomous MDO. | The audience recognizes current coordination and evidence-reconciliation pain. |
| ASM-002 | Heterogeneous source data strengthens the story. | The differences remain understandable and clinically relevant rather than becoming an integration demo. |
| ASM-003 | Conversion and resectability is authentic for the audience. | The synthetic case and evidence are reviewed for clinical plausibility before presentation. |
| ASM-004 | A presenter-led experience is appropriate. | The event does not require unscripted hands-on clinician operation. |
| ASM-005 | A narrative handoff is sufficient for version one. | The audience values the end-to-end concept without demanding shared runtime state between products. |
| ASM-006 | A research glimpse broadens the vision without diluting it. | The clinical journey remains the dominant narrative. |
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
**Approved scope:** Product brief version 0.2, including expertise discovery, cross-border referral, heterogeneous evidence preparation, late imaging update, human responsibility, narrative MDO handoff, and separately authorized research epilogue.
**Rejected alternatives:** Direct individual-doctor discovery without centre context; full backend integration with the MDO in version one; research-first scope; clean FHIR-only demonstration.
**Approver:** User
**Approval date:** 2026-09-23
**Accepted conditions:** All seven conditions in `docs/reviews/product-red-team.md`.
**Re-approval conditions:** Material changes to expertise discovery, clinical use case, audience, core journey, MDO relationship, clinical/research boundary, or success measures.
