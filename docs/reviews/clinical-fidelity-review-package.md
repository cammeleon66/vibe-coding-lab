# Clinical-fidelity review package

**Status:** Ready for external oncology review; not clinically validated  
**Case:** synthetic `CRC-EU-001`  
**Review focus:** metastatic colorectal cancer with liver-limited metastases
after conversion therapy  
**Audience risk:** a clinically expert audience may reject the entire
demonstration if the dossier, imaging language, or presenter inference is
implausible

## What the reviewer is being asked to decide

1. Is the case trajectory plausible enough for a short stakeholder
   demonstration?
2. Are the evidence gaps and conflicts credible rather than theatrically
   convenient?
3. Does the late-imaging delta identify relevant questions without implying an
   automated resectability decision?
4. Is the human opinion appropriately bounded?
5. Would any screen or presenter sentence mislead an oncology audience about
   clinical evidence, institutional behavior, or decision authority?

## Case dossier to review

| Domain | Demonstrated content | Fidelity question |
| --- | --- | --- |
| Diagnosis | Metastatic colorectal adenocarcinoma with liver-limited metastases | Is the terminology internally consistent and appropriate for the intended pathway? |
| Treatment | Conversion-therapy timeline from a synthetic Milan source | Is the sequence plausible without implying a specific recommended regimen? |
| Pathology | PDF-derived synthetic pathology text with retained source | Are histology and wording credible and sufficiently bounded? |
| Molecular | Incomplete RAS/BRAF/MMR-MSI context remains visible | Are the missing elements relevant and described without overstating their immediate effect? |
| Baseline imaging | Synthetic DICOM metadata identifies original liver lesion sites | Are the segment references and baseline-review need plausible? |
| Restaging imaging | Synthetic MRI metadata describes changed visibility/size and a segment VIII relationship to the right hepatic vein | Is this an appropriate reason for renewed multidisciplinary assessment? |
| Decision boundary | The workspace refuses to decide treatment or resectability | Is the boundary clinically and rhetorically clear? |
| Responsibility | A fictional Utrecht oncologist records an opinion and assigns MDO coordination | Is this workflow plausible enough for a conceptual cross-border demonstration? |

## Claims that must remain bounded

**Acceptable**

- New imaging changes the evidence available for human reassessment.
- Original lesion sites, current findings, missing molecular evidence, and
  source conflicts can be reviewed together.
- A versioned case can carry provenance, unresolved issues, opinion, and next
  responsibility into a narrative MDO handoff.

**Not acceptable**

- The patient is resectable or unresectable.
- A specific operation, regimen, sequence, or referral is recommended.
- UMC Utrecht, Milan, or any named clinician actually uses these formats,
  pathways, permissions, or availability rules.
- The synthetic match proves credentialing, authorization, interoperability,
  or real-time availability.
- The MDO application received shared clinical state.

## Reviewer walkthrough

Review these artifacts in order:

1. `src/collab/fixtures/milan/referral.cda.xml`
2. `src/collab/fixtures/milan/pathology.pdf.txt`
3. `src/collab/fixtures/milan/treatment.local.json`
4. `src/collab/fixtures/milan/baseline-ct.dicom-metadata.json`
5. `src/collab/fixtures/milan/restaging-mri.dicom-metadata.json`
6. `src/collab/fixtures/utrecht/referral.fhir.json`
7. `src/collab/fixtures/utrecht/review-requirements.json`
8. [`../demo/evidence/state-update.jpg`](../demo/evidence/state-update.jpg)
9. [`../demo/evidence/state-completed.jpg`](../demo/evidence/state-completed.jpg)
10. [`../demo/presenter-guide.md`](../demo/presenter-guide.md)

## Review record

| Item | Reviewer result |
| --- | --- |
| Case trajectory | Pending external clinical review |
| Pathology language | Pending external clinical review |
| Molecular context | Pending external clinical review |
| Imaging/lesion language | Pending external clinical review |
| Human-opinion wording | Pending external clinical review |
| Presenter language | Pending external clinical review |
| Required corrections | None recorded yet |
| Approval for presentation | **Not granted by this package** |

This repository can prove software behavior, provenance, boundaries, and
presentation repeatability. It cannot self-certify oncology fidelity. External
review remains the one unresolved presentation gate from `RT-002`.

