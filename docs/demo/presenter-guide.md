# Presenter guide: the evidence changes the room

**Target duration:** 90 seconds  
**Runtime:** deterministic synthetic rehearsal  
**Boundary:** no Azure or Fabric provisioning, private MDO state, real patient
data, live directory, or live AI

## Before the audience arrives

1. Build the frontend and start FastAPI as described in `README.md`.
2. Select **Preflight**. Continue only when all required local checks pass.
3. Select **Reset**. The green confirmation must say the rehearsal returned to
   a clean synthetic case.
4. Keep the browser at 100% zoom. Use at least 1280×800; the tested presenter
   viewport is 1440×960.
5. Treat the MDO launch as a narrative handoff. Its availability is not checked
   and no private backend state is read.

## The 90-second story

| Time | What the audience should see | Presenter move and language |
| --- | --- | --- |
| 0–8s | Milan on the left, a clinical question on the right, and the persistent **Deterministic rehearsal** label | “This begins with a clinical need, not a directory search: who can help reconsider liver-directed options after conversion therapy?” Select **Find European expertise**. |
| 8–22s | A ranked European network with the strongest fit opened, reasons visible, and synthetic boundaries beside it | “The room is explainable: disease expertise, accepted evidence, pathway, language, and simulated availability. It is bounded—not a claim of universal European credentialing.” Select **Request specialist collaboration**. |
| 22–36s | The Milan→Utrecht route and an evidence-readiness ledger with missing conditions | “The referral does not become magically complete. Utrecht’s review conditions become explicit responsibility.” Select **Prepare clinical workspace**. |
| 36–54s | Source fact beside normalized value; missing molecular evidence and a date conflict remain visually prominent | “Different records can be brought together without erasing where they came from. This value changed format; this disagreement did not disappear.” Open one provenance link, point to institution, source format, pointer, and preserved original, then press **Escape**. |
| 54–78s | The late-imaging control, followed by the before/after version comparison and changed human questions | Select **Receive late imaging evidence**. “No new prompt. Case v1 remains immutable while v2 links baseline sites to restaging MRI. The system shows what changed; resectability remains a human multidisciplinary conclusion.” |
| 78–90s | Human opinion, explicit condition resolutions, next responsibility, then the completed banner and versioned manifest | Use the prepared rehearsal opinion and resolve each condition. Save, create the manifest, then say: “Evidence, judgement, unresolved issues, and responsibility now travel together into a clearly labeled, separate MDO demonstration.” |

## Prepared rehearsal wording

**Human opinion**

> The source-linked imaging update warrants multidisciplinary reassessment; no
> automated resectability conclusion is recorded.

**Condition note**

> Reviewed explicitly for this synthetic rehearsal and carried into the MDO
> record.

Do not say that surgery is feasible, that Utrecht accepted a real referral, or
that any clinician, institution, permission, availability, or interoperability
claim is live.

## If something goes wrong

- **Preflight failure:** do not begin. Fix the failed required check and run it
  again.
- **Loading remains visible:** refresh once. If state restore fails, show the
  explicit error rather than describing a successful flow.
- **Evidence update fails:** point out that the previous valid case version is
  preserved; do not retry with a new event ID during the presentation.
- **MDO unavailable:** stop at the completed manifest. Explain that continuity
  is represented by the versioned narrative handoff, not shared runtime state.
- **Need a clean restart:** select **Reset** and wait for the green confirmation.

## Visual evidence index

| State | Evidence |
| --- | --- |
| Loading | [`evidence/state-loading.jpg`](evidence/state-loading.jpg) |
| Empty bounded match | [`evidence/state-empty.jpg`](evidence/state-empty.jpg) |
| Explicit error | [`evidence/state-error.jpg`](evidence/state-error.jpg) |
| Evidence update | [`evidence/state-update.jpg`](evidence/state-update.jpg) |
| Completed clinical path | [`evidence/state-completed.jpg`](evidence/state-completed.jpg) |
| Desktop responsive acceptance | [`evidence/completed-desktop-chromium.jpg`](evidence/completed-desktop-chromium.jpg) |
| Mobile responsive acceptance | [`evidence/completed-mobile-chromium.jpg`](evidence/completed-mobile-chromium.jpg) |

