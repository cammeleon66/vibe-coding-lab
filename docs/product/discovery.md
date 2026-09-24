# Product discovery: European oncology collaboration demo

**Status:** Revised product direction approved; implementation in progress
**Last updated:** 2026-09-24
**Primary audience:** Professor Miriam Koopman and oncology stakeholders in the room
**Presenter:** Product/demo presenter

## USER-001: Original intent

Make a future European oncology collaboration foundation tangible:

- an oncologist collaborates across borders as naturally as within one hospital;
- the patient does not carry information between institutions;
- a prepared workspace presents the clinical question, relevant history, original evidence, missing information, changes, uncertainty, and required human judgement;
- summaries remain connected to source evidence;
- access follows appropriate permissions;
- clinicians retain responsibility and make the next action explicit;
- separately authorized research use does not inherit clinical-care permissions;
- the audience should leave asking what they could build on the foundation.

The product is a demonstration, not a production clinical system.

## Current product hypothesis

A presenter-led demonstration begins with a synthetic Italian oncologist searching for appropriate European expertise for a patient with metastatic colorectal cancer and liver metastases. The platform identifies verified expert centres and teams, explains why they fit the clinical need, reveals eligible clinicians, and supports selection of a fictional UMC Utrecht colorectal oncologist.

The oncologist then initiates a cross-border request. Two simulated institutions hold differently structured, incomplete oncology data in real Azure-backed sources. The platform prepares an evidence-linked clinical workspace, shows missing and conflicting information, incorporates new evidence, and supports a human decision about conversion therapy and liver-metastasis resectability.

The demonstration should prove that useful cross-border collaboration does not require every hospital to first create a perfect data warehouse.

## Approved discovery decisions

### DEC-001: Demonstration boundary

**Decision:** Build a stakeholder demonstration using synthetic data and a real backend.
**Approved by:** User
**Date:** 2026-09-23
**Implications:** Hospital systems may be simulated; no real patient data; no claim of clinical validation or production readiness.

### DEC-002: Heterogeneous source systems

**Decision:** Represent two Azure-backed institutional data sources with different formats, quality, and completeness.
**Approved by:** User
**Date:** 2026-09-23
**Implications:** Preserve source fidelity, provenance, missingness, and conflicts rather than presenting an unrealistically clean warehouse.

### DEC-003: Clinical anchor

**Decision:** Use conversion therapy and liver-metastasis resectability in metastatic colorectal cancer as the central clinical decision.
**Approved by:** User
**Date:** 2026-09-23
**Rationale:** This aligns with Professor Koopman's publicly documented colorectal-cancer and CAIRO5 focus and naturally requires multidisciplinary imaging, pathology, molecular, and treatment evidence.

### DEC-004: Presentation mode

**Decision:** The user presents the demo while Professor Koopman is in the audience.
**Approved by:** User
**Date:** 2026-09-23
**Implications:** Optimize for a controlled, compelling presenter journey rather than unsupported self-service operation.

### DEC-005: Clinician representation

**Decision:** Use a fictional, role-based UMC Utrecht colorectal oncologist in the product. Tailor the scenario to Professor Koopman's public specialty without impersonating her or implying endorsement.
**Approved by:** User
**Date:** 2026-09-23

### DEC-006: Decisive evidence update

**Decision:** During the demonstration, original baseline liver imaging and a high-quality restaging liver MRI arrive after the initial referral.
**Approved by:** User
**Date:** 2026-09-23
**Implications:** The workspace must connect current findings to original lesion sites, show newly available vessel and anatomical detail, identify changed or disappearing lesions, and make clear which resectability questions can now be reconsidered by humans.

### DEC-007: Autonomous MDO relationship

**Status:** Superseded by DEC-010.
**Decision:** The original version ended with a narrative handoff to the existing autonomous MDO demonstration rather than integrating the two backends.
**Approved by:** User
**Date:** 2026-09-23
**Superseded on:** 2026-09-24
**Reason:** The approved redesign now includes a simulated Utrecht receiving workflow, evidence request, version acknowledgement, MDO acceptance, and returned outcome inside this demonstration.

### DEC-008: Expertise discovery model

**Decision:** Discover verified expert centres and teams first, then show eligible clinicians within the selected context.
**Approved by:** User
**Date:** 2026-09-23
**Rationale:** Europe has expert-centre networks and referral pathways, but no authoritative universal directory proving that every doctor is interoperable, authorized, appropriate, and available for a specific case.
**Implications:** Matching must explain specialty fit, disease expertise, network or credential context, referral pathway, accepted evidence types, and availability without claiming exhaustive EU coverage.

### DEC-009: Product brief approval

**Decision:** Approve `docs/product/product-brief.md` version 0.2 with the conditions recorded in `docs/reviews/product-red-team.md`.
**Approved by:** User
**Date:** 2026-09-23
**Re-approval conditions:** Material changes to expertise discovery, clinical use case, audience, core journey, MDO relationship, clinical/research boundary, or success measures.

### DEC-010: Closed-loop federated referral

