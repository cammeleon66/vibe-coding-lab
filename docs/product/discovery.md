# Product discovery: European oncology collaboration demo

**Status:** Product direction approved; ready for architecture
**Last updated:** 2026-09-23
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

**Decision:** End with a narrative handoff to the existing autonomous MDO demonstration rather than initially integrating the two backends.
**Approved by:** User
**Date:** 2026-09-23
**Implications:** The collaboration platform must visibly prepare a review-ready case and preserve a future integration seam, but the first version may use a controlled launch or deep link.

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

## JOURNEY-001: Clinical journey under consideration

1. A synthetic Italian oncologist defines the clinical need for a patient with colorectal liver metastases.
2. The platform finds suitable verified European expert centres and teams, then eligible clinicians within them.
3. The platform explains why Utrecht is a credible match and what referral or evidence conditions apply.
4. The Italian oncologist selects the fictional Utrecht colorectal oncologist and initiates the request.
5. The receiving oncologist sees the clinical question, urgency, sender, authorization context, and responsibility.
6. The platform assembles information from two differently structured institutional sources.
7. The workspace distinguishes source facts, normalized values, conflicts, missing information, and AI-generated synthesis.
8. Important summary claims link to their source evidence.
9. Imaging, pathology, molecular status, prior treatment, response, and patient fitness support resectability review.
10. Original baseline liver imaging and a restaging MRI arrive; the workspace links lesion history, highlights new anatomical evidence, and identifies which conclusions require reassessment.
11. The human clinician records a considered opinion and the responsible next action.
12. The prepared case hands off narratively to the autonomous MDO.
13. The presentation points toward a separately authorized research workspace without conflating clinical and research permissions.

This journey is approved as the product direction. Architecture must preserve it or return for re-approval.

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
| ASM-005 | The research workspace should appear as a second horizon rather than a full first-demo workflow. | Medium | Research collaboration is equally important to the immediate audience outcome. |
| ASM-006 | Two simulated institutions are sufficient to establish a European platform story. | Medium | The audience needs a third role, such as a shared platform or laboratory, to understand the governance boundary. |
| ASM-007 | Expert-centre discovery is a compelling first act rather than administrative preamble. | Medium-high | The audience already knows whom to contact and sees no discovery problem. |

## Risks

- Building a generic data platform rather than a clinical collaboration experience.
- Showing AI as making or recommending a treatment decision instead of preparing evidence for human judgement.
- Overloading the demonstration with clinical collaboration, research, interoperability, identity, and governance in one journey.
- Making the synthetic case medically implausible or too similar to a real patient.
- Implying Professor Koopman's endorsement, preferences, or fictional clinical decisions.
- Claiming exhaustive European clinician coverage or real credential, availability, authorization, or interoperability verification.
- Selecting Azure services before requirements justify them.
- Creating meaningful Azure spend before explicit cost approval.

## Open questions

- What is the one dramatic moment that should make the audience recognize the platform's value?
- Which two institutional source formats best represent credible messy reality?
- What research-workspace glimpse is sufficient to establish the broader foundation?
