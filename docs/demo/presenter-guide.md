# Presenter guide: from Utrecht to European collaboration

**Target duration:** about five minutes

**Runtime:** synthetic referral rehearsal

**Live URL:** `https://oncology-collab-demo.wittyrock-0461f613.westeurope.azurecontainerapps.io`

**Boundary:** no real patients, clinicians, directory, hospital connection, or
clinical decision support

## Before the audience arrives

1. Open the live URL and enter the current shared demo access code. Obtain the
   code from the deployment owner; never add it to the repository or slides.
2. Select **Reset** and wait for confirmation that the synthetic journey was
   cleared.
3. Keep the browser at 100% zoom. The tested presenter viewports are 1440×960
   and Pixel 7.
4. Start at the Utrecht regional problem. Do not skip directly to the clinical
   role picker: the local proof establishes the pattern used by the rest of the
   story.

## Five-minute path

| Time | Presenter action | What to say |
| --- | --- | --- |
| 0:00–0:35 | Check the nearby patient-summary and imaging sources, then approve regional sharing. | “A Utrecht oncology team needs an MRI held by the hospital around the corner. The exchange finds the summary and images through hospital APIs. The originals stay at Stadshaven, and Dr Noor Jansen decides what may cross.” |
| 0:35–0:55 | Open the scale reveal and point from Utrecht to the Netherlands, Germany and Italy, and Europe. | “This is not a special local integration. Geography changes; source ownership, provenance, clinician approval, and named responsibility do not.” |
| 0:55–1:20 | Open the international referral, enter **Milan workspace**, and select **Giulia Moretti**. | “Now we apply the same pattern across borders. Dr Luca Bianchi starts from his active-patient list and selects the case that needs external review.” |
| 1:20–1:50 | Let the three Milan checks complete. Point to the EHR, document repository, and imaging archive requests. | “Again, each hospital-owned system is queried separately. Available and missing evidence stay visible without first centralizing every source record.” |
| 1:50–2:35 | Confirm the clinical question, query the directory, select **UMC Utrecht**, query requirements, and prepare version 1. | “The destination is explainable and bounded. Utrecht’s requirements remain visible, including missing baseline CT and liver MRI.” |
| 2:35–3:05 | Point to **Shared after approval** and **Remains in Milan**, then approve and send version 1. | “Structured context and provenance cross only after Dr Bianchi approves them. Original documents, images, and the Milan record stay in Milan.” |
| 3:05–3:40 | Continue as **Dr Eva van Dijk**, acknowledge version 1, record the provisional opinion, and request imaging. | “Utrecht acknowledges the exact version. Dr van Dijk’s opinion is separate from Milan’s assessment, and her evidence request gives a clinical reason.” |
| 3:40–4:15 | Return to Milan, receive the imaging event, review the version 1→2 delta, and approve version 2. | “Late evidence creates an immutable second version. The exchange shows what changed, but Dr Bianchi still decides whether the update crosses.” |
| 4:15–4:45 | Return to Utrecht, acknowledge version 2, record the final opinion, and accept it into the MDO. | “The final opinion applies to the acknowledged current version, and Utrecht names the meeting time.” |
| 4:45–5:00 | Return the outcome to Milan and point to the next responsibility. | “The loop closes with the opinion, MDO schedule, and exact next action. We solved the nearby problem first, then proved the same architecture at European scale.” |

## Clinical wording to preserve

- Say **source-linked referral package**, not “centralized patient record.”
- Say **regional exchange** for the nearby-hospital opening, not “internal
  transfer.”
- Say **deterministic preparation**, not “AI diagnosis” or “automated clinical
  decision.”
- Say **synthetic bounded directory**, not “European clinician registry.”
- Say **MDO acceptance**, not “treatment approval.”
- State that resectability and treatment remain human multidisciplinary
  conclusions.

Do not say that surgery is feasible, that Utrecht accepted a real referral, or
that any clinician, institution, permission, availability, or interoperability
claim is live.

## If something goes wrong

- **Access-code rejection:** confirm the current code with the deployment owner.
  Do not send access codes in URLs.
- **A source check fails:** leave the failed source visible and use **Retry
  failed source**. Do not describe the referral as ready.
- **State restore fails:** refresh once, then show the explicit error rather
  than describing a successful flow.
- **Evidence update fails:** explain that the previous valid case version is
  preserved. Reuse the same event ID only when retrying the same delivery.
- **Need a clean restart:** select **Reset** and wait for confirmation.

## Current visual evidence

| View | Evidence |
| --- | --- |
| Regional proof desktop | [`evidence/regional-proof-desktop-chromium.png`](evidence/regional-proof-desktop-chromium.png) |
| Regional proof mobile | [`evidence/regional-proof-mobile-chromium.png`](evidence/regional-proof-mobile-chromium.png) |
| European scale reveal desktop | [`evidence/scale-reveal-desktop-chromium.png`](evidence/scale-reveal-desktop-chromium.png) |
| European scale reveal mobile | [`evidence/scale-reveal-mobile-chromium.png`](evidence/scale-reveal-mobile-chromium.png) |
| Closed-loop desktop outcome | [`evidence/closed-loop-desktop-chromium.png`](evidence/closed-loop-desktop-chromium.png) |
| Closed-loop mobile outcome | [`evidence/closed-loop-mobile-chromium.png`](evidence/closed-loop-mobile-chromium.png) |
| Live Azure desktop outcome | [`evidence/live-closed-loop-desktop-chromium.png`](evidence/live-closed-loop-desktop-chromium.png) |
| Live Azure mobile outcome | [`evidence/live-closed-loop-mobile-chromium.png`](evidence/live-closed-loop-mobile-chromium.png) |
