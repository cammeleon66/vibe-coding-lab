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
4. Start at step 1. The workflow rail on the left (a numbered strip on mobile)
   shows all 14 steps; future steps are locked, completed steps reopen
   read-only.

## The 14 steps

Each step has one responsible clinician, shown in the page header. The primary
button in the bottom toolbar advances the story and only enables once the
step's work is done. When the responsible clinician changes, a **Handover**
banner names who handed over and what was carried. **Audit log** in the top bar
lists every hospital-system request.

| Step | Screen title | Presenter action | Advance button | What to say |
| --- | --- | --- | --- | --- |
| 1 | The MRI is at the hospital around the corner | Introduce Sanne de Vries and the missing MRI. | **Ask the exchange agent to find it** | “A Utrecht oncology team needs an MRI held by the hospital around the corner.” |
| 2 | The agent asks Stadshaven's own systems | Let the patient-summary and imaging requests complete; point to the assistant pane. | **Send the sharing request to Dr Noor Jansen** | “The exchange asks Stadshaven's own systems. Nothing is copied yet.” |
| 3 | Stadshaven decides what may cross | As Dr Noor Jansen, select **Approve release**. Point out that original images stay. | **Show what Utrecht receives** | “The originals stay at Stadshaven, and Dr Jansen decides what may cross.” |
| 4 | Today's treatment review can go ahead | Point to the released MRI finding. | **Now scale the same pattern** | “The nearby problem is solved without a shared database.” |
| 5 | From Utrecht to a European network | Select **Netherlands**, **Germany and Italy**, then **Europe**. | **Follow one referral from Milan to Utrecht** | “Geography changes; source ownership, provenance, approval, and named responsibility do not.” |
| 6 | Milan needs a second opinion | As Dr Luca Bianchi, select **Open Giulia's case**. | **Let the agent check Milan's own sources** | “The same pattern now crosses a border.” |
| 7 | The agent checks what Milan already holds | Let the EHR, document and imaging checks complete; point to missing evidence. | **Frame the clinical question** | “Each hospital-owned system is queried separately; gaps stay visible.” |
| 8 | Dr Bianchi frames the question | Select **Confirm the question**. | **Find the right expert centre** | “The clinician owns the question, not the software.” |
| 9 | Choosing the expert centre | Select **Choose Dr Eva van Dijk**. | **Prepare the referral package** | “The destination is explainable and bounded.” |
| 10 | Approve exactly what crosses the border | Point to what is shared and what remains in Milan, then **Approve and send case version 1**. | **Hand over to Dr Eva van Dijk in Utrecht** | “Structured context and provenance cross only after Dr Bianchi approves them.” |
| 11 | Utrecht reviews and asks for imaging | As Dr van Dijk: **Acknowledge case version 1**, **Record provisional opinion**, **Send the imaging request to Milan**. | **Hand back to Dr Luca Bianchi in Milan** | “Utrecht acknowledges the exact version, and the imaging request gives a clinical reason.” |
| 12 | New imaging arrives in Milan | **Simulate PACS arrival**, review the version 1→2 changes, then **Approve and send case version 2**. | **Hand over to Dr Eva van Dijk in Utrecht** | “Late evidence creates an immutable second version, and Dr Bianchi still decides whether it crosses.” |
| 13 | Utrecht completes the specialist review | **Acknowledge case version 2**, **Record specialist opinion**, **Accept into the MDO**. | **Return the outcome to Milan** | “The final opinion applies to the acknowledged current version.” |
| 14 | The loop is closed | Point to the opinion, MDO date (29 September 2026, 14:00 CEST) and next action. No advance button. | — | “We solved the nearby problem first, then proved the same pattern at European scale.” |
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
- **A source check fails:** leave the failed source visible and use **Retry the failed source**. Do not describe the referral as ready.
- **Agent work interrupted (e.g. after a refresh):** select **Resume assistant tasks**
  in the assistant pane.
- **State restore fails:** refresh once, then show the explicit error rather
  than describing a successful flow.
- **Evidence update fails:** explain that the previous valid case version is
  preserved. Reuse the same event ID only when retrying the same delivery.
- **Need a clean restart:** select **Reset** and wait for confirmation.

## Current visual evidence

Full-page desktop and mobile captures of steps 1–7, 9–12 and 14 are generated
by `frontend/tests/storyline.spec.ts` into [`evidence/`](evidence/), named
`NN-<scene>-<desktop|mobile>-chromium.png` (for example
[`evidence/01-local-problem-desktop-chromium.png`](evidence/01-local-problem-desktop-chromium.png)
and
[`evidence/14-closing-outcome-mobile-chromium.png`](evidence/14-closing-outcome-mobile-chromium.png)).
Live-environment captures for the storyline redesign have not been taken yet.