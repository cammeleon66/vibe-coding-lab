# INC-006 quality review

**Issue:** GitHub #5, INC-006  
**Requirement:** REQ-013  
**Baseline:** `28c8d53db44f34626e6974830223e9fc7eb0d609`  
**Date:** 2026-09-23

## Intent review

The change stays inside the approved local demonstration boundary. It adds no
Azure or Fabric resource, private MDO integration, real identity, real data, or
live AI. The primary path is deterministic and presenter-controlled. Preflight
explicitly states what it does not contact, and the completed state continues
to describe the MDO as a separate backend.

## Code review

- Preflight is a typed backend contract rather than UI-only optimism.
- Preflight parses required fixtures through the real preparation and
  late-arrival adapters, so malformed source content fails readiness.
- State-store readiness reloads and rewrites the current state through the same
  atomic replacement path used by the demo.
- Reset clears referral, prepared versions, event IDs, opinions, handoffs,
  research publication, presenter-edited inputs, and all local research
  sessions.
- Browser helpers drive the public UI rather than private application state.
- Loading, empty, error, update, and completed states are explicit; failed
  operations do not become success-shaped fallbacks.
- The source inspector is a portal-backed modal dialog with inert background
  content, trapped keyboard focus, Escape close, and trigger-focus restoration.

## Security and privacy review

- No secrets are added. The test-only research code is process-local and used
  only by the browser-test server.
- Preflight does not make outbound requests and cannot expose Azure, Fabric, or
  private MDO state.
- The reset route affects only the local synthetic rehearsal store and revokes
  every issued local research session.
- The existing HTTP-only research cookie boundary remains unchanged.
- Generated screenshots contain only synthetic demonstration content.
- Dependency audit from `npm install` reported zero known vulnerabilities.

Residual limitations: local endpoints have no production authentication,
`secure=False` remains appropriate only for localhost rehearsal, and this is not
a penetration test or production threat-model approval.

## Independent review findings resolved

- **Standards:** the preflight build test originally depended on ignored
  `frontend/dist` output. `create_app` now accepts a test-only frontend path,
  and tests cover both present and missing builds.
- **Standards:** the state probe originally checked a temporary write while
  claiming atomic replacement readiness. It now reloads and saves through the
  real `JsonStateStore.save` path, and the claim was narrowed.
- **Intent:** UI reset originally retained edited clinical need, sender, and
  urgency. Reset now restores all deterministic presenter inputs, with browser
  regression coverage.
- **Security:** reset originally left the in-memory research session authorized.
  It now revokes the session and expires the cookie, with backend regression
  coverage.
- **Security:** reset initially revoked only the requesting browser's research
  session. It now revokes every issued local session, with multi-session
  regression coverage.
- **Reliability:** preflight initially checked only whether source fixture files
  existed. It now exercises the real preparation and late-arrival parsers, and
  rejects malformed fixture content.
- **UI state:** reset confirmation initially remained visible after the next
  journey action. Journey actions now clear the stale confirmation, with
  browser coverage using the public Reset control.
- **Accessibility:** source-inspector focus could initially escape the modal.
  It now traps Tab and Shift+Tab, makes the application background inert, and
  restores focus to the provenance trigger after Escape.

## Visual review

The interface uses a clinical route, evidence ledger, source/normalized value
pairs, conflict/missingness signals, version comparison, human-responsibility
panel, and manifest transition rather than generic KPI cards. Provenance,
missingness, and responsibility cues remain visible at presenter distance.

Desktop acceptance uses Chromium at 1440×960. Mobile acceptance uses the Pixel
7 profile. The durable evidence set is indexed in
[`../demo/presenter-guide.md`](../demo/presenter-guide.md). JPEGs total less than
1 MB and are viewport captures rather than large recordings.

## Accessibility review

- axe WCAG 2 A/AA and WCAG 2.1 A/AA scans report no critical or serious
  violations on the opening and prepared-workspace states at desktop and mobile
  widths.
- The journey is an ordered, keyboard-focusable progress region with
  `aria-current`.
- Buttons, links, inputs, selects, and textareas have visible focus treatment.
- The source inspector uses dialog semantics, initial focus, Tab/Shift+Tab
  containment, an inert application background, Escape close, and
  trigger-focus restoration.
- Loading, reset confirmation, errors, update preservation, and completion use
  status or alert semantics.

Automation does not replace screen-reader testing with clinicians or users with
disabilities.

## Requirements-to-test/demo traceability

| Requirement | Implementation/test evidence | Demo evidence |
| --- | --- | --- |
| REQ-001–002 expertise discovery and explanation | `tests/test_discovery.py`; `frontend/src/App.test.tsx` | Presenter guide 8–22s; empty-state capture proves bounded matching |
| REQ-003 referral and responsibility | `tests/test_referrals.py`; browser rehearsal | Presenter guide 22–36s |
| REQ-004–008 heterogeneous, prepared, source-linked, missing/conflicting, bounded synthesis | `tests/test_preparation.py`; axe/keyboard browser test | Presenter guide 36–54s |
| REQ-009 evidence update | `tests/test_evidence_arrivals.py`; browser update path | `state-update.jpg`; presenter guide 54–78s |
| REQ-010 human responsibility | `tests/test_handoff.py`; completed browser path | Presenter guide 78–90s |
| REQ-011 narrative MDO handoff | `tests/test_handoff.py`; launch URL assertion | Completed desktop/mobile captures |
| REQ-012 research boundary | `tests/test_research.py`; 13 frontend unit tests | Optional epilogue remains outside the 90-second clinical path |
| REQ-013 deterministic demonstration reliability | `/api/preflight`, `/api/reset`, `frontend/tests/demo.spec.ts` | 90-second beat plan plus loading/empty/error/update/completed evidence |

## Verification record

| Gate | Result |
| --- | --- |
| Ruff format | Pass, 31 files |
| Ruff lint | Pass |
| strict mypy | Pass, 14 source files |
| pytest | Pass, 40 tests |
| backend coverage | 96% statements |
| frontend lint | Pass |
| frontend unit | Pass, 13 tests |
| production build | Pass |
| browser acceptance | Pass, desktop and mobile complete paths |
| accessibility automation | Pass, desktop and mobile |
| visual states | Pass, loading/empty/error/update/completed captured |
| planned presenter duration | 90 seconds |

## Known limitations and unresolved criteria

- Clinical fidelity is **not approved**. The package is ready for an external
  oncology reviewer; `RT-002` remains unresolved until that review is recorded.
- DICOM is metadata only; no pixels, derived rendering, DICOMweb, or image
  interpretation is present.
- The MDO target is not probed and no state transfer or receipt exists.
- The research adapter remains a local fake with separate simulated
  authorization.
- Browser automation covers Chromium, not Safari, Firefox, assistive-technology
  combinations, or clinical-user usability research.
- The automated path executes faster than a human narration; the presenter beat
  plan is explicitly 90 seconds and is bounded by the under-120-second browser
  rehearsal.
