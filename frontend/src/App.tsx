import {
  ArrowRight,
  Building2,
  Check,
  CircleAlert,
  History,
  Network,
  RotateCcw,
  ShieldCheck,
  Stethoscope,
  UserRound,
  Users,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import './App.css'

type JourneyRole = 'milan' | 'utrecht'
type JourneyStageId =
  | 'patient'
  | 'local_data'
  | 'referral'
  | 'utrecht_review'
  | 'evidence_update'
  | 'mdo_outcome'

interface JourneyRoleView {
  id: JourneyRole
  clinician_name: string
  institution: string
  specialty: string
  responsibilities: string[]
  available: boolean
  unavailable_reason: string | null
  recommended: boolean
}

interface JourneyPatient {
  case_id: string
  display_name: string
  age_band: string
  diagnosis: string
  care_status: string
  current_plan: string
  last_updated: string
  referral_candidate: boolean
}

interface JourneyStage {
  id: JourneyStageId
  label: string
  status: 'complete' | 'current' | 'available' | 'locked'
  prerequisite: string | null
}

interface JourneyActivity {
  id: string
  kind:
    | 'workspace_opened'
    | 'patient_selected'
    | 'source_queried'
    | 'source_query_failed'
    | 'question_confirmed'
    | 'directory_queried'
    | 'requirements_queried'
    | 'destination_selected'
    | 'package_prepared'
    | 'package_approved'
  actor: string
  institution: string
  title: string
  detail: string
  occurred_at: string
}

type FederatedSourceId = 'milan_ehr' | 'milan_documents' | 'milan_pacs'

interface SourceCheck {
  source_id: FederatedSourceId
  source_label: string
  endpoint: string
  patient_id: string
  status: 'complete' | 'failed'
  records: {
    id: string
    label: string
    status: 'available' | 'missing'
    detail: string
  }[]
  checked_at: string
  error: string | null
}

interface JourneySnapshot {
  active_role: JourneyRole | null
  selected_patient_id: string | null
  roles: JourneyRoleView[]
  patients: JourneyPatient[]
  stages: JourneyStage[]
  activity: JourneyActivity[]
  source_checks: SourceCheck[]
  clinical_question: string | null
  destinations: {
    centre_id: string
    centre_name: string
    city: string
    country: string
    clinician_id: string
    clinician_name: string
    score: number
    reasons: { label: string; detail: string; status: 'match' | 'condition' }[]
    limitations: string[]
  }[]
  selected_centre_id: string | null
  requirements: {
    key: string
    label: string
    rationale: string
    status: 'present' | 'missing'
  }[]
  package: {
    case_version: number
    clinical_question: string
    centre_name: string
    clinician_name: string
    requirements: {
      key: string
      label: string
      rationale: string
      status: 'present' | 'missing'
    }[]
    structured_context: string[]
    retained_in_milan: string[]
    provenance_links: number
    missing_evidence: string[]
    approved: boolean
    approved_by: string | null
    referral_assessment: string | null
  } | null
  next_role: JourneyRole | null
}

type Screen = 'role' | 'patients' | 'selected' | 'referral'

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}.`)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function App() {
  const [snapshot, setSnapshot] = useState<JourneySnapshot | null>(null)
  const [screen, setScreen] = useState<Screen>('role')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    requestJson<JourneySnapshot>('/api/journey')
      .then((restored) => {
        setSnapshot(restored)
        if (restored.active_role === 'milan') {
          setScreen(
            restored.package
              ? 'referral'
              : restored.selected_patient_id
                ? 'selected'
                : 'patients',
          )
        }
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Could not restore the journey.')
      })
  }, [])

  async function applyAction(action: object) {
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const updated = await requestJson<JourneySnapshot>('/api/journey/actions', {
        method: 'POST',
        body: JSON.stringify(action),
      })
      setSnapshot(updated)
      return updated
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The action could not be completed.')
      return null
    } finally {
      setBusy(false)
    }
  }

  async function enterRole(role: JourneyRole) {
    const updated = await applyAction({ type: 'enter_role', role })
    if (!updated) return
    if (role === 'milan') {
      setScreen(
        updated.package ? 'referral' : updated.selected_patient_id ? 'selected' : 'patients',
      )
    } else {
      setNotice('The Utrecht receiving screen is implemented in issue #10.')
    }
  }

  async function selectPatient(patientId: string) {
    const updated = await applyAction({ type: 'select_patient', patient_id: patientId })
    if (!updated) return
    setScreen('selected')
    await runSourceChecks(updated)
  }

  async function runSourceChecks(current: JourneySnapshot) {
    setBusy(true)
    setError(null)
    let latest = current
    for (const sourceId of [
      'milan_ehr',
      'milan_documents',
      'milan_pacs',
    ] as FederatedSourceId[]) {
      if (
        latest.source_checks.some(
          (check) => check.source_id === sourceId && check.status === 'complete',
        )
      ) {
        continue
      }
      try {
        latest = await requestJson<JourneySnapshot>('/api/journey/actions', {
          method: 'POST',
          body: JSON.stringify({ type: 'query_source', source_id: sourceId }),
        })
        setSnapshot(latest)
      } catch (reason) {
        setError(
          reason instanceof Error ? reason.message : 'A Milan source could not be queried.',
        )
        break
      }
    }
    setBusy(false)
  }

  async function resetDemo() {
    setBusy(true)
    setError(null)
    try {
      await requestJson<void>('/api/reset', { method: 'POST' })
      setSnapshot(await requestJson<JourneySnapshot>('/api/journey'))
      setScreen('role')
      setNotice('The synthetic referral journey has been reset.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The journey could not be reset.')
    } finally {
      setBusy(false)
    }
  }

  const selectedPatient =
    snapshot?.patients.find((patient) => patient.case_id === snapshot.selected_patient_id) ??
    null

  return (
    <main className="journey-app" aria-busy={busy || snapshot === null}>
      <header className="masthead">
        <div className="brand" aria-label="European Oncology Exchange">
          <span className="brand-mark" aria-hidden="true">
            <Network size={18} strokeWidth={1.7} />
          </span>
          <span>
            <strong>European Oncology Exchange</strong>
            <small>Synthetic cross-border referral demonstration</small>
          </span>
        </div>
        <div className="presenter-controls">
          {snapshot?.active_role && (
            <span className={`role-indicator ${snapshot.active_role}`}>
              <UserRound size={15} />
              {snapshot.roles.find((role) => role.id === snapshot.active_role)?.clinician_name}
            </span>
          )}
          <button
            className="header-action"
            type="button"
            onClick={() => setScreen('role')}
            disabled={busy}
          >
            <Users size={15} />
            Clinical roles
          </button>
          <button className="header-action" type="button" onClick={resetDemo} disabled={busy}>
            <RotateCcw size={15} />
            Reset
          </button>
        </div>
      </header>

      {snapshot && (
        <ol className="journey-rail" aria-label="Referral stages">
          {snapshot.stages.map((stage, index) => (
            <li
              className={`journey-step ${stage.status}`}
              key={stage.id}
              aria-current={stage.status === 'current' ? 'step' : undefined}
            >
              <button
                type="button"
                aria-disabled={stage.status === 'locked'}
                title={stage.prerequisite ?? undefined}
                onClick={() => {
                  if (stage.status === 'locked') {
                    setNotice(stage.prerequisite)
                    return
                  }
                  if (stage.id === 'patient') setScreen('patients')
                  else if (stage.id === 'local_data') setScreen('selected')
                  else if (stage.id === 'referral') setScreen('referral')
                  else setNotice(`${stage.label} is implemented in a later increment.`)
                }}
              >
                <span>{String(index + 1).padStart(2, '0')}</span>
                {stage.label}
              </button>
            </li>
          ))}
        </ol>
      )}

      {error && (
        <div className="alert" role="alert">
          <CircleAlert size={18} />
          {error}
        </div>
      )}
      {notice && (
        <div className="status-banner" role="status">
          <ShieldCheck size={17} />
          {notice}
        </div>
      )}

      {snapshot === null ? (
        <section className="loading-stage" role="status">
          <span className="loading-pulse" aria-hidden="true" />
          <p className="eyebrow">Loading demonstration state</p>
          <h1>Restoring the referral journey</h1>
        </section>
      ) : (
        <div className="journey-layout">
          <section className="journey-screen">
            {screen === 'role' && (
              <RolePicker roles={snapshot.roles} busy={busy} onEnter={enterRole} />
            )}
            {screen === 'patients' && (
              <PatientWorklist
                patients={snapshot.patients}
                busy={busy}
                onSelect={selectPatient}
              />
            )}
            {screen === 'selected' && selectedPatient && (
              <SelectedPatient
                patient={selectedPatient}
                sourceChecks={snapshot.source_checks}
                busy={busy}
                onRetry={() => void runSourceChecks(snapshot)}
                onContinue={() => setScreen('referral')}
              />
            )}
            {screen === 'referral' && selectedPatient && (
              <ReferralPreparation
                snapshot={snapshot}
                patient={selectedPatient}
                busy={busy}
                onAction={applyAction}
              />
            )}
          </section>
          <ActivityTimeline activity={snapshot.activity} />
        </div>
      )}

      <footer>
        <span>Synthetic demonstration · No real patient or clinician data</span>
        <span>Clinical roles and hospital systems are simulated</span>
      </footer>
    </main>
  )
}

function RolePicker({
  roles,
  busy,
  onEnter,
}: {
  roles: JourneyRoleView[]
  busy: boolean
  onEnter: (role: JourneyRole) => void
}) {
  return (
    <section className="role-picker screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Synthetic clinical roles</p>
          <h1>Choose a clinical workspace</h1>
        </div>
        <p>
          Each role has separate hospital data and responsibilities. This role picker is part of
          the demonstration and is not a production sign-in system.
        </p>
      </div>
      <div className="role-card-grid">
        {roles.map((role) => (
          <article
            className={`role-card ${role.recommended ? 'recommended' : ''} ${
              role.available ? '' : 'unavailable'
            }`}
            key={role.id}
          >
            <div className="role-card-heading">
              <span className={`role-icon ${role.id}`}>
                {role.id === 'milan' ? <UserRound size={22} /> : <Stethoscope size={22} />}
              </span>
              {role.recommended && <span className="recommended-label">Continue here</span>}
            </div>
            <p className="eyebrow">{role.id === 'milan' ? 'Milan' : 'Utrecht'}</p>
            <h2>{role.clinician_name}</h2>
            <p>{role.specialty}</p>
            <dl>
              <div>
                <dt>Institution</dt>
                <dd>{role.institution}</dd>
              </div>
              <div>
                <dt>Responsibilities</dt>
                <dd>{role.responsibilities.join(' · ')}</dd>
              </div>
            </dl>
            <button
              className={role.available ? 'primary-action full' : 'secondary-action full'}
              type="button"
              disabled={busy || !role.available}
              onClick={() => onEnter(role.id)}
            >
              {role.available ? `Open ${role.id === 'milan' ? 'Milan' : 'Utrecht'} workspace` : role.unavailable_reason}
              {role.available && <ArrowRight size={18} />}
            </button>
          </article>
        ))}
      </div>
    </section>
  )
}

function PatientWorklist({
  patients,
  busy,
  onSelect,
}: {
  patients: JourneyPatient[]
  busy: boolean
  onSelect: (patientId: string) => void
}) {
  return (
    <section className="patient-worklist screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dr Luca Bianchi · Milan</p>
          <h1>Active patients</h1>
        </div>
        <p>Select the patient whose current care plan calls for external specialist review.</p>
      </div>
      <div className="patient-list" role="list" aria-label="Active synthetic patients">
        {patients.map((patient) => (
          <article
            className={`patient-card ${patient.referral_candidate ? 'referral-candidate' : ''}`}
            role="listitem"
            key={patient.case_id}
          >
            <div className="patient-card-heading">
              <span className="patient-avatar" aria-hidden="true">
                {patient.display_name
                  .split(' ')
                  .map((part) => part[0])
                  .join('')}
              </span>
              <div>
                <span className="synthetic-tag">Synthetic patient</span>
                <h2>{patient.display_name}</h2>
                <p>
                  {patient.case_id} · Age {patient.age_band}
                </p>
              </div>
              <span className={`care-status ${patient.referral_candidate ? 'attention' : ''}`}>
                {patient.care_status}
              </span>
            </div>
            <p className="patient-diagnosis">{patient.diagnosis}</p>
            <div className="patient-referral-reason">
              <strong>Current plan</strong>
              <span>{patient.current_plan}</span>
            </div>
            <div className="patient-card-actions">
              <small>Updated {patient.last_updated}</small>
              <button
                className={patient.referral_candidate ? 'primary-action' : 'secondary-action'}
                type="button"
                disabled={busy || !patient.referral_candidate}
                onClick={() => onSelect(patient.case_id)}
              >
                {patient.referral_candidate
                  ? 'Prepare specialist referral'
                  : 'No external referral due'}
                {patient.referral_candidate && <ArrowRight size={17} />}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

const sourceDefinitions: {
  id: FederatedSourceId
  label: string
  shortEndpoint: string
}[] = [
  {
    id: 'milan_ehr',
    label: 'Milan electronic health record',
    shortEndpoint: 'source=milan_ehr',
  },
  {
    id: 'milan_documents',
    label: 'Milan document repository',
    shortEndpoint: 'source=milan_documents',
  },
  {
    id: 'milan_pacs',
    label: 'Milan imaging archive',
    shortEndpoint: 'source=milan_pacs',
  },
]

function SelectedPatient({
  patient,
  sourceChecks,
  busy,
  onRetry,
  onContinue,
}: {
  patient: JourneyPatient
  sourceChecks: SourceCheck[]
  busy: boolean
  onRetry: () => void
  onContinue: () => void
}) {
  const checksComplete =
    sourceChecks.length === sourceDefinitions.length &&
    sourceChecks.every((check) => check.status === 'complete')
  const checkFailed = sourceChecks.some((check) => check.status === 'failed')
  return (
    <section className="selected-patient data-check-stage screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            {patient.display_name} · {patient.case_id}
          </p>
          <h1>Check available data in Milan</h1>
        </div>
        <p>
          The platform calls each hospital-owned source separately. Results show what can support
          the referral and what remains missing.
        </p>
      </div>
      <div className="federated-check-layout">
        <article className="selected-patient-summary">
          <span className="patient-avatar" aria-hidden="true">
            {patient.display_name
              .split(' ')
              .map((part) => part[0])
              .join('')}
          </span>
          <div>
            <h2>{patient.display_name}</h2>
            <p>{patient.diagnosis}</p>
            <strong>{patient.current_plan}</strong>
          </div>
        </article>
        <div className="source-check-list" aria-live="polite">
          {sourceDefinitions.map((source) => {
            const check = sourceChecks.find((item) => item.source_id === source.id)
            return (
              <article
                className={`source-check ${check?.status ?? (busy ? 'running' : 'queued')}`}
                key={source.id}
              >
                <div className="source-check-heading">
                  <div>
                    <small>{source.label}</small>
                    <code>POST /api/journey/actions · {source.shortEndpoint}</code>
                  </div>
                  <strong>
                    {!check && busy && 'Requesting'}
                    {!check && !busy && 'Queued'}
                    {check?.status === 'complete' && '200 OK'}
                    {check?.status === 'failed' && 'Failed'}
                  </strong>
                </div>
                {check?.records.map((record) => (
                  <div className={`source-record-status ${record.status}`} key={record.id}>
                    {record.status === 'available' ? (
                      <Check size={16} />
                    ) : (
                      <CircleAlert size={16} />
                    )}
                    <span>
                      <strong>{record.label}</strong>
                      <small>{record.detail}</small>
                    </span>
                    <em>{record.status === 'available' ? 'Available' : 'Missing'}</em>
                  </div>
                ))}
                {check?.error && <p className="field-error">{check.error}</p>}
              </article>
            )
          })}
        </div>
      </div>
      {checksComplete && (
        <div className="stage-completion">
          <div className="next-increment-note" role="status">
            <ShieldCheck size={18} />
            <span>
              <strong>Local data check complete</strong>
              Available and missing evidence remain visible during referral preparation.
            </span>
          </div>
          <button className="primary-action" type="button" disabled={busy} onClick={onContinue}>
            Confirm referral and destination
            <ArrowRight size={17} />
          </button>
        </div>
      )}
      {checkFailed && (
        <button className="secondary-action" type="button" disabled={busy} onClick={onRetry}>
          Retry failed source
        </button>
      )}
    </section>
  )
}

const defaultReferralQuestion =
  'Please assess response to conversion therapy and liver resectability.'

const defaultReferralAssessment =
  'Giulia has liver-limited metastatic colorectal cancer with response after conversion therapy. Please assess resectability and advise the next multidisciplinary step.'

function ReferralPreparation({
  snapshot,
  patient,
  busy,
  onAction,
}: {
  snapshot: JourneySnapshot
  patient: JourneyPatient
  busy: boolean
  onAction: (action: object) => Promise<JourneySnapshot | null>
}) {
  const [question, setQuestion] = useState(
    snapshot.clinical_question ?? defaultReferralQuestion,
  )
  const [assessment, setAssessment] = useState(
    snapshot.package?.referral_assessment ?? defaultReferralAssessment,
  )
  const selectedDestination = snapshot.destinations.find(
    (destination) => destination.centre_id === snapshot.selected_centre_id,
  )

  return (
    <section className="referral-preparation screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            {patient.display_name} · Milan referral
          </p>
          <h1>Prepare referral for specialist review</h1>
        </div>
        <p>
          Confirm the clinical question, choose an explainable destination, and approve exactly
          what crosses to Utrecht.
        </p>
      </div>

      <article className="referral-step-card">
        <span className="step-number">1</span>
        <div className="step-content">
          <h2>Clinical question</h2>
          <label htmlFor="referral-question">Question for the receiving specialist</label>
          <textarea
            id="referral-question"
            value={question}
            disabled={busy || snapshot.package?.approved}
            onChange={(event) => setQuestion(event.target.value)}
          />
          {!snapshot.clinical_question && (
            <button
              className="primary-action"
              type="button"
              disabled={busy || question.trim().length < 10}
              onClick={() =>
                void onAction({ type: 'confirm_referral_question', question: question.trim() })
              }
            >
              Confirm clinical question
            </button>
          )}
          {snapshot.clinical_question && <p className="confirmed-line"><Check size={16} /> Confirmed by Dr Bianchi</p>}
        </div>
      </article>

      {snapshot.clinical_question && (
        <article className="referral-step-card">
          <span className="step-number">2</span>
          <div className="step-content">
            <h2>Expert destination</h2>
            {snapshot.destinations.length === 0 ? (
              <>
                <p>
                  Query the bounded synthetic directory for clinical fit, evidence compatibility,
                  working language, and availability.
                </p>
                <button
                  className="primary-action"
                  type="button"
                  disabled={busy}
                  onClick={() => void onAction({ type: 'query_expert_directory' })}
                >
                  Query expert directory
                </button>
              </>
            ) : (
              <div className="destination-list">
                {snapshot.destinations.map((destination, index) => (
                  <article
                    className={`destination-card ${
                      destination.centre_id === snapshot.selected_centre_id ? 'selected' : ''
                    }`}
                    key={destination.centre_id}
                  >
                    <div>
                      <small>{index === 0 ? 'Best match' : 'Alternative'}</small>
                      <h3>{destination.centre_name}</h3>
                      <p>
                        {destination.city}, {destination.country} · {destination.clinician_name}
                      </p>
                    </div>
                    <strong>{destination.score} match points</strong>
                    <ul>
                      {destination.reasons.slice(0, 3).map((reason) => (
                        <li key={reason.label}>
                          <Check size={14} />
                          <span>
                            <strong>{reason.label}</strong>
                            {reason.detail}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <button
                      className={
                        destination.centre_id === snapshot.selected_centre_id
                          ? 'secondary-action'
                          : 'primary-action'
                      }
                      type="button"
                      disabled={busy || snapshot.package?.approved}
                      onClick={() =>
                        void onAction({
                          type: 'select_destination',
                          centre_id: destination.centre_id,
                          clinician_id: destination.clinician_id,
                        })
                      }
                    >
                      {destination.centre_id === snapshot.selected_centre_id
                        ? 'Destination selected'
                        : `Select ${destination.centre_name}`}
                    </button>
                  </article>
                ))}
                <p className="directory-limit">
                  {snapshot.destinations[0].limitations[0]}
                </p>
              </div>
            )}
          </div>
        </article>
      )}

      {selectedDestination && (
        <article className="referral-step-card">
          <span className="step-number">3</span>
          <div className="step-content">
            <h2>Utrecht referral requirements</h2>
            {snapshot.requirements.length === 0 ? (
              <button
                className="primary-action"
                type="button"
                disabled={busy}
                onClick={() => void onAction({ type: 'query_requirements' })}
              >
                Query Utrecht requirements
              </button>
            ) : (
              <>
                <div className="requirement-list">
                  {snapshot.requirements.map((requirement) => (
                    <div className={`requirement ${requirement.status}`} key={requirement.key}>
                      {requirement.status === 'present' ? (
                        <Check size={16} />
                      ) : (
                        <CircleAlert size={16} />
                      )}
                      <span>
                        <strong>{requirement.label}</strong>
                        <small>{requirement.rationale}</small>
                      </span>
                      <em>{requirement.status === 'present' ? 'Present' : 'Missing'}</em>
                    </div>
                  ))}
                </div>
                {!snapshot.package && (
                  <button
                    className="primary-action"
                    type="button"
                    disabled={busy}
                    onClick={() => void onAction({ type: 'prepare_referral_package' })}
                  >
                    Prepare case version 1
                  </button>
                )}
              </>
            )}
          </div>
        </article>
      )}

      {snapshot.package && (
        <article className="referral-step-card package-card">
          <span className="step-number">4</span>
          <div className="step-content">
            <div className="package-heading">
              <div>
                <h2>Case version {snapshot.package.case_version}</h2>
                <p>
                  For {snapshot.package.clinician_name} at {snapshot.package.centre_name}
                </p>
              </div>
              <span>{snapshot.package.provenance_links} provenance links</span>
            </div>
            <div className="sharing-boundary">
              <div>
                <h3>Shared after approval</h3>
                <ul>
                  {snapshot.package.structured_context.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
              <div>
                <h3>Remains in Milan</h3>
                <ul>
                  {snapshot.package.retained_in_milan.map((item) => <li key={item}>{item}</li>)}
                </ul>
                <p>Original files can be retrieved later through authorized hospital access.</p>
              </div>
            </div>
            <label htmlFor="referral-assessment">Dr Bianchi's referral assessment</label>
            <textarea
              id="referral-assessment"
              value={assessment}
              disabled={busy || snapshot.package.approved}
              onChange={(event) => setAssessment(event.target.value)}
            />
            {snapshot.package.approved ? (
              <div className="sent-confirmation" role="status">
                <ShieldCheck size={20} />
                <span>
                  <strong>Case version 1 approved and sent</strong>
                  Utrecht is now the next clinical workspace.
                </span>
              </div>
            ) : (
              <button
                className="primary-action"
                type="button"
                disabled={busy || assessment.trim().length < 20}
                onClick={() =>
                  void onAction({
                    type: 'approve_referral_package',
                    referral_assessment: assessment.trim(),
                  })
                }
              >
                Approve and send case version 1
                <ArrowRight size={17} />
              </button>
            )}
          </div>
        </article>
      )}
    </section>
  )
}

function ActivityTimeline({ activity }: { activity: JourneyActivity[] }) {
  return (
    <aside className="activity-timeline" aria-label="Referral activity">
      <div className="timeline-heading">
        <div>
          <p className="eyebrow">Referral activity</p>
          <h2>Clinical actions</h2>
        </div>
        <span>{activity.length}</span>
      </div>
      {activity.length === 0 ? (
        <div className="timeline-empty">
          <History size={22} />
          <p>Workspace and patient actions will appear here.</p>
        </div>
      ) : (
        <ol>
          {[...activity].reverse().map((event) => (
            <li key={event.id}>
              <span className="timeline-dot" aria-hidden="true" />
              <div>
                <small>{event.institution}</small>
                <strong>{event.title}</strong>
                <p>{event.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
      <div className="timeline-boundary">
        <Building2 size={17} />
        <p>
          Hospital-owned source queries and cross-hospital approvals are added in the next
          increments.
        </p>
      </div>
    </aside>
  )
}

export default App
