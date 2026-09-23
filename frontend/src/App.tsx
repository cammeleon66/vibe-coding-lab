import {
  ArrowRight,
  Check,
  CircleAlert,
  CircleDot,
  FileCheck2,
  Globe2,
  Languages,
  MapPin,
  Network,
  RotateCcw,
  ShieldCheck,
  Stethoscope,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import './App.css'

type MatchStatus = 'match' | 'condition'
type RequirementStatus = 'present' | 'missing'
type Urgency = 'routine' | 'expedited' | 'urgent'

interface ClinicalNeed {
  case_id: string
  diagnosis: string
  decision_focus: string
  referring_country: string
  preferred_languages: string[]
  available_evidence: string[]
}

interface Clinician {
  id: string
  name: string
  role: string
  specialties: string[]
  languages: string[]
  fictional: boolean
  eligible: boolean
}

interface RequirementDefinition {
  key: string
  label: string
  evidence_type: string
  rationale: string
}

interface Centre {
  id: string
  name: string
  city: string
  country: string
  network_context: string
  profile_label: string
  expertise_tags: string[]
  accepted_evidence: string[]
  languages: string[]
  synthetic_availability: string
  referral_pathway: string
  requirements: RequirementDefinition[]
  clinicians: Clinician[]
  simulated: boolean
}

interface MatchReason {
  label: string
  detail: string
  status: MatchStatus
}

interface ExpertMatch {
  centre: Centre
  score: number
  reasons: MatchReason[]
  conditions: string[]
}

interface MatchResponse {
  need: ClinicalNeed
  matches: ExpertMatch[]
  limitations: string[]
}

interface ReferralRequirement {
  key: string
  label: string
  rationale: string
  status: RequirementStatus
}

interface Referral {
  id: string
  version: number
  created_at: string
  need: ClinicalNeed
  urgency: Urgency
  sender: ReferralSender
  centre: Centre
  clinician: Clinician
  requirements: ReferralRequirement[]
  status: string
  responsibility: {
    actor: string
    action: string
  }
  limitations: string[]
}

interface ReferralSender {
  clinician_name: string
  institution: string
  country: string
}

const initialNeed: ClinicalNeed = {
  case_id: 'CRC-EU-001',
  diagnosis: 'Metastatic colorectal cancer with liver-limited metastases',
  decision_focus: 'Conversion therapy and liver-metastasis resectability',
  referring_country: 'Italy',
  preferred_languages: ['Italian', 'English'],
  available_evidence: ['pathology', 'treatment_timeline', 'current_ct_summary'],
}

const initialSender: ReferralSender = {
  clinician_name: 'Dr Luca Bianchi',
  institution: 'Istituto Nazionale dei Tumori, Milan',
  country: 'Italy',
}

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}.`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

function App() {
  const [need, setNeed] = useState(initialNeed)
  const [sender, setSender] = useState(initialSender)
  const [urgency, setUrgency] = useState<Urgency>('expedited')
  const [matches, setMatches] = useState<MatchResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedClinicianId, setSelectedClinicianId] = useState<string | null>(null)
  const [referral, setReferral] = useState<Referral | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    requestJson<Referral | null>('/api/referrals/current')
      .then(setReferral)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Could not restore the demo state.')
      })
  }, [])

  const selected = useMemo(
    () => matches?.matches.find((item) => item.centre.id === selectedId) ?? null,
    [matches, selectedId],
  )

  function selectCentre(match: ExpertMatch) {
    setSelectedId(match.centre.id)
    setSelectedClinicianId(match.centre.clinicians.find((item) => item.eligible)?.id ?? null)
  }

  async function findExpertise() {
    setBusy(true)
    setError(null)
    try {
      const result = await requestJson<MatchResponse>('/api/expert-matches', {
        method: 'POST',
        body: JSON.stringify(need),
      })
      setMatches(result)
      const topMatch = result.matches[0]
      if (topMatch) selectCentre(topMatch)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Expert discovery failed.')
    } finally {
      setBusy(false)
    }
  }

  async function initiateReferral() {
    if (!selected || !selectedClinicianId) return
    setBusy(true)
    setError(null)
    try {
      const created = await requestJson<Referral>('/api/referrals', {
        method: 'POST',
        body: JSON.stringify({
          need,
          centre_id: selected.centre.id,
          clinician_id: selectedClinicianId,
          urgency,
          sender,
        }),
      })
      setReferral(created)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Referral creation failed.')
    } finally {
      setBusy(false)
    }
  }

  async function resetDemo() {
    setBusy(true)
    setError(null)
    try {
      await requestJson<void>('/api/reset', { method: 'POST' })
      setReferral(null)
      setMatches(null)
      setSelectedId(null)
      setSelectedClinicianId(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not reset the demo.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main>
      <header className="masthead">
        <a className="brand" href="/" aria-label="European Oncology Exchange">
          <span className="brand-mark" aria-hidden="true">
            <Network size={18} strokeWidth={1.7} />
          </span>
          <span>
            <strong>European Oncology Exchange</strong>
            <small>Synthetic collaboration demonstrator</small>
          </span>
        </a>
        <div className="mode-label">
          <CircleDot size={14} />
          Deterministic rehearsal
        </div>
      </header>

      <section className="journey-rail" aria-label="Demonstration journey">
        {['Find expertise', 'Open collaboration', 'Prepare evidence', 'Human review', 'MDO'].map(
          (step, index) => (
            <div
              className={`journey-step ${
                referral ? (index < 2 ? 'complete' : '') : matches && index === 0 ? 'complete' : ''
              } ${(!matches && index === 0) || (matches && !referral && index === 1) ? 'active' : ''}`}
              key={step}
            >
              <span>{String(index + 1).padStart(2, '0')}</span>
              {step}
            </div>
          ),
        )}
      </section>

      {error && (
        <div className="alert" role="alert">
          <CircleAlert size={18} />
          <span>{error}</span>
        </div>
      )}

      {referral ? (
        <ReferralOpened referral={referral} busy={busy} onReset={resetDemo} />
      ) : (
        <>
          <section className="hero">
            <div className="hero-copy">
              <p className="eyebrow">Milan · synthetic case CRC-EU-001</p>
              <h1>Find the right room before moving the case.</h1>
              <p className="hero-lede">
                A patient may need expertise beyond one hospital. Start from the clinical need,
                discover a credible European centre, then carry the evidence—not the burden—to
                the right colleague.
              </p>
              <button className="primary-action" onClick={findExpertise} disabled={busy}>
                <Globe2 size={19} />
                {busy ? 'Searching the network…' : 'Find European expertise'}
                <ArrowRight size={18} />
              </button>
            </div>
            <ClinicalQuestion
              need={need}
              sender={sender}
              urgency={urgency}
              onNeedChange={setNeed}
              onSenderChange={setSender}
              onUrgencyChange={setUrgency}
            />
          </section>

          {matches && (
            <section className="discovery" aria-live="polite">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Explainable discovery</p>
                  <h2>Three possible rooms. One strongest fit.</h2>
                </div>
                <p>
                  Ranked from the synthetic capability profiles and the evidence currently
                  available in Milan.
                </p>
              </div>

              <div className="network-layout">
                <div className="centre-list" role="list" aria-label="Matched expert centres">
                  {matches.matches.map((match, index) => (
                    <button
                      className={`centre-row ${selectedId === match.centre.id ? 'selected' : ''}`}
                      key={match.centre.id}
                      onClick={() => selectCentre(match)}
                      role="listitem"
                      type="button"
                    >
                      <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                      <span className="centre-name">
                        <strong>{match.centre.name}</strong>
                        <small>
                          {match.centre.city}, {match.centre.country}
                        </small>
                      </span>
                      <span className="score">Score {match.score}</span>
                      <ArrowRight size={17} />
                    </button>
                  ))}
                  <div className="directory-boundary">
                    <ShieldCheck size={17} />
                    <span>{matches.limitations[0]}</span>
                  </div>
                </div>

                {selected && (
                  <article className="match-detail">
                    <div className="match-title">
                      <div>
                        <p className="profile-label">{selected.centre.profile_label}</p>
                        <h3>{selected.centre.name}</h3>
                        <p>{selected.centre.network_context}</p>
                      </div>
                      <div className="match-score">
                        <strong>{selected.score}</strong>
                        <span>match score</span>
                      </div>
                    </div>

                    <div className="reason-grid">
                      {selected.reasons.map((reason) => (
                        <div className="reason" key={reason.label}>
                          {reason.status === 'match' ? (
                            <Check size={17} />
                          ) : (
                            <CircleAlert size={17} />
                          )}
                          <div>
                            <strong>{reason.label}</strong>
                            <p>{reason.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="clinician-line">
                      <div className="clinician-avatar" aria-hidden="true">
                        EV
                      </div>
                      <div>
                        <small>Eligible clinician in this demonstration</small>
                        <label className="sr-only" htmlFor="clinician">
                          Select eligible clinician
                        </label>
                        <select
                          id="clinician"
                          value={selectedClinicianId ?? ''}
                          onChange={(event) => setSelectedClinicianId(event.target.value)}
                        >
                          {selected.centre.clinicians
                            .filter((clinician) => clinician.eligible)
                            .map((clinician) => (
                              <option value={clinician.id} key={clinician.id}>
                                {clinician.name} · {clinician.role}
                              </option>
                            ))}
                        </select>
                      </div>
                      <div className="language">
                        <Languages size={16} />
                        {selected.centre.clinicians
                          .find((clinician) => clinician.id === selectedClinicianId)
                          ?.languages.join(' · ')}
                      </div>
                    </div>

                    <div className="referral-path">
                      <FileCheck2 size={18} />
                      <div>
                        <strong>Referral path</strong>
                        <p>{selected.centre.referral_pathway}</p>
                      </div>
                    </div>

                    <button
                      className="primary-action full"
                      onClick={initiateReferral}
                      disabled={busy || !selectedClinicianId}
                    >
                      <Stethoscope size={19} />
                      {busy ? 'Opening collaboration…' : 'Request specialist collaboration'}
                      <ArrowRight size={18} />
                    </button>
                  </article>
                )}
              </div>
            </section>
          )}
        </>
      )}

      <footer>
        <span>Demonstration system · No real patient data</span>
        <span>No live directory, credential or availability verification</span>
      </footer>
    </main>
  )
}

function ClinicalQuestion({
  need,
  sender,
  urgency,
  onNeedChange,
  onSenderChange,
  onUrgencyChange,
}: {
  need: ClinicalNeed
  sender: ReferralSender
  urgency: Urgency
  onNeedChange: (need: ClinicalNeed) => void
  onSenderChange: (sender: ReferralSender) => void
  onUrgencyChange: (urgency: Urgency) => void
}) {
  return (
    <aside className="clinical-question">
      <div className="route-label">
        <MapPin size={17} />
        Referring team · Milan
      </div>
      <p className="case-label">Clinical need</p>
      <div className="clinical-form">
        <label>
          Clinical question
          <textarea
            value={need.decision_focus}
            onChange={(event) => onNeedChange({ ...need, decision_focus: event.target.value })}
            rows={3}
          />
        </label>
        <label>
          Diagnosis
          <input
            value={need.diagnosis}
            onChange={(event) => onNeedChange({ ...need, diagnosis: event.target.value })}
          />
        </label>
        <div className="field-grid">
          <label>
            Urgency
            <select
              value={urgency}
              onChange={(event) => onUrgencyChange(event.target.value as Urgency)}
            >
              <option value="routine">Routine</option>
              <option value="expedited">Expedited</option>
              <option value="urgent">Urgent</option>
            </select>
          </label>
          <label>
            Sender
            <input
              value={sender.clinician_name}
              onChange={(event) =>
                onSenderChange({ ...sender, clinician_name: event.target.value })
              }
            />
          </label>
        </div>
        <label>
          Referring institution
          <input
            value={sender.institution}
            onChange={(event) => onSenderChange({ ...sender, institution: event.target.value })}
          />
        </label>
        <div className="evidence-now">
          <span>Evidence now</span>
          <strong>Pathology · treatment timeline · current CT summary</strong>
          <small>Known gap: original liver imaging and full molecular context</small>
        </div>
      </div>
      <div className="question-boundary">
        The platform finds expertise. It does not decide treatment.
      </div>
    </aside>
  )
}

function ReferralOpened({
  referral,
  busy,
  onReset,
}: {
  referral: Referral
  busy: boolean
  onReset: () => void
}) {
  const present = referral.requirements.filter((item) => item.status === 'present').length

  return (
    <section className="referral-opened">
      <div className="route-stage">
        <div className="city">
          <span>Origin</span>
          <strong>{referral.sender.country}</strong>
          <small>{referral.sender.institution}</small>
        </div>
        <div className="route-line">
          <span>{referral.id}</span>
          <div>
            <i />
          </div>
          <small>Collaboration requested</small>
        </div>
        <div className="city destination">
          <span>Expert centre</span>
          <strong>{referral.centre.city}</strong>
          <small>{referral.clinician.name} · fictional</small>
        </div>
      </div>

      <div className="referral-content">
        <div className="referral-intro">
          <p className="eyebrow">Collaboration workspace opened</p>
          <h1>The request now knows what it still needs.</h1>
          <p>
            The selected centre’s review conditions have become part of the case. Available
            evidence can move now; missing evidence remains an explicit responsibility.
          </p>
          <div className="responsibility">
            <CircleAlert size={19} />
            <div>
              <small>Next responsibility</small>
              <strong>
                {referral.responsibility.actor}: {referral.responsibility.action}
              </strong>
            </div>
          </div>
          <p className="referral-meta">
            Sent by {referral.sender.clinician_name} · {referral.urgency} priority
          </p>
        </div>

        <div className="requirements">
          <div className="requirements-head">
            <div>
              <span>Referral readiness</span>
              <strong>
                {present} of {referral.requirements.length} evidence conditions available
              </strong>
            </div>
            <span className="version">Case v{referral.version}</span>
          </div>
          {referral.requirements.map((requirement) => (
            <div className={`requirement ${requirement.status}`} key={requirement.key}>
              <span className="requirement-icon">
                {requirement.status === 'present' ? <Check size={16} /> : <CircleAlert size={16} />}
              </span>
              <div>
                <strong>{requirement.label}</strong>
                <p>{requirement.rationale}</p>
              </div>
              <span>{requirement.status === 'present' ? 'Available' : 'Required'}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="next-chapter">
        <div>
          <p className="eyebrow">Next chapter</p>
          <h2>Prepare the evidence without erasing its origin.</h2>
          <p>
            The next increment connects the two institutional sources and builds the
            source-linked case workspace.
          </p>
        </div>
        <button className="secondary-action" onClick={onReset} disabled={busy}>
          <RotateCcw size={17} />
          Reset rehearsal
        </button>
      </div>
    </section>
  )
}

export default App
