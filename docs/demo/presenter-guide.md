# Presenter guide: Milan-to-Utrecht referral

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
4. Start at **Clinical roles** with Dr Luca Bianchi marked **Continue here**.

## Five-minute path

| Time | Presenter action | What to say |
| --- | --- | --- |
| 0:00–0:35 | Open **Milan workspace**, then select **Giulia Moretti**. | “Dr Luca Bianchi starts from his active-patient list. Two patients remain in local care; Giulia needs external review of conversion response and liver resectability.” |
| 0:35–1:10 | Let the three Milan checks complete. Point to the EHR, document repository, and imaging archive requests. | “The exchange asks each hospital-owned system separately. It records what is available and what is missing; it does not first copy every source record into one central platform.” |
| 1:10–2:00 | Continue, confirm the clinical question, query the directory, select **UMC Utrecht**, query requirements, and prepare version 1. | “Utrecht is selected through clinical fit, evidence compatibility, language, and synthetic availability. Its requirements remain visible, including missing baseline CT, liver MRI, and molecular context.” |
| 2:00–2:35 | Point to **Shared after approval** and **Remains in Milan**. Read the prepared referral assessment, then approve and send version 1. | “Structured context and provenance cross after Dr Bianchi approves them. Original documents, images, and the Milan record stay in Milan for authorized retrieval.” |
| 2:35–3:15 | Continue as **Dr Eva van Dijk**, acknowledge version 1, record the provisional opinion, and request the missing imaging. | “Utrecht acknowledges the exact version under review. Dr van Dijk’s opinion is separate from the Milan referral assessment, and her request names both the evidence and the clinical reason.” |
| 3:15–4:00 | Return to Milan, receive the imaging event, review the version 1→2 delta, and approve sharing version 2. | “The imaging event creates an immutable second version. Version 1 remains available. The exchange shows what was added and what changed, but Dr Bianchi still decides whether the update crosses hospitals.” |
| 4:00–4:40 | Return to Utrecht, acknowledge version 2, record the final opinion, and accept version 2 into the Utrecht MDO. | “The final opinion applies only to the acknowledged current version. Utrecht accepts that version into its multidisciplinary meeting and names the meeting time.” |
| 4:40–5:00 | Return the outcome to Milan. Point to the specialist opinion, MDO schedule, next responsibility, and activity timeline. | “The loop closes in Dr Bianchi’s workspace. Milan receives the opinion, the scheduled MDO, and the exact next action. The timeline preserves every source query, approval, acknowledgement, and responsibility change.” |

## Clinical wording to preserve

- Say **source-linked referral package**, not “centralized patient record.”
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
| Closed-loop desktop outcome | [`evidence/closed-loop-desktop-chromium.png`](evidence/closed-loop-desktop-chromium.png) |
| Closed-loop mobile outcome | [`evidence/closed-loop-mobile-chromium.png`](evidence/closed-loop-mobile-chromium.png) |
