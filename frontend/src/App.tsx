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
  kind: 'workspace_opened' | 'patient_selected'
  actor: string
  institution: string
  title: string
  detail: string
  occurred_at: string
}

interface JourneySnapshot {
  active_role: JourneyRole | null
  selected_patient_id: string | null
  roles: JourneyRoleView[]
  patients: JourneyPatient[]
  stages: JourneyStage[]
  activity: JourneyActivity[]
}

type Screen = 'role' | 'patients' | 'selected'

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
          setScreen(restored.selected_patient_id ? 'selected' : 'patients')
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
      setScreen(updated.selected_patient_id ? 'selected' : 'patients')
    } else {
      setNotice('The Utrecht receiving screen is implemented in issue #10.')
    }
  }

  async function selectPatient(patientId: string) {
    const updated = await applyAction({ type: 'select_patient', patient_id: patientId })
    if (updated) setScreen('selected')
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
              <SelectedPatient patient={selectedPatient} />
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

function SelectedPatient({ patient }: { patient: JourneyPatient }) {
  return (
    <section className="selected-patient screen-stage">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            {patient.display_name} · {patient.case_id}
          </p>
          <h1>Patient selected for referral preparation</h1>
        </div>
        <p>The next increment adds the federated checks of Milan hospital systems.</p>
      </div>
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
        <span className="stage-ready">
          <Check size={17} />
          Ready for local data check
        </span>
      </article>
      <div className="next-increment-note" role="status">
        <ShieldCheck size={18} />
        <span>
          <strong>Journey foundation complete</strong>
          Federated Milan source checks are the next implementation increment.
        </span>
      </div>
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
