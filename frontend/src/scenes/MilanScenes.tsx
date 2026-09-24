import {
  ArrowRight,
  CircleAlert,
  CircleCheck,
  FileText,
  ImageDown,
  LoaderCircle,
  MapPin,
  RefreshCw,
  Send,
} from 'lucide-react'
import { useState } from 'react'
import type { FederatedSourceId } from '../api/types'
import { BoundaryPreview } from '../components/BoundaryPreview'
import { sceneEntryWork } from './entryWork'
import type { SceneProps } from './types'

export const DEFAULT_QUESTION =
  'Please assess response to conversion therapy and liver resectability.'
export const DEFAULT_ASSESSMENT =
  'Giulia has liver-limited metastatic colorectal cancer with response after conversion therapy. Please assess resectability and advise the next multidisciplinary step.'

const milanSources: { id: FederatedSourceId; label: string }[] = [
  { id: 'milan_ehr', label: 'Milan electronic health record' },
  { id: 'milan_documents', label: 'Milan document repository' },
  { id: 'milan_pacs', label: 'Milan imaging archive' },
]

function selectedPatient(snapshot: SceneProps['snapshot']) {
  return snapshot.patients.find((patient) => patient.case_id === snapshot.selected_patient_id)
}

export function CrossPatientScene({ snapshot, busy, readOnly, act }: SceneProps) {
  return (
    <div className="scene-stack">
      <section className="panel">
        <h2 className="panel-title">
          Worklist · Medical oncology, Milan
          <span className="panel-title-meta">{snapshot.patients.length} patients</span>
        </h2>
        <table className="grid" aria-label="Milan oncology worklist">
          <thead>
            <tr>
              <th scope="col">Patient</th>
              <th scope="col">Age</th>
              <th scope="col">Diagnosis</th>
              <th scope="col">Plan</th>
              <th scope="col">Status</th>
              <th scope="col">Updated</th>
              <th scope="col">
                <span className="sr-only">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {snapshot.patients.map((patient) => {
              const selected = patient.case_id === snapshot.selected_patient_id
              return (
                <tr key={patient.case_id} className={selected ? 'row-selected' : ''}>
                  <td>
                    <strong>{patient.display_name}</strong>
                    <div className="cell-sub">{patient.case_id}</div>
                  </td>
                  <td>{patient.age_band}</td>
                  <td>{patient.diagnosis}</td>
                  <td>{patient.current_plan}</td>
                  <td>
                    <span className={`badge ${patient.referral_candidate ? 'warning' : 'neutral'}`}>
                      {patient.care_status}
                    </span>
                  </td>
                  <td>{patient.last_updated}</td>
                  <td>
                    {patient.referral_candidate && (
                      <button
                        className={selected ? 'btn' : 'btn primary'}
                        type="button"
                        disabled={busy || readOnly || selected}
                        onClick={() => void act({ type: 'select_patient', patient_id: patient.case_id })}
                      >
                        {selected ? (
                          <>
                            <CircleCheck size={14} aria-hidden="true" />
                            Selected
                          </>
                        ) : (
                          `Open ${patient.display_name.split(' ')[0]}'s case`
                        )}
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>
    </div>
  )
}

export function CrossSourcesScene({ snapshot, busy, readOnly, runAgent }: SceneProps) {
  const patient = selectedPatient(snapshot)
  const failed = snapshot.source_checks.some((check) => check.status === 'failed')
  const missing = snapshot.source_checks.flatMap((check) =>
    check.records.filter((record) => record.status === 'missing').map((record) => record.label),
  )
  const allComplete = milanSources.every((source) =>
    snapshot.source_checks.some((check) => check.source_id === source.id && check.status === 'complete'),
  )
  return (
    <div className="scene-stack">
      <p className="hint">
        Local source inventory for {patient?.display_name ?? 'the selected patient'}. Records are queried in place; nothing is exported.
      </p>
      <div className="source-grid">
        {milanSources.map((source) => {
          const check = snapshot.source_checks.find((item) => item.source_id === source.id)
          return (
            <article key={source.id} className={`source-card ${check?.status ?? 'waiting'}`}>
              <header>
                <strong>{source.label}</strong>
                {check ? (
                  <em className={check.status}>{check.status === 'complete' ? '200 OK' : 'Failed'}</em>
                ) : (
                  <em className="waiting">
                    <LoaderCircle size={13} className="spin" aria-hidden="true" />
                    Asking
                  </em>
                )}
              </header>
              {check && <code>{check.endpoint}</code>}
              {check?.status === 'failed' && <p className="source-error">{check.error}</p>}
              <ul className="record-list compact">
                {check?.records.map((record) => (
                  <li key={record.id} className={record.status}>
                    {record.status === 'available' ? (
                      <FileText size={14} aria-hidden="true" />
                    ) : (
                      <CircleAlert size={14} aria-hidden="true" />
                    )}
                    <span>
                      <strong>{record.label}</strong>
                      {record.status === 'available' ? record.detail : 'Not held in Milan'}
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          )
        })}
      </div>
      {failed && (
        <div className="decision-row">
          <button
            className="btn"
            type="button"
            disabled={busy || readOnly}
            onClick={() => void runAgent(sceneEntryWork('cross_sources', snapshot))}
          >
            <RefreshCw size={16} aria-hidden="true" />
            Retry the failed source
          </button>
          <span className="hint">Failed sources are reported and can be retried.</span>
        </div>
      )}
      {allComplete && missing.length > 0 && (
        <article className="gap-card">
          <CircleAlert size={18} aria-hidden="true" />
          <div>
            <strong>Missing evidence (included in referral as known gaps)</strong>
            <p>{missing.join(' · ')}</p>
          </div>
        </article>
      )}
    </div>
  )
}

export function CrossQuestionScene({ snapshot, busy, readOnly, act }: SceneProps) {
  const patient = selectedPatient(snapshot)
  const [question, setQuestion] = useState(snapshot.clinical_question ?? DEFAULT_QUESTION)
  const confirmed = snapshot.clinical_question !== null
  return (
    <div className="scene-stack narrow">
      {patient && (
        <article className="patient-strip">
          <strong>{patient.display_name}</strong>
          <span>
            {patient.age_band} · {patient.diagnosis}
          </span>
          <small>{patient.current_plan}</small>
        </article>
      )}
      <label className="field">
        <span>Clinical question for the receiving specialist</span>
        <textarea
          rows={3}
          value={question}
          disabled={confirmed || readOnly}
          onChange={(event) => setQuestion(event.target.value)}
        />
      </label>
      {confirmed ? (
        <p className="confirmation">
          <CircleCheck size={18} aria-hidden="true" />
          Question confirmed by Dr Luca Bianchi. The agent will use it to find the right centre.
        </p>
      ) : (
        <div className="decision-row">
          <button
            className="btn primary"
            type="button"
            disabled={busy || readOnly || question.trim().length < 10}
            onClick={() => void act({ type: 'confirm_referral_question', question: question.trim() })}
          >
            <CircleCheck size={17} aria-hidden="true" />
            Confirm the question
          </button>
          <span className="hint">Confirmed by the referring clinician.</span>
        </div>
      )}
    </div>
  )
}

export function CrossDestinationScene({ snapshot, busy, readOnly, act }: SceneProps) {
  if (snapshot.destinations.length === 0) {
    return (
      <p className="hint">
        <LoaderCircle size={16} className="spin" aria-hidden="true" /> The agent is asking the
        European expert directory…
      </p>
    )
  }
  const limitations = snapshot.destinations[0]?.limitations ?? []
  return (
    <div className="scene-stack">
      <div className="destination-grid">
        {snapshot.destinations.map((destination, index) => {
          const selected = destination.centre_id === snapshot.selected_centre_id
          return (
            <article
              key={destination.centre_id}
              className={`destination-card ${selected ? 'selected' : ''} ${index === 0 ? 'best' : ''}`}
            >
              <header>
                <small>
                  <MapPin size={13} aria-hidden="true" />
                  {destination.city}, {destination.country}
                </small>
                <strong>{destination.centre_name}</strong>
                <span>{destination.clinician_name}</span>
              </header>
              <div className="score" aria-label={`Match ${destination.score} out of 100`}>
                <i style={{ width: `${destination.score}%` }} />
                <span>{destination.score}% match</span>
              </div>
              <ul>
                {destination.reasons.map((reason) => (
                  <li key={reason.label} className={reason.status}>
                    <strong>{reason.label}</strong>
                    {reason.detail}
                  </li>
                ))}
              </ul>
              <button
                className={selected ? 'btn' : index === 0 ? 'btn primary' : 'btn'}
                type="button"
                disabled={busy || readOnly || selected || snapshot.selected_centre_id !== null}
                onClick={() =>
                  void act({
                    type: 'select_destination',
                    centre_id: destination.centre_id,
                    clinician_id: destination.clinician_id,
                  })
                }
              >
                {selected ? 'Selected' : `Choose ${destination.clinician_name}`}
              </button>
            </article>
          )
        })}
      </div>
      <p className="footnote">{limitations.join(' ')}</p>
    </div>
  )
}

export function CrossPackageScene({ snapshot, busy, readOnly, act }: SceneProps) {
  const pkg = snapshot.package
  const [assessment, setAssessment] = useState(pkg?.referral_assessment ?? DEFAULT_ASSESSMENT)
  if (!pkg) {
    return (
      <p className="hint">
        <LoaderCircle size={16} className="spin" aria-hidden="true" /> The agent is reading
        UMC Utrecht's requirements and preparing case version 1…
      </p>
    )
  }
  return (
    <div className="scene-stack">
      <section className="requirements" aria-label={`${pkg.centre_name} requirements`}>
        <h2>What {pkg.centre_name} asks for</h2>
        <ul>
          {pkg.requirements.map((requirement) => (
            <li key={requirement.key} className={requirement.status}>
              {requirement.status === 'present' ? (
                <CircleCheck size={16} aria-hidden="true" />
              ) : (
                <CircleAlert size={16} aria-hidden="true" />
              )}
              <span>
                <strong>{requirement.label}</strong>
                {requirement.status === 'present' ? 'Included' : 'Missing, sent as a known gap'}
              </span>
            </li>
          ))}
        </ul>
      </section>
      <BoundaryPreview
        crossesTitle={`Case version 1 crosses to ${pkg.centre_name}`}
        crosses={pkg.structured_context}
        staysTitle="Stays in Milan"
        stays={pkg.retained_in_milan}
        note={`${pkg.provenance_links} provenance links point back to the Milan sources.`}
      />
      <label className="field">
        <span>Dr Bianchi's referral assessment</span>
        <textarea
          rows={3}
          value={assessment}
          disabled={pkg.approved || readOnly}
          onChange={(event) => setAssessment(event.target.value)}
        />
      </label>
      {pkg.approved ? (
        <p className="confirmation">
          <Send size={17} aria-hidden="true" />
          Case version 1 approved by {pkg.approved_by} and sent to {pkg.clinician_name}.
        </p>
      ) : (
        <div className="decision-row">
          <button
            className="btn primary"
            type="button"
            disabled={busy || readOnly || assessment.trim().length < 10}
            onClick={() =>
              void act({ type: 'approve_referral_package', referral_assessment: assessment.trim() })
            }
          >
            <Send size={17} aria-hidden="true" />
            Approve and send case version 1
          </button>
          <span className="hint">Requires approval by the referring clinician.</span>
        </div>
      )}
    </div>
  )
}

export function MilanUpdateScene({
  snapshot,
  busy,
  readOnly,
  act,
  deliverImagingEvent,
}: SceneProps) {
  const request = snapshot.evidence_request
  const update = snapshot.evidence_update
  const approved =
    snapshot.update_available_version !== null &&
    snapshot.update_approved_versions.includes(snapshot.update_available_version)
  return (
    <div className="scene-stack">
      {request && (
        <article className="request-card">
          <small>Request from {request.requested_by} · UMC Utrecht</small>
          <p>
            <strong>{request.requested_evidence.join(' and ')}</strong>
          </p>
          <p>{request.clinical_reason}</p>
        </article>
      )}
      {!update ? (
        <article className="event-card">
          <ImageDown size={22} aria-hidden="true" />
          <div>
            <strong>Awaiting imaging from Milan PACS</strong>
            <p>
              When radiology stores the studies, the archive raises an event and the Milan agent
              prepares case version 2. No one has to chase it.
            </p>
          </div>
          <button
            className="btn primary"
            type="button"
            disabled={busy || readOnly}
            onClick={() => void deliverImagingEvent()}
          >
            <ImageDown size={17} aria-hidden="true" />
            Simulate PACS arrival
          </button>
        </article>
      ) : (
        <>
          <section className="version-diff" aria-label="What changed from version 1 to version 2">
            <header>
              <span className="version-tag">v{update.previous_version}</span>
              <ArrowRight size={16} aria-hidden="true" />
              <span className="version-tag new">v{update.case_version}</span>
              <strong>What changed</strong>
            </header>
            <div className="diff-columns">
              <div>
                <h3>Added</h3>
                <ul>
                  {update.added_evidence.map((item) => (
                    <li key={item} className="added">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Changed findings</h3>
                <ul>
                  {update.changed_findings.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Still uncertain</h3>
                <ul>
                  {update.remaining_uncertainty.map((item) => (
                    <li key={item} className="uncertain">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
          {approved ? (
            <p className="confirmation">
              <Send size={17} aria-hidden="true" />
              Case version {update.case_version} approved by Dr Luca Bianchi and sent to Utrecht.
            </p>
          ) : (
            <div className="decision-row">
              <button
                className="btn primary"
                type="button"
                disabled={busy || readOnly}
                onClick={() =>
                  void act({ type: 'approve_evidence_update', case_version: update.case_version })
                }
              >
                <Send size={17} aria-hidden="true" />
                Approve and send case version {update.case_version}
              </button>
              <span className="hint">Version 1 is retained unchanged.</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
