# Product red-team review

**Reviewed artifact:** `docs/product/product-brief.md` version 0.2
**Date:** 2026-09-23
**Status:** Conditions accepted with product approval

## Overall assessment

The proposed demo has a strong audience fit and a coherent end-to-end narrative from expert discovery to multidisciplinary review. It deserves to proceed to architecture only if the product approval accepts the explicit demonstration boundary and the team treats discovery claims, clinical plausibility, source provenance, and the MDO handoff as validation obligations rather than presentation polish.

## Findings

| ID | Severity | Finding | Evidence and assumptions | Recommendation | User decision |
| --- | --- | --- | --- | --- | --- |
| RT-001 | High | The product may become integration theatre: two Azure sources could look technically impressive without proving a better clinical decision workflow. | The vision emphasizes collaboration and judgement; heterogeneous formats are valuable only when they expose a real clinical friction. | Make every source-system difference affect missingness, verification, change detection, or responsibility. Remove data-format details that do not change the clinical story. | Accepted. |
| RT-002 | High | Clinical inaccuracy or an implausible resectability narrative would destroy trust with the target audience. | The audience includes a leading colorectal oncologist. Public research can frame the scenario but cannot validate the final synthetic case. | Require domain-expert review of the case dossier, lesion timeline, molecular context, and presenter language before the final demo. | Accepted as mandatory before presentation. |
| RT-003 | High | The handoff to the autonomous MDO may feel like two unrelated demos. | Version one deliberately avoids backend integration. | Preserve the same case ID, clinical question, evidence version, unresolved issues, and visual transition across the handoff. Do not imply a live data integration if none exists. | Accepted. |
| RT-004 | Medium | The demo could imply that data normalization resolves semantic disagreement. | Mapping CDA, local codes, FHIR, and DICOM does not make clinical meaning automatically equivalent. | Show transformation status, unmapped values, source context, and human-confirmed mappings. | Accepted. |
| RT-005 | Medium | The research-workspace glimpse may distract from the clinical story or imply unlawful secondary use. | The vision includes research, but the selected wedge is clinical. | Keep research to a short, separately authorized epilogue that demonstrates the boundary rather than a complete workflow. | Accepted. |
| RT-006 | Medium | Using named institutions may be interpreted as representing their actual systems or governance. | The scenario uses Milan and Utrecht for narrative credibility but no institutional integration has been validated. | Label institutions and data as simulated; avoid claims about their real formats, processes, or permissions. | Accepted. |
| RT-007 | Medium | A deterministic rehearsal can conceal whether the underlying product behavior is real. | The reference MDO separates rehearsal and live modes clearly. | Label rehearsal explicitly, keep backend state transitions real, and identify any scripted evidence arrival. Never present scripted behavior as autonomous discovery. | Accepted. |
| RT-008 | Low | The product may overfit one expert and fail to communicate a reusable platform foundation. | Tailoring to Professor Koopman's specialty is intentional, but the larger vision is European oncology collaboration. | Make the case specific while keeping platform concepts—source, permission, provenance, update, responsibility—visibly reusable. | No immediate decision required. |
| RT-009 | High | “Find all interoperable doctors” would be a misleading product claim. | ERNs and EURACAN expose expert networks and centres; ESMO supports professional networking; no authoritative universal directory establishes case-specific credentialing, authorization, compatibility, availability, and referral eligibility for every European oncologist. | Discover verified or curated expert centres first, show clinicians within that context, explain match criteria, and label the demonstration directory as synthetic. | Accepted during discovery. |
| RT-010 | Medium | Expert discovery may become a superficial marketplace screen disconnected from clinical collaboration. | A directory alone does not establish permission, referral readiness, or evidence needs. | Make the selected centre's required referral pathway and evidence conditions shape the case preparation that follows. | Accepted. |

## Stronger alternatives considered

### Alternative A: Generic cross-border oncology dashboard

Rejected because it would be easier to build but less clinically credible and less effective at demonstrating judgement, provenance, and changing evidence.

### Alternative B: Full backend integration with the autonomous MDO

Deferred because it adds coupling and architecture risk before the collaboration product has proved its own value.

### Alternative C: Research-first federated cohort explorer

Deferred because it weakens the immediate clinician story and introduces a separate governance problem before the primary clinical experience is established.

### Alternative D: Clean FHIR-only demonstration

Rejected because it contradicts the intended “messy reality” and risks implying that standardization alone solves collaboration.

## Recommendation

Approve product brief version 0.2 with these conditions:

1. The expertise directory is explicitly synthetic and bounded; it does not claim exhaustive EU coverage or real credential verification.
2. Expert matching explains why a centre and clinician fit and carries referral/evidence conditions into the collaboration workflow.
3. The final synthetic case receives credible oncology review before presentation.
4. The first demo remains clinical-first; research is a separately authorized epilogue.
5. The MDO connection remains a clearly labeled narrative handoff.
6. Azure and source formats serve the clinical story and are not treated as the product.
7. No Azure resources are provisioned until architecture and cost review are complete and explicitly approved.
