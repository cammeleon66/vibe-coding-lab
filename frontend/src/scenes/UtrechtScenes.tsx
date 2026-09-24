import { CalendarCheck, CircleCheck, RotateCcw, Send } from 'lucide-react'
import { useState } from 'react'
import { DecisionSteps } from '../components/DecisionSteps'
import type { SceneProps } from './types'

export const DEFAULT_PROVISIONAL =
  'The treatment response appears sufficient to discuss liver-directed treatment, but original baseline CT and current liver MRI are needed before a definitive resectability opinion.'
export const DEFAULT_EVIDENCE_REASON =
  'Original lesion sites and current vessel relationships must be reviewed before the multidisciplinary resectability decision.'
export const DEFAULT_FINAL =
  'Case version 2 accounts for the original lesion sites and current vessel relationships. The case is appropriate for Utrecht liver MDO review to determine the combined local treatment plan.'
export const DEFAULT_SCHEDULE = '29 September 2026 at 14:00 CEST'
export const DEFAULT_NEXT_ACTION =
  'Discuss the Utrecht opinion and MDO schedule with Giulia, confirm attendance, and provide any interval clinical changes.'

const isImaging = (item: string) => /\bCT\b|\bMRI\b/.test(item)

export function UtrechtReviewScene({ snapshot, busy, readOnly, act }: SceneProps) {
  const pkg = snapshot.package
  const imagingGaps = (pkg?.missing_evidence ?? []).filter(isImaging)
  const [opinion, setOpinion] = useState(snapshot.provisional_opinion ?? DEFAULT_PROVISIONAL)
  const [requested, setRequested] = useState<string[]>(imagingGaps)
  const [reason, setReason] = useState(DEFAULT_EVIDENCE_REASON)
  const locked = busy || readOnly
  if (!pkg) return null

  return (
    <DecisionSteps
      steps={[
        {
          id: 'acknowledge',
          title: 'Receive case version 1',
          done: snapshot.acknowledged_versions.includes(1),
          doneSummary: `Case version 1 from Milan received: ${pkg.clinical_question}`,
          content: (
            <div className="scene-stack">
              <article className="case-summary">
                <small>From Dr Luca Bianchi · Milan · case version 1</small>
                <p>
                  <strong>{pkg.clinical_question}</strong>
                </p>
                <p>{pkg.referral_assessment}</p>
                <ul className="chip-list">
                  {pkg.structured_context.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <p className="gap-line">Known gaps: {pkg.missing_evidence.join(' · ')}</p>
              </article>
              <button
                className="btn primary"
                type="button"
                disabled={locked}
                onClick={() => void act({ type: 'acknowledge_case_version', case_version: 1 })}
              >
                <CircleCheck size={17} aria-hidden="true" />
                Acknowledge case version 1
              </button>
            </div>
          ),
        },
        {
          id: 'opinion',
          title: 'Give a provisional opinion',
          done: snapshot.provisional_opinion !== null,
          doneSummary: snapshot.provisional_opinion ?? '',
          content: (
            <div className="scene-stack">
              <label className="field">
                <span>Dr van Dijk's provisional opinion</span>
                <textarea rows={3} value={opinion} disabled={readOnly} onChange={(event) => setOpinion(event.target.value)} />
              </label>
              <button
                className="btn primary"
                type="button"
                disabled={locked || opinion.trim().length < 10}
                onClick={() => void act({ type: 'record_provisional_opinion', opinion: opinion.trim() })}
              >
                Record provisional opinion
              </button>
            </div>
          ),
        },
        {
          id: 'request',
          title: 'Ask Milan for the missing imaging',
          done: snapshot.evidence_request !== null,
          doneSummary: `Requested: ${snapshot.evidence_request?.requested_evidence.join(' and ') ?? ''}`,
          content: (
            <div className="scene-stack">
              <fieldset className="check-group">
                <legend>Request from Milan</legend>
                {imagingGaps.map((item) => (
                  <label key={item}>
                    <input
                      type="checkbox"
                      checked={requested.includes(item)}
                      disabled={readOnly}
                      onChange={(event) =>
                        setRequested(
                          event.target.checked
                            ? [...requested, item]
                            : requested.filter((value) => value !== item),
                        )
                      }
                    />
                    {item}
                  </label>
                ))}
              </fieldset>
              <label className="field">
                <span>Clinical reason</span>
                <textarea rows={2} value={reason} disabled={readOnly} onChange={(event) => setReason(event.target.value)} />
              </label>
              <button
                className="btn primary"
                type="button"
                disabled={locked || requested.length === 0 || reason.trim().length < 10}
                onClick={() =>
                  void act({
                    type: 'request_evidence',
                    requested_evidence: requested,
                    clinical_reason: reason.trim(),
                  })
                }
              >
                <Send size={17} aria-hidden="true" />
                Send the imaging request to Milan
              </button>
            </div>
          ),
        },
      ]}
    />
  )
}

export function UtrechtMdoScene({ snapshot, busy, readOnly, act }: SceneProps) {
  const version = snapshot.update_available_version ?? 2
  const update = snapshot.evidence_update
  const [opinion, setOpinion] = useState(snapshot.final_opinion ?? DEFAULT_FINAL)
  const [schedule, setSchedule] = useState(DEFAULT_SCHEDULE)
  const [nextAction, setNextAction] = useState(DEFAULT_NEXT_ACTION)
  const locked = busy || readOnly

  return (
    <DecisionSteps
      steps={[
        {
          id: 'acknowledge',
          title: `Receive case version ${version}`,
          done: snapshot.acknowledged_versions.includes(version),
          doneSummary: `Case version ${version} received with ${update?.added_evidence.join(' and ').toLowerCase() ?? 'the new imaging'}.`,
          content: (
            <div className="scene-stack">
              {update && (
                <article className="case-summary">
                  <small>From Dr Luca Bianchi · Milan · case version {version}</small>
                  <ul className="chip-list">
                    {update.added_evidence.map((item) => (
                      <li key={item} className="added">
                        + {item}
                      </li>
                    ))}
                  </ul>
                  <p>{update.changed_findings[0]}</p>
                </article>
              )}
              <button
                className="btn primary"
                type="button"
                disabled={locked}
                onClick={() => void act({ type: 'acknowledge_case_version', case_version: version })}
              >
                <CircleCheck size={17} aria-hidden="true" />
                Acknowledge case version {version}
              </button>
            </div>
          ),
        },
        {
          id: 'final',
          title: 'Give the specialist opinion',
          done: snapshot.final_opinion !== null,
          doneSummary: snapshot.final_opinion ?? '',
          content: (
            <div className="scene-stack">
              <label className="field">
                <span>Dr van Dijk's specialist opinion</span>
                <textarea rows={3} value={opinion} disabled={readOnly} onChange={(event) => setOpinion(event.target.value)} />
              </label>
              <button
                className="btn primary"
                type="button"
                disabled={locked || opinion.trim().length < 10}
                onClick={() => void act({ type: 'record_final_opinion', opinion: opinion.trim() })}
              >
                Record specialist opinion
              </button>
            </div>
          ),
        },
        {
          id: 'mdo',
          title: 'Accept into the Utrecht liver MDO',
          done: snapshot.mdo_outcome !== null,
          doneSummary: `Scheduled for ${snapshot.mdo_outcome?.scheduled_for ?? ''}.`,
          content: (
            <div className="scene-stack">
              <label className="field">
                <span>MDO slot</span>
                <input value={schedule} disabled={readOnly} onChange={(event) => setSchedule(event.target.value)} />
              </label>
              <label className="field">
                <span>Next action for Milan</span>
                <textarea rows={2} value={nextAction} disabled={readOnly} onChange={(event) => setNextAction(event.target.value)} />
              </label>
              <button
                className="btn primary"
                type="button"
                disabled={locked || schedule.trim().length < 5 || nextAction.trim().length < 10}
                onClick={() =>
                  void act({
                    type: 'accept_mdo_outcome',
                    scheduled_for: schedule.trim(),
                    next_action: nextAction.trim(),
                  })
                }
              >
                <CalendarCheck size={17} aria-hidden="true" />
                Accept into the MDO
              </button>
            </div>
          ),
        },
      ]}
    />
  )
}

export function ClosingOutcomeScene({ snapshot, busy, reset }: SceneProps) {
  const outcome = snapshot.mdo_outcome
  const exchange = snapshot.regional_exchange
  const approvals = snapshot.activity.filter((event) => /approv/i.test(event.kind))
  return (
    <div className="scene-stack">
      {outcome && (
        <section className="panel">
          <h2 className="panel-title">
            Specialist outcome · case version {outcome.case_version}
            <span className="badge success">Returned to referrer</span>
          </h2>
          <dl className="kv">
            <dt>Specialist</dt>
            <dd>{outcome.specialist}, UMC Utrecht</dd>
            <dt>Opinion</dt>
            <dd>{outcome.final_opinion}</dd>
            <dt>MDO</dt>
            <dd>
              <CalendarCheck size={13} aria-hidden="true" /> Utrecht liver MDO, {outcome.scheduled_for}
            </dd>
            <dt>Next responsible</dt>
            <dd>{outcome.next_responsible_actor}</dd>
            <dt>Next action</dt>
            <dd>{outcome.next_action}</dd>
          </dl>
        </section>
      )}
      <section className="panel">
        <h2 className="panel-title">Exchange summary</h2>
        <table className="grid">
          <thead>
            <tr>
              <th scope="col">Exchange</th>
              <th scope="col">Scope</th>
              <th scope="col">Released</th>
              <th scope="col">Retained at source</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                {exchange.source_institution} → {exchange.requesting_institution}
              </td>
              <td>Regional</td>
              <td>{exchange.crosses_boundary.join(', ')}</td>
              <td>{exchange.stays_at_source.join(', ')}</td>
            </tr>
            <tr>
              <td>Istituto Nazionale dei Tumori, Milan → UMC Utrecht</td>
              <td>Cross-border</td>
              <td>{snapshot.package?.structured_context.join(', ')}</td>
              <td>{snapshot.package?.retained_in_milan.join(', ')}</td>
            </tr>
          </tbody>
        </table>
        <p className="panel-note">
          {approvals.length} clinician approvals recorded · {snapshot.storyline.system_calls.length}{' '}
          source system requests · full trail in the audit log.
        </p>
      </section>
      <div className="form-actions">
        <button className="btn" type="button" disabled={busy} onClick={() => void reset()}>
          <RotateCcw size={14} aria-hidden="true" />
          Reset demo data
        </button>
        <span className="hint">All patients, clinicians and institutions are synthetic.</span>
      </div>
    </div>
  )
}