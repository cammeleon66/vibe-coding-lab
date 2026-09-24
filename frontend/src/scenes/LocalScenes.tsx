import { CircleCheck, LoaderCircle, ShieldCheck } from 'lucide-react'
import type { RegionalSourceId } from '../api/types'
import { BoundaryPreview } from '../components/BoundaryPreview'
import type { SceneProps } from './types'

const regionalSourceOrder: { id: RegionalSourceId; label: string }[] = [
  { id: 'utrecht_patient_summary', label: 'Stadshaven patient-summary service' },
  { id: 'utrecht_imaging', label: 'Stadshaven imaging archive' },
]

export function LocalProblemScene({ snapshot }: SceneProps) {
  const exchange = snapshot.regional_exchange
  return (
    <div className="scene-stack">
      <section className="panel">
        <h2 className="panel-title">Information request</h2>
        <dl className="kv">
          <dt>Reason</dt>
          <dd>{exchange.problem}</dd>
          <dt>Decision due</dt>
          <dd>Treatment review, today 14:00</dd>
          <dt>Required document</dt>
          <dd>Latest liver MRI (report)</dd>
          <dt>Requesting centre</dt>
          <dd>
            {exchange.requesting_institution} · {exchange.requesting_clinician}
          </dd>
          <dt>Record holder</dt>
          <dd>
            {exchange.source_institution} · {exchange.source_clinician}
          </dd>
          <dt>Shared record system</dt>
          <dd>
            <span className="badge warning">None</span> Current route: telephone, fax or CD by
            courier. Alternative: repeat MRI.
          </dd>
        </dl>
      </section>
      <p className="hint">
        Use the exchange assistant to locate the MRI at {exchange.source_institution}. No data
        is shared without approval from the record holder.
      </p>
    </div>
  )
}

export function LocalSearchScene({ snapshot }: SceneProps) {
  const exchange = snapshot.regional_exchange
  const checks = exchange.source_checks
  const allDone = regionalSourceOrder.every((source) => checks[source.id])
  return (
    <div className="scene-stack">
      <section className="panel">
        <h2 className="panel-title">Source queries · {exchange.source_institution}</h2>
        <table className="grid">
          <thead>
            <tr>
              <th scope="col">Source system</th>
              <th scope="col">Request</th>
              <th scope="col">Status</th>
              <th scope="col">Records found</th>
            </tr>
          </thead>
          <tbody>
            {regionalSourceOrder.map((source) => {
              const check = checks[source.id]
              return (
                <tr key={source.id}>
                  <td>{source.label}</td>
                  <td>
                    <code>{check?.endpoint ?? '—'}</code>
                  </td>
                  <td>
                    {check ? (
                      <span className="badge success">200 OK</span>
                    ) : (
                      <span className="badge neutral">
                        <LoaderCircle size={11} className="spin" aria-hidden="true" /> Querying
                      </span>
                    )}
                  </td>
                  <td>
                    {check?.records.map((record) => (
                      <div key={record.id} className="cell-line">
                        <strong>{record.label}</strong> — {record.detail}
                      </div>
                    ))}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>
      {allDone && (
        <div className="message info">
          <span>
            MRI report of 24 September 2026 located at {exchange.source_institution}. Release
            requires approval by {exchange.source_clinician}. A sharing request has been drafted;
            nothing has been shared yet.
          </span>
        </div>
      )}
    </div>
  )
}

export function LocalApprovalScene({ snapshot, busy, readOnly, act }: SceneProps) {
  const exchange = snapshot.regional_exchange
  const directive = exchange.source_checks.utrecht_patient_summary?.records.find(
    (record) => record.id === 'consent-directive',
  )
  return (
    <div className="scene-stack">
      <section className="panel">
        <h2 className="panel-title">Incoming sharing request</h2>
        <dl className="kv">
          <dt>From</dt>
          <dd>
            {exchange.requesting_clinician} · {exchange.requesting_institution}
          </dd>
          <dt>Patient</dt>
          <dd>
            {exchange.patient_label} ({exchange.case_id})
          </dd>
          <dt>Purpose</dt>
          <dd>Treatment review today</dd>
          {directive && (
            <>
              <dt>Sharing basis</dt>
              <dd>
                <ShieldCheck size={13} aria-hidden="true" /> {directive.label}: {directive.detail}
              </dd>
            </>
          )}
        </dl>
      </section>
      <BoundaryPreview
        crossesTitle={`Released to ${exchange.requesting_institution}`}
        crosses={exchange.crosses_boundary}
        staysTitle={`Retained at ${exchange.source_institution}`}
        stays={exchange.stays_at_source}
      />
      {exchange.sharing_approved ? (
        <div className="message success">
          <CircleCheck size={15} aria-hidden="true" />
          <span>Approved by {exchange.approved_by}. Released items: 2.</span>
        </div>
      ) : (
        <div className="form-actions">
          <button
            className="btn primary"
            type="button"
            disabled={busy || readOnly}
            onClick={() => void act({ type: 'approve_regional_exchange' })}
          >
            Approve release
          </button>
          <span className="hint">Signed as {exchange.source_clinician}</span>
        </div>
      )}
    </div>
  )
}

export function LocalResultScene({ snapshot }: SceneProps) {
  const exchange = snapshot.regional_exchange
  const result = exchange.shared_result
  if (!result) return <p className="hint">No shared result available.</p>
  return (
    <div className="scene-stack">
      <section className="panel">
        <h2 className="panel-title">Received document · {result.title}</h2>
        <dl className="kv">
          <dt>Finding</dt>
          <dd>{result.finding}</dd>
          <dt>Released by</dt>
          <dd>{exchange.approved_by}</dd>
          <dt>Provenance</dt>
          <dd>Source-linked to {exchange.source_institution}</dd>
          <dt>Next responsibility</dt>
          <dd>{exchange.next_responsibility}</dd>
        </dl>
      </section>
      <section className="panel">
        <h2 className="panel-title">Impact on today's review</h2>
        <ul className="plain-list">
          {result.impact.map((item) => (
            <li key={item}>
              <CircleCheck size={14} aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
