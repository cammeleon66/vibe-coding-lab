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
import { useEffect, useRef, useState } from 'react'
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
    | 'version_acknowledged'
    | 'provisional_opinion_recorded'
    | 'evidence_requested'
    | 'evidence_update_received'
    | 'evidence_update_approved'
    | 'final_opinion_recorded'
    | 'mdo_accepted'
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
  acknowledged_versions: number[]
  provisional_opinion: string | null
  evidence_request: {
    case_version: number
    requested_evidence: string[]
    clinical_reason: string
    requested_by: string
    requested_at: string
  } | null
  update_available_version: number | null
  update_approved_versions: number[]
  final_opinion: string | null
  mdo_outcome: {
    case_version: number
    specialist: string
    final_opinion: string
    scheduled_for: string
    accepted_at: string
    next_responsible_actor: string
    next_action: string
  } | null
  evidence_update: {
    case_version: number
    previous_version: number
    added_evidence: string[]
    changed_findings: string[]
    remaining_uncertainty: string[]
  } | null
}

type Screen =
  | 'role'
  | 'patients'
  | 'selected'
  | 'referral'
  | 'utrecht'
  | 'evidence_update'
  | 'mdo'
  | 'outcome'

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
  const screenRef = useRef<HTMLElement>(null)

  useEffect(() => {
    requestJson<JourneySnapshot>('/api/journey')
      .then((restored) => {
        setSnapshot(restored)
        if (restored.active_role === 'milan') {
          setScreen(
            restored.mdo_outcome
              ? 'outcome'
              : restored.evidence_request
                ? 'evidence_update'
                : restored.package
              ? 'referral'
              : restored.selected_patient_id
                ? 'selected'
                : 'patients',
          )
        } else if (restored.active_role === 'utrecht') {
          setScreen(restored.update_approved_versions.length > 0 ? 'mdo' : 'utrecht')
        }
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Could not restore the journey.')
      })
  }, [])

  useEffect(() => {
    const heading = screenRef.current?.querySelector<HTMLElement>('h1')
    if (!heading) return
    heading.tabIndex = -1
    heading.focus()
  }, [screen, snapshot?.active_role, snapshot?.selected_patient_id])

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
        updated.mdo_outcome
          ? 'outcome'
          : updated.evidence_request
            ? 'evidence_update'
            : updated.package
              ? 'referral'
              : updated.selected_patient_id
                ? 'selected'
                : 'patients',
      )
    } else {
      setScreen(updated.update_approved_versions.length > 0 ? 'mdo' : 'utrecht')
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

  async function receiveEvidenceUpdate() {
    setBusy(true)
    setError(null)
    try {
      await requestJson('/api/evidence-arrivals', {
        method: 'POST',
        body: JSON.stringify({
          event_id: 'journey-imaging-001',
          occurred_at: new Date().toISOString(),
        }),
      })
      const updated = await requestJson<JourneySnapshot>('/api/journey')
      setSnapshot(updated)
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'The imaging update could not be received.',
      )
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
                  else if (stage.id === 'utrecht_review') setScreen('utrecht')
                  else if (stage.id === 'evidence_update') setScreen('evidence_update')
                  else if (stage.id === 'mdo_outcome') {
                    setScreen(snapshot.mdo_outcome ? 'outcome' : 'mdo')
                  }
                  else setNotice(`${stage.label} is not available for the current case state.`)
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
          <section className="journey-screen" ref={screenRef}>
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
                onOpenUtrecht={() => void enterRole('utrecht')}
              />
            )}
            {screen === 'utrecht' && selectedPatient && (
              <UtrechtReview
                snapshot={snapshot}
                patient={selectedPatient}
                busy={busy}
                onAction={applyAction}
                onReturnMilan={() => void enterRole('milan')}
              />
            )}
            {screen === 'evidence_update' && selectedPatient && (
              <EvidenceUpdate
                snapshot={snapshot}
                patient={selectedPatient}
                busy={busy}
                onAction={applyAction}
                onReceive={receiveEvidenceUpdate}
                onOpenUtrecht={() => void enterRole('utrecht')}
              />
            )}
            {screen === 'mdo' && selectedPatient && (
              <MdoReview
                snapshot={snapshot}
                patient={selectedPatient}
                busy={busy}
                onAction={applyAction}
                onReturnMilan={() => void enterRole('milan')}
              />
            )}
            {screen === 'outcome' && selectedPatient && (
              <MilanOutcome snapshot={snapshot} patient={selectedPatient} />
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
          The exchange calls each hospital-owned source separately. Results show what can support
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
  onOpenUtrecht,
}: {
  snapshot: JourneySnapshot
  patient: JourneyPatient
  busy: boolean
  onAction: (action: object) => Promise<JourneySnapshot | null>
  onOpenUtrecht: () => void
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
              <>
                <div className="sent-confirmation" role="status">
                  <ShieldCheck size={20} />
                  <span>
                    <strong>Case version 1 approved and sent</strong>
                    Utrecht is now the next clinical workspace.
                  </span>
                </div>
                <button
                  className="primary-action"
                  type="button"
                  disabled={busy}
                  onClick={onOpenUtrecht}
                >
                  Continue as Dr Eva van Dijk
                  <ArrowRight size={17} />
                </button>
              </>
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

const defaultProvisionalOpinion =
  'The treatment response appears sufficient to discuss liver-directed treatment, but original baseline CT and current liver MRI are needed before a definitive resectability opinion.'

const defaultEvidenceReason =
  'Original lesion sites and current vessel relationships must be reviewed before the multidisciplinary resectability decision.'

function UtrechtReview({
  snapshot,
  patient,
  busy,
  onAction,
  onReturnMilan,
}: {
  snapshot: JourneySnapshot
  patient: JourneyPatient
  busy: boolean
  onAction: (action: object) => Promise<JourneySnapshot | null>
  onReturnMilan: () => void
}) {
  const [opinion, setOpinion] = useState(
    snapshot.provisional_opinion ?? defaultProvisionalOpinion,
  )
  const [reason, setReason] = useState(
    snapshot.evidence_request?.clinical_reason ?? defaultEvidenceReason,
  )
  const version = snapshot.package?.case_version ?? 1
  const acknowledged = snapshot.acknowledged_versions.includes(version)
  const requestedImaging =
    snapshot.package?.missing_evidence.filter(
      (item) => item.includes('CT') || item.includes('MRI'),
    ) ?? []

  return (
    <section className="utrecht-review screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dr Eva van Dijk · UMC Utrecht</p>
          <h1>Review incoming referral</h1>
        </div>
        <p>
          Review the exact approved package, record a provisional specialist opinion, and ask
          Milan for evidence needed before the final decision.
        </p>
      </div>

      <div className="incoming-referral-heading">
        <div>
          <span>Incoming referral</span>
          <h2>{patient.display_name}</h2>
          <p>{patient.diagnosis}</p>
        </div>
        <strong>Case version {version}</strong>
      </div>

      <article className="receiving-card">
        <h2>Approved referral from Milan</h2>
        <dl>
          <div>
            <dt>Clinical question</dt>
            <dd>{snapshot.package?.clinical_question}</dd>
          </div>
          <div>
            <dt>Dr Bianchi's referral assessment</dt>
            <dd>{snapshot.package?.referral_assessment}</dd>
          </div>
        </dl>
        <p className="package-version-note">
          This review applies to case version {version}. Source provenance remains attached to
          the structured package.
        </p>
        {!acknowledged ? (
          <button
            className="primary-action"
            type="button"
            disabled={busy}
            onClick={() =>
              void onAction({ type: 'acknowledge_case_version', case_version: version })
            }
          >
            Acknowledge case version {version}
          </button>
        ) : (
          <p className="confirmed-line">
            <Check size={16} /> Version {version} acknowledged by Dr van Dijk
          </p>
        )}
      </article>

      {acknowledged && (
        <article className="receiving-card">
          <h2>Provisional specialist opinion</h2>
          <p>
            This is Dr van Dijk's clinical assessment. It is separate from the Milan referral
            assessment above.
          </p>
          <label htmlFor="provisional-opinion">Opinion for case version {version}</label>
          <textarea
            id="provisional-opinion"
            value={opinion}
            disabled={busy || snapshot.provisional_opinion !== null}
            onChange={(event) => setOpinion(event.target.value)}
          />
          {!snapshot.provisional_opinion ? (
            <button
              className="primary-action"
              type="button"
              disabled={busy || opinion.trim().length < 20}
              onClick={() =>
                void onAction({
                  type: 'record_provisional_opinion',
                  opinion: opinion.trim(),
                })
              }
            >
              Record provisional opinion
            </button>
          ) : (
            <p className="confirmed-line">
              <Check size={16} /> Provisional opinion recorded
            </p>
          )}
        </article>
      )}

      {snapshot.provisional_opinion && (
        <article className="receiving-card evidence-request-card">
          <h2>Evidence needed from Milan</h2>
          <div className="requested-evidence">
            {requestedImaging.map((item) => (
              <span key={item}>
                <CircleAlert size={15} />
                {item}
              </span>
            ))}
          </div>
          <label htmlFor="evidence-reason">Clinical reason</label>
          <textarea
            id="evidence-reason"
            value={reason}
            disabled={busy || snapshot.evidence_request !== null}
            onChange={(event) => setReason(event.target.value)}
          />
          {snapshot.evidence_request ? (
            <>
              <div className="sent-confirmation" role="status">
                <ShieldCheck size={20} />
                <span>
                  <strong>Imaging request sent to Milan</strong>
                  Dr Bianchi is now responsible for reviewing and approving the update.
                </span>
              </div>
              <button
                className="primary-action"
                type="button"
                disabled={busy}
                onClick={onReturnMilan}
              >
                Continue as Dr Luca Bianchi
                <ArrowRight size={17} />
              </button>
            </>
          ) : (
            <button
              className="primary-action"
              type="button"
              disabled={busy || reason.trim().length < 20 || requestedImaging.length === 0}
              onClick={() =>
                void onAction({
                  type: 'request_evidence',
                  requested_evidence: requestedImaging,
                  clinical_reason: reason.trim(),
                })
              }
            >
              Request missing imaging
              <ArrowRight size={17} />
            </button>
          )}
        </article>
      )}
    </section>
  )
}

function EvidenceUpdate({
  snapshot,
  patient,
  busy,
  onAction,
  onReceive,
  onOpenUtrecht,
}: {
  snapshot: JourneySnapshot
  patient: JourneyPatient
  busy: boolean
  onAction: (action: object) => Promise<JourneySnapshot | null>
  onReceive: () => void
  onOpenUtrecht: () => void
}) {
  const update = snapshot.evidence_update
  const approved =
    update !== null && snapshot.update_approved_versions.includes(update.case_version)

  return (
    <section className="evidence-update-screen screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dr Luca Bianchi · Milan</p>
          <h1>Review requested imaging update</h1>
        </div>
        <p>
          Utrecht requested named imaging for {patient.display_name}. New evidence stays in Milan
          until Dr Bianchi approves the new case version.
        </p>
      </div>

      <article className="receiving-card">
        <h2>Utrecht evidence request</h2>
        <div className="requested-evidence">
          {snapshot.evidence_request?.requested_evidence.map((item) => (
            <span key={item}>
              <CircleAlert size={15} />
              {item}
            </span>
          ))}
        </div>
        <p>{snapshot.evidence_request?.clinical_reason}</p>
      </article>

      {!update ? (
        <article className="receiving-card source-arrival-card">
          <h2>Hospital imaging event</h2>
          <p>
            Simulate the approved demonstration event from Milan's imaging archive. The existing
            evidence-arrival path prepares an immutable version 2 and keeps version 1 available.
          </p>
          <code>POST /api/evidence-arrivals · Microsoft.Storage.BlobCreated</code>
          <button className="primary-action" type="button" disabled={busy} onClick={onReceive}>
            Receive requested imaging
          </button>
        </article>
      ) : (
        <article className="receiving-card update-delta-card">
          <div className="package-heading">
            <div>
              <h2>Case version {update.case_version}</h2>
              <p>Compared with approved case version {update.previous_version}</p>
            </div>
            <span>Immutable update</span>
          </div>
          <h3>Added evidence</h3>
          <ul>
            {update.added_evidence.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <h3>Changed findings</h3>
          <ul>
            {update.changed_findings.map((item) => <li key={item}>{item}</li>)}
          </ul>
          {!approved ? (
            <button
              className="primary-action"
              type="button"
              disabled={busy}
              onClick={() =>
                void onAction({
                  type: 'approve_evidence_update',
                  case_version: update.case_version,
                })
              }
            >
              Approve sharing case version {update.case_version}
              <ArrowRight size={17} />
            </button>
          ) : (
            <>
              <div className="sent-confirmation" role="status">
                <ShieldCheck size={20} />
                <span>
                  <strong>Case version {update.case_version} approved</strong>
                  Utrecht can now acknowledge and complete the specialist review.
                </span>
              </div>
              <button
                className="primary-action"
                type="button"
                disabled={busy}
                onClick={onOpenUtrecht}
              >
                Continue as Dr Eva van Dijk
                <ArrowRight size={17} />
              </button>
            </>
          )}
        </article>
      )}
    </section>
  )
}

const defaultFinalOpinion =
  'Case version 2 accounts for the original lesion sites and current vessel relationships. The case is appropriate for Utrecht liver MDO review to determine the combined local treatment plan.'

function MdoReview({
  snapshot,
  patient,
  busy,
  onAction,
  onReturnMilan,
}: {
  snapshot: JourneySnapshot
  patient: JourneyPatient
  busy: boolean
  onAction: (action: object) => Promise<JourneySnapshot | null>
  onReturnMilan: () => void
}) {
  const version = snapshot.update_available_version ?? 2
  const acknowledged = snapshot.acknowledged_versions.includes(version)
  const [opinion, setOpinion] = useState(snapshot.final_opinion ?? defaultFinalOpinion)

  return (
    <section className="mdo-review-screen screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dr Eva van Dijk · UMC Utrecht</p>
          <h1>Complete specialist review</h1>
        </div>
        <p>
          Acknowledge the approved update, record the final opinion, and accept the current
          version into the Utrecht multidisciplinary meeting.
        </p>
      </div>

      <article className="incoming-referral-heading">
        <div>
          <span>Approved update from Milan</span>
          <h2>{patient.display_name}</h2>
          <p>{snapshot.evidence_update?.added_evidence.join(' · ')}</p>
        </div>
        <strong>Case version {version}</strong>
      </article>

      <article className="receiving-card">
        <h2>Version acknowledgement</h2>
        {!acknowledged ? (
          <button
            className="primary-action"
            type="button"
            disabled={busy}
            onClick={() =>
              void onAction({ type: 'acknowledge_case_version', case_version: version })
            }
          >
            Acknowledge case version {version}
          </button>
        ) : (
          <p className="confirmed-line"><Check size={16} /> Version {version} acknowledged</p>
        )}
      </article>

      {acknowledged && (
        <article className="receiving-card">
          <h2>Final specialist opinion</h2>
          <label htmlFor="final-opinion">Opinion for case version {version}</label>
          <textarea
            id="final-opinion"
            value={opinion}
            disabled={busy || snapshot.final_opinion !== null}
            onChange={(event) => setOpinion(event.target.value)}
          />
          {!snapshot.final_opinion ? (
            <button
              className="primary-action"
              type="button"
              disabled={busy || opinion.trim().length < 20}
              onClick={() =>
                void onAction({ type: 'record_final_opinion', opinion: opinion.trim() })
              }
            >
              Record final specialist opinion
            </button>
          ) : (
            <p className="confirmed-line"><Check size={16} /> Final opinion recorded</p>
          )}
        </article>
      )}

      {snapshot.final_opinion && (
        <article className="receiving-card">
          <h2>Utrecht MDO acceptance</h2>
          <p>
            The meeting will review case version {version}. After acceptance, the opinion,
            schedule, and next responsibility return to Milan.
          </p>
          {snapshot.mdo_outcome ? (
            <>
              <div className="sent-confirmation" role="status">
                <ShieldCheck size={20} />
                <span>
                  <strong>Accepted into Utrecht MDO</strong>
                  {snapshot.mdo_outcome.scheduled_for}
                </span>
              </div>
              <button
                className="primary-action"
                type="button"
                disabled={busy}
                onClick={onReturnMilan}
              >
                Return outcome to Dr Luca Bianchi
                <ArrowRight size={17} />
              </button>
            </>
          ) : (
            <button
              className="primary-action"
              type="button"
              disabled={busy}
              onClick={() =>
                void onAction({
                  type: 'accept_mdo_outcome',
                  scheduled_for: '29 September 2026 at 14:00 CEST',
                  next_action:
                    'Discuss the Utrecht opinion and MDO schedule with Giulia, confirm attendance, and provide any interval clinical changes.',
                })
              }
            >
              Accept case version {version} into MDO
            </button>
          )}
        </article>
      )}
    </section>
  )
}

function MilanOutcome({
  snapshot,
  patient,
}: {
  snapshot: JourneySnapshot
  patient: JourneyPatient
}) {
  const outcome = snapshot.mdo_outcome
  if (!outcome) return null
  return (
    <section className="milan-outcome screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dr Luca Bianchi · Milan</p>
          <h1>Utrecht outcome received</h1>
        </div>
        <p>
          The cross-border referral is closed for {patient.display_name}. Milan now owns the next
          clinical action.
        </p>
      </div>
      <article className="outcome-card">
        <span className="outcome-status"><Check size={18} /> Accepted into Utrecht MDO</span>
        <h2>Case version {outcome.case_version}</h2>
        <dl>
          <div>
            <dt>Specialist opinion · {outcome.specialist}</dt>
            <dd>{outcome.final_opinion}</dd>
          </div>
          <div>
            <dt>MDO schedule</dt>
            <dd>{outcome.scheduled_for}</dd>
          </div>
          <div>
            <dt>Next responsibility · {outcome.next_responsible_actor}</dt>
            <dd>{outcome.next_action}</dd>
          </div>
        </dl>
      </article>
    </section>
  )
}

function ActivityTimeline({ activity }: { activity: JourneyActivity[] }) {
  return (
    <aside className="activity-timeline" aria-label="Referral activity" tabIndex={0}>
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
          This timeline records hospital-owned source queries, clinician approvals, version
          acknowledgements, and the returned MDO outcome.
        </p>
      </div>
    </aside>
  )
}

export default App