**Decision:** Replace the one-sided referral-to-handoff story with a closed loop across visible Milan and Utrecht workspaces.
**Approved by:** User
**Date:** 2026-09-24
**Implications:** The main journey starts from a Milan patient worklist, shows federated API calls, requires explicit sharing approvals, switches to the Utrecht receiving role, handles a requested evidence update, ends with MDO acceptance and a returned specialist opinion, and removes research from the primary path.

## JOURNEY-001: Approved clinical journey

1. The presenter chooses a synthetic clinical role and enters Dr Luca Bianchi's Milan workspace.
2. Dr Bianchi selects the referral candidate from three synthetic active patients.
3. The platform calls the Milan EHR, document repository, and PACS and shows the result of each request.
4. Dr Bianchi confirms the clinical question.
5. The platform calls the European expert directory and Utrecht referral-requirements service.
6. Dr Bianchi selects Utrecht and Dr Eva van Dijk.
7. The platform prepares case version 1 and distinguishes information in the referral package from source evidence that stays in Milan.
8. Dr Bianchi records the referral assessment, approves the package, and sends it.
9. The presenter follows a guided role handoff to Dr van Dijk's Utrecht inbox.
10. Dr van Dijk acknowledges case version 1, records a provisional specialist opinion, and requests missing imaging.
11. New imaging becomes available in Milan and the platform prepares case version 2.
12. Dr Bianchi approves the update; Dr van Dijk acknowledges the new version.
13. Dr van Dijk finalizes the specialist opinion and accepts case version 2 into the MDO.
14. Milan receives the opinion, MDO state, and next responsibility.

A persistent activity timeline shows API calls, approvals, transfers, acknowledgements, evidence requests, and clinical decisions. The primary path contains no research workflow.

## Evidence and inspiration

- Professor Koopman's public clinical and research focus includes colorectal and anal cancer, biomarkers, treatment optimization, real-world outcomes, and metastatic colorectal cancer.
- CAIRO5 used centralized multidisciplinary expert reassessment of initially unresectable colorectal liver metastases during conversion therapy.
- Relevant case evidence includes imaging, pathology, RAS/BRAF status, MMR/MSI status, prior treatment and response, extrahepatic disease, patient fitness, and liver-remnant considerations.
- Cross-border tumor boards report value for complex and rare cases but face case-preparation, interoperability, governance, language, and evidence-provenance challenges.
- Azure Health Data Services provides relevant FHIR and DICOM patterns, but service selection remains an architecture decision.
- The `jochenvw/mdt-observatory` repository provides useful interaction patterns: deterministic rehearsal, visible uncertainty, source-linked evidence, explicit human steering and concurrence, captured decisions, and clear demonstration boundaries.
- A credible initial source contrast is a Milan-side legacy document and imaging flow (for example CDA/XML, PDF/pathology reports, DICOM, and local codes) against a Utrecht-side structured FHIR/BgZ-style view that still preserves source documents. This remains a product-level scenario, not an approved architecture.

### Initial sources

- UMC Utrecht / Utrecht University public profiles for Professor Miriam Koopman
- Dutch Colorectal Cancer Group: CAIRO5
- CAIRO5 publications and multidisciplinary resectability analyses
- European multidisciplinary tumor-board research
- Microsoft Research: tumor-board case preparation
- Microsoft Learn: Azure Health Data Services, FHIR, and DICOM
- `jochenvw/mdt-observatory` README, architecture, and presenter walkthrough

## Assumption register

| ID | Assumption | Confidence | What would invalidate it |
| --- | --- | --- | --- |
| ASM-001 | A prepared cross-border case workspace is a compelling precursor to the autonomous MDO demonstration. | Medium-high | The audience sees no unmet problem before the MDO begins. |
| ASM-002 | Heterogeneous source data is more persuasive than a clean, standardized dataset. | High | Data complexity distracts from rather than strengthens the clinical story. |
| ASM-003 | Liver-metastasis conversion and resectability creates an authentic decision for the target audience. | High | Professor Koopman considers another colorectal workflow materially more relevant. |
| ASM-004 | A presenter-led journey is the best format for the event. | High | The event requires hands-on clinician operation or open-ended exploration. |
| ASM-005 | Research should remain outside the primary five-minute journey. | High | The audience requires research reuse to understand the referral outcome. |
| ASM-006 | Two simulated institutions are sufficient to establish a European platform story. | Medium | The audience needs a third role, such as a shared platform or laboratory, to understand the governance boundary. |
| ASM-007 | Expert-centre discovery is a compelling first act rather than administrative preamble. | Medium-high | The audience already knows whom to contact and sees no discovery problem. |

## Risks

- Building a generic data platform rather than a clinical collaboration experience.
- Showing platform automation as making or recommending a treatment decision instead of preparing evidence for human judgement.
- Overloading the demonstration with clinical collaboration, research, interoperability, identity, and governance in one journey.
- Making the synthetic case medically implausible or too similar to a real patient.
- Implying Professor Koopman's endorsement, preferences, or fictional clinical decisions.
- Claiming exhaustive European clinician coverage or real credential, availability, authorization, or interoperability verification.
- Selecting Azure services before requirements justify them.
- Creating meaningful Azure spend before explicit cost approval.

## Open questions

No product-scope question currently blocks implementation. Implementation risks and
dependencies are tracked in GitHub issues #7–#13 and
`docs/implementation/plan.md`.
