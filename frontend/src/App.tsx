import {
  ArrowRight,
  Check,
  CircleAlert,
  CircleDot,
  ClipboardCheck,
  Database,
  ExternalLink,
  FileCheck2,
  FileSearch,
  GitCompare,
  Globe2,
  History,
  Languages,
  Link2,
  MapPin,
  Network,
  Radio,
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

interface ProvenanceLink {
  evidence_id: string
  source_pointer: string
  source_institution: string
  source_format: string
  observed_at: string
  transformation_status: string
}

interface EvidenceFact {
  key: string
  label: string
  category: string
  raw_value: string
  normalized_value: string | null
  transformation: string
  source_pointer: string
}

interface EvidenceEnvelope {
  source_institution: string
  source_identifier: string
  source_format: string
  observed_at: string
  received_at: string
  content_hash: string
  transformation_status: string
  facts: EvidenceFact[]
  warnings: string[]
  unmapped_values: string[]
  retrieval_reference: string
  original_media_type: string
  original_content: string
}

interface PreparedClaim {
  id: string
  label: string
  category: string
  raw_value: string
  normalized_value: string | null
  kind: string
  transformation: string
  provenance: ProvenanceLink[]
}

interface PreparedCase {
  case_id: string
  referral_id: string
  version: number
  prepared_at: string
  clinical_question: string
  evidence: EvidenceEnvelope[]
  claims: PreparedClaim[]
  conflicts: {
    id: string
    field: string
    description: string
    claim_ids: string[]
    resolution: string
  }[]
  missing: {
    id: string
    field: string
    description: string
    severity: string
    required_by: string
    provenance: ProvenanceLink[]
  }[]
  warnings: string[]
  unmapped_values: string[]
  synthesis: { text: string; support_ids: string[] }[]
  limitations: string[]
  delta: {
    from_version: number
    to_version: number
    added_evidence: {
      evidence_id: string
      label: string
      source_format: string
      source_institution: string
      observed_at: string
    }[]
    changed_findings: {
      subject: string
      before: string
      after: string
      conclusion_requires_reassessment: boolean
    }[]
    remaining_uncertainty: string[]
    affected_human_questions: string[]
  } | null
}

interface EvidenceArrivalResult {
  event_id: string
  duplicate: boolean
  prepared_case: PreparedCase
}

interface CaseUpdateError {
  event_id: string
  message: string
  occurred_at: string
  preserved_version: number
}

type ReviewConditionStatus = 'open' | 'resolved'

interface ReviewCondition {
  issue_id: string
  kind: 'required_evidence' | 'review'
  description: string
  status: ReviewConditionStatus
  resolution: string
}

interface HumanOpinion {
  id: string
  case_id: string
  case_version: number
  reviewer: string
  opinion: string
  conditions: ReviewCondition[]
  next_responsibility: {
    actor: string
    action: string
  }
  recorded_at: string
}

interface HumanReviewState {
  current_case_version: number
  opinion: HumanOpinion | null
  required_conditions: ReviewCondition[]
  stale: boolean
  handoff_ready: boolean
  blockers: string[]
}

interface HandoffManifest {
  id: string
  version: number
  case_id: string
  clinical_question: string
  evidence_version: number
  source_evidence_inventory: string[]
  unresolved_issues: string[]
  opinion_id: string
  responsibility: {
    actor: string
    action: string
  }
  created_at: string
  synthetic_labels: string[]
  launch_url: string
  separate_backend: boolean
  backend_notice: string
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
  const [preparedCase, setPreparedCase] = useState<PreparedCase | null>(null)
  const [previousCase, setPreviousCase] = useState<PreparedCase | null>(null)
  const [inspectedSource, setInspectedSource] = useState<EvidenceEnvelope | null>(null)
  const [caseUpdateError, setCaseUpdateError] = useState<CaseUpdateError | null>(null)
  const [reviewState, setReviewState] = useState<HumanReviewState | null>(null)
  const [handoffManifest, setHandoffManifest] = useState<HandoffManifest | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      requestJson<Referral | null>('/api/referrals/current'),
      requestJson<PreparedCase | null>('/api/cases/current'),
    ])
      .then(([restoredReferral, restoredCase]) => {
        setReferral(restoredReferral)
        setPreparedCase(restoredCase)
        if (restoredCase) {
          void requestJson<CaseUpdateError | null>('/api/cases/current/update-error')
            .then(setCaseUpdateError)
            .catch(() => undefined)
          if (restoredCase.version > 1) {
            void requestJson<PreparedCase>(
              `/api/cases/current/versions/${restoredCase.version - 1}`,
            )
              .then(setPreviousCase)
              .catch(() => undefined)
          }
          void Promise.all([
            requestJson<HumanReviewState>('/api/cases/current/review'),
            requestJson<HandoffManifest[]>('/api/cases/current/handoffs'),
          ])
            .then(([state, items]) => {
              setReviewState(state)
              const currentManifest =
                state.handoff_ready && state.opinion
                  ? items
                      .filter(
                        (item) =>
                          item.evidence_version === restoredCase.version &&
                          item.opinion_id === state.opinion?.id,
                      )
                      .at(-1) ?? null
                  : null
              setHandoffManifest(currentManifest)
            })
            .catch(() => undefined)
        }
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Could not restore the demo state.')
      })
  }, [])

  async function refreshReviewState() {
    try {
      const state = await requestJson<HumanReviewState>('/api/cases/current/review')
      setReviewState(state)
    } catch {
      setReviewState(null)
    }
  }

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
      setPreparedCase(null)
      setPreviousCase(null)
      setCaseUpdateError(null)
      setReviewState(null)
      setHandoffManifest(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Referral creation failed.')
    } finally {
      setBusy(false)
    }
  }

  async function prepareWorkspace() {
    setBusy(true)
    setError(null)
    try {
      const prepared = await requestJson<PreparedCase>('/api/cases/current/prepare', {
        method: 'POST',
      })
      setPreparedCase(prepared)
      setPreviousCase(null)
      setCaseUpdateError(null)
      await refreshReviewState()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Case preparation failed.')
    } finally {
      setBusy(false)
    }
  }

  async function inspectSource(evidenceId: string, version?: number) {
    setBusy(true)
    setError(null)
    try {
      const evidence = await requestJson<EvidenceEnvelope>(
        `/api/cases/current/sources/${encodeURIComponent(evidenceId)}${
          version === undefined ? '' : `?version=${version}`
        }`,
      )
      setInspectedSource(evidence)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Source inspection failed.')
    } finally {
      setBusy(false)
    }
  }

  async function deliverImagingEvidence() {
    if (!preparedCase) return
    setBusy(true)
    setError(null)
    try {
      const result = await requestJson<EvidenceArrivalResult>('/api/evidence-arrivals', {
        method: 'POST',
        body: JSON.stringify({
          event_id: 'local-event-grid-imaging-001',
          event_type: 'Microsoft.Storage.BlobCreated',
          subject: '/synthetic/milan/CRC-EU-001/imaging',
          case_id: preparedCase.case_id,
          evidence_set: 'baseline-and-restaging-imaging',
          occurred_at: new Date().toISOString(),
        }),
      })
      setPreviousCase(preparedCase)
      setPreparedCase(result.prepared_case)
      setCaseUpdateError(null)
      setHandoffManifest(null)
      await refreshReviewState()
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Evidence update failed.'
      setError(message)
      setCaseUpdateError({
        event_id: 'local-event-grid-imaging-001',
        message,
        occurred_at: new Date().toISOString(),
        preserved_version: preparedCase.version,
      })
    } finally {
      setBusy(false)
    }
  }

  async function saveHumanReview(command: {
    case_version: number
    reviewer: string
    opinion: string
    conditions: {
      issue_id: string
      status: ReviewConditionStatus
      resolution: string
    }[]
    next_responsibility: {
      actor: string
      action: string
    }
  }) {
    setBusy(true)
    setError(null)
    try {
      const state = await requestJson<HumanReviewState>('/api/cases/current/reviews', {
        method: 'POST',
        body: JSON.stringify(command),
      })
      setReviewState(state)
      setHandoffManifest(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Human review could not be saved.')
    } finally {
      setBusy(false)
    }
  }

  async function createMdoHandoff() {
    if (!preparedCase || !reviewState?.opinion) return
    setBusy(true)
    setError(null)
    try {
      const manifest = await requestJson<HandoffManifest>('/api/cases/current/handoffs', {
        method: 'POST',
        body: JSON.stringify({
          case_version: preparedCase.version,
          opinion_id: reviewState.opinion.id,
        }),
      })
      setHandoffManifest(manifest)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'MDO handoff could not be created.')
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
      setPreparedCase(null)
      setPreviousCase(null)
      setInspectedSource(null)
      setCaseUpdateError(null)
      setReviewState(null)
      setHandoffManifest(null)
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
                preparedCase
                  ? index < 3
                    ? 'complete'
                    : ''
                  : referral
                    ? index < 2
                      ? 'complete'
                      : ''
                    : matches && index === 0
                      ? 'complete'
                      : ''
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

      {preparedCase && referral ? (
        <PreparedWorkspace
          preparedCase={preparedCase}
          previousCase={previousCase}
          referral={referral}
          busy={busy}
          caseUpdateError={caseUpdateError}
          reviewState={reviewState}
          handoffManifest={handoffManifest}
          inspectedSource={inspectedSource}
          onInspectSource={inspectSource}
          onDeliverImaging={deliverImagingEvidence}
          onSaveReview={saveHumanReview}
          onCreateHandoff={createMdoHandoff}
          onCloseSource={() => setInspectedSource(null)}
          onReset={resetDemo}
        />
      ) : referral ? (
        <ReferralOpened
          referral={referral}
          busy={busy}
          onPrepare={prepareWorkspace}
          onReset={resetDemo}
        />
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
  onPrepare,
  onReset,
}: {
  referral: Referral
  busy: boolean
  onPrepare: () => void
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
        <div className="next-actions">
          <button className="primary-action" onClick={onPrepare} disabled={busy}>
            <Database size={17} />
            {busy ? 'Preparing evidence…' : 'Prepare clinical workspace'}
          </button>
          <button className="secondary-action" onClick={onReset} disabled={busy}>
            <RotateCcw size={17} />
            Reset rehearsal
          </button>
        </div>
      </div>
    </section>
  )
}

function PreparedWorkspace({
  preparedCase,
  previousCase,
  referral,
  busy,
  caseUpdateError,
  reviewState,
  handoffManifest,
  inspectedSource,
  onInspectSource,
  onDeliverImaging,
  onSaveReview,
  onCreateHandoff,
  onCloseSource,
  onReset,
}: {
  preparedCase: PreparedCase
  previousCase: PreparedCase | null
  referral: Referral
  busy: boolean
  caseUpdateError: CaseUpdateError | null
  reviewState: HumanReviewState | null
  handoffManifest: HandoffManifest | null
  inspectedSource: EvidenceEnvelope | null
  onInspectSource: (evidenceId: string, version?: number) => void
  onDeliverImaging: () => void
  onSaveReview: (command: {
    case_version: number
    reviewer: string
    opinion: string
    conditions: {
      issue_id: string
      status: ReviewConditionStatus
      resolution: string
    }[]
    next_responsibility: {
      actor: string
      action: string
    }
  }) => void
  onCreateHandoff: () => void
  onCloseSource: () => void
  onReset: () => void
}) {
  return (
    <section className="workspace">
      <header className="workspace-head">
        <div>
          <p className="eyebrow">Prepared clinical workspace · case v{preparedCase.version}</p>
          <h1>Evidence together. Origins intact.</h1>
          <p>{preparedCase.clinical_question}</p>
        </div>
        <div className="workspace-route">
          <span>{referral.sender.country}</span>
          <ArrowRight size={17} />
          <span>{referral.centre.country}</span>
          <small>{preparedCase.evidence.length} source envelopes</small>
          {preparedCase.version === 1 && (
            <button className="arrival-action" onClick={onDeliverImaging} disabled={busy}>
              <Radio size={16} />
              {busy ? 'Receiving imaging…' : 'Receive late imaging evidence'}
            </button>
          )}
        </div>
      </header>

      {caseUpdateError && (
        <section className="update-error" role="status">
          <CircleAlert size={20} />
          <div>
            <strong>Evidence update failed — case v{caseUpdateError.preserved_version} preserved</strong>
            <p>{caseUpdateError.message}</p>
            <small>Delivery {caseUpdateError.event_id}</small>
          </div>
        </section>
      )}

      {preparedCase.delta && previousCase && (
        <CaseChangeView
          preparedCase={preparedCase}
          previousCase={previousCase}
          onInspectSource={onInspectSource}
        />
      )}

      <div className="workspace-alerts">
        {preparedCase.conflicts.map((conflict) => (
          <article className="finding conflict" key={conflict.id}>
            <CircleAlert size={19} />
            <div>
              <strong>Unresolved source conflict</strong>
              <p>{conflict.description}</p>
              <small>{conflict.resolution}</small>
            </div>
          </article>
        ))}
        {preparedCase.missing.map((missing) => (
          <article className="finding missing" key={missing.id}>
            <CircleAlert size={19} />
            <div>
              <strong>Required evidence missing</strong>
              <p>{missing.description}</p>
              <button
                className="text-action"
                onClick={() => onInspectSource(missing.provenance[0].evidence_id)}
              >
                Inspect requirement source <ExternalLink size={14} />
              </button>
            </div>
          </article>
        ))}
      </div>

      {reviewState && (
        <HumanReviewPanel
          key={`${preparedCase.version}-${reviewState.opinion?.id ?? 'new'}-${reviewState.stale}`}
          preparedCase={preparedCase}
          reviewState={reviewState}
          handoffManifest={handoffManifest}
          busy={busy}
          onSaveReview={onSaveReview}
          onCreateHandoff={onCreateHandoff}
        />
      )}

      <div className="workspace-grid">
        <section className="claim-board" aria-label="Prepared evidence claims">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Source facts and transformations</p>
              <h2>Reviewable evidence</h2>
            </div>
            <span>{preparedCase.claims.length} claims</span>
          </div>
          {preparedCase.claims.map((claim) => (
            <article className="claim" key={claim.id}>
              <div className="claim-title">
                <span>{claim.category}</span>
                <strong>{claim.label}</strong>
              </div>
              <div className="value-pair">
                <div className="source-value">
                  <small>Source fact</small>
                  <p>{claim.raw_value}</p>
                </div>
                <ArrowRight size={16} aria-hidden="true" />
                <div className={claim.normalized_value ? 'normalized-value' : 'unmapped-value'}>
                  <small>{claim.normalized_value ? 'Normalized value' : 'Unmapped'}</small>
                  <p>{claim.normalized_value ?? 'No normalized value'}</p>
                </div>
              </div>
              <div className="claim-foot">
                <span>{claim.transformation}</span>
                <button
                  className="source-link"
                  onClick={() => onInspectSource(claim.provenance[0].evidence_id)}
                >
                  <Link2 size={14} />
                  {claim.provenance[0].source_institution} ·{' '}
                  {claim.provenance[0].source_format}
                </button>
              </div>
            </article>
          ))}
        </section>

        <aside className="synthesis-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Deterministic synthesis</p>
              <h2>Bounded case view</h2>
            </div>
          </div>
          <div className="boundary-note">
            <ShieldCheck size={18} />
            Uses only the evidence package below. No treatment recommendation or clinical
            conclusion.
          </div>
          <ol className="synthesis-list">
            {preparedCase.synthesis.map((statement) => (
              <li key={`${statement.text}-${statement.support_ids.join('-')}`}>
                <p>{statement.text}</p>
                <small>Supported by {statement.support_ids.join(', ')}</small>
              </li>
            ))}
          </ol>
          <div className="warning-stack">
            <strong>Transformation notes</strong>
            {preparedCase.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
            {preparedCase.unmapped_values.map((value) => (
              <p className="unmapped" key={value}>
                Unmapped: {value}
              </p>
            ))}
          </div>
          <button className="secondary-action" onClick={onReset} disabled={busy}>
            <RotateCcw size={17} />
            Reset rehearsal
          </button>
        </aside>
      </div>

      {inspectedSource && (
        <SourceInspector evidence={inspectedSource} onClose={onCloseSource} />
      )}
    </section>
  )
}

function HumanReviewPanel({
  preparedCase,
  reviewState,
  handoffManifest,
  busy,
  onSaveReview,
  onCreateHandoff,
}: {
  preparedCase: PreparedCase
  reviewState: HumanReviewState
  handoffManifest: HandoffManifest | null
  busy: boolean
  onSaveReview: (command: {
    case_version: number
    reviewer: string
    opinion: string
    conditions: {
      issue_id: string
      status: ReviewConditionStatus
      resolution: string
    }[]
    next_responsibility: {
      actor: string
      action: string
    }
  }) => void
  onCreateHandoff: () => void
}) {
  const currentOpinion =
    reviewState.opinion?.case_version === preparedCase.version ? reviewState.opinion : null
  const [reviewer, setReviewer] = useState(currentOpinion?.reviewer ?? 'Dr Eva van Dijk')
  const [opinion, setOpinion] = useState(currentOpinion?.opinion ?? '')
  const [nextActor, setNextActor] = useState(
    currentOpinion?.next_responsibility.actor ?? 'Utrecht colorectal MDO coordinator',
  )
  const [nextAction, setNextAction] = useState(
    currentOpinion?.next_responsibility.action ??
      'Schedule multidisciplinary review of the versioned synthetic case.',
  )
  const [conditions, setConditions] = useState<ReviewCondition[]>(
    currentOpinion?.conditions ?? reviewState.required_conditions,
  )

  function updateCondition(issueId: string, update: Partial<ReviewCondition>) {
    setConditions((items) =>
      items.map((item) => (item.issue_id === issueId ? { ...item, ...update } : item)),
    )
  }

  function submitReview() {
    onSaveReview({
      case_version: preparedCase.version,
      reviewer,
      opinion,
      conditions: conditions.map((condition) => ({
        issue_id: condition.issue_id,
        status: condition.status,
        resolution: condition.resolution,
      })),
      next_responsibility: {
        actor: nextActor,
        action: nextAction,
      },
    })
  }

  return (
    <section className="human-review" aria-label="Human review and MDO handoff">
      <div className="review-heading">
        <div>
          <p className="eyebrow">Human judgement · bound to case v{preparedCase.version}</p>
          <h2>Opinion, conditions, and next responsibility</h2>
        </div>
        <span className={reviewState.handoff_ready ? 'ready-state ready' : 'ready-state'}>
          {reviewState.handoff_ready ? 'Ready to create handoff' : 'Handoff gated'}
        </span>
      </div>

      {reviewState.stale && reviewState.opinion && (
        <div className="stale-review" role="status">
          <History size={19} />
          <div>
            <strong>Previous opinion is stale</strong>
            <p>
              Opinion {reviewState.opinion.id} covers case v{reviewState.opinion.case_version}.
              Case v{preparedCase.version} requires a new human review and cannot inherit approval.
            </p>
          </div>
        </div>
      )}

      <div className="review-layout">
        <div className="review-form">
          <label>
            Reviewing clinician
            <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
          </label>
          <label>
            Considered human opinion
            <textarea
              rows={4}
              value={opinion}
              onChange={(event) => setOpinion(event.target.value)}
              placeholder="Record the clinical opinion without presenting it as an automated conclusion."
            />
          </label>
          <div className="responsibility-fields">
            <label>
              Next responsible actor
              <input value={nextActor} onChange={(event) => setNextActor(event.target.value)} />
            </label>
            <label>
              Explicit next action
              <input value={nextAction} onChange={(event) => setNextAction(event.target.value)} />
            </label>
          </div>
          <button
            className="primary-action"
            onClick={submitReview}
            disabled={busy || !reviewer.trim() || !opinion.trim() || !nextActor.trim() || !nextAction.trim()}
          >
            <ClipboardCheck size={18} />
            {busy ? 'Saving review…' : `Save opinion for case v${preparedCase.version}`}
          </button>
        </div>

        <div className="review-conditions">
          <div className="conditions-heading">
            <strong>Required evidence and review conditions</strong>
            <small>Every item needs an explicit resolution before handoff.</small>
          </div>
          {conditions.map((condition) => (
            <article className="review-condition" key={condition.issue_id}>
              <label className="condition-toggle">
                <input
                  type="checkbox"
                  checked={condition.status === 'resolved'}
                  onChange={(event) =>
                    updateCondition(condition.issue_id, {
                      status: event.target.checked ? 'resolved' : 'open',
                    })
                  }
                />
                <span>
                  <strong>
                    {condition.kind === 'required_evidence'
                      ? 'Required evidence condition'
                      : 'Review condition'}
                  </strong>
                  <small>{condition.issue_id}</small>
                </span>
              </label>
              <p>{condition.description}</p>
              <label>
                Resolution note
                <input
                  value={condition.resolution}
                  onChange={(event) =>
                    updateCondition(condition.issue_id, { resolution: event.target.value })
                  }
                  placeholder="Required when marked resolved"
                />
              </label>
            </article>
          ))}
        </div>
      </div>

      <div className="handoff-zone">
        <div>
          <p className="eyebrow">Versioned narrative handoff</p>
          <h3>Continue into the autonomous MDO demonstration</h3>
          <p>
            Version one does not synchronize runtime state. The MDO uses a separate backend;
            this app creates a controlled deep link from a persisted continuity manifest.
          </p>
          {!reviewState.handoff_ready && (
            <ul>
              {reviewState.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          )}
        </div>
        <button
          className="handoff-action"
          onClick={onCreateHandoff}
          disabled={busy || !reviewState.handoff_ready}
        >
          <ExternalLink size={18} />
          Create MDO handoff manifest
        </button>
      </div>

      {handoffManifest && (
        <article className="handoff-manifest" aria-label="MDO handoff manifest">
          <div className="manifest-title">
            <div>
              <p className="eyebrow">Manifest v{handoffManifest.version}</p>
              <h3>{handoffManifest.id}</h3>
            </div>
            <span>{handoffManifest.synthetic_labels.join(' · ')}</span>
          </div>
          <dl>
            <div>
              <dt>Case ID</dt>
              <dd>{handoffManifest.case_id}</dd>
            </div>
            <div>
              <dt>Evidence version</dt>
              <dd>Case v{handoffManifest.evidence_version}</dd>
            </div>
            <div>
              <dt>Clinical question</dt>
              <dd>{handoffManifest.clinical_question}</dd>
            </div>
            <div>
              <dt>Next actor and action</dt>
              <dd>
                {handoffManifest.responsibility.actor}: {handoffManifest.responsibility.action}
              </dd>
            </div>
            <div>
              <dt>Unresolved issues carried forward</dt>
              <dd>
                {handoffManifest.unresolved_issues.length
                  ? handoffManifest.unresolved_issues.join(' · ')
                  : 'None'}
              </dd>
            </div>
          </dl>
          <p className="backend-notice">{handoffManifest.backend_notice}</p>
          <a
            className="primary-action"
            href={handoffManifest.launch_url}
            target="_blank"
            rel="noreferrer"
          >
            Launch separate MDO demonstration
            <ArrowRight size={18} />
          </a>
        </article>
      )}
    </section>
  )
}

function CaseChangeView({
  preparedCase,
  previousCase,
  onInspectSource,
}: {
  preparedCase: PreparedCase
  previousCase: PreparedCase
  onInspectSource: (evidenceId: string, version?: number) => void
}) {
  const delta = preparedCase.delta
  if (!delta) return null

  return (
    <section className="case-change" aria-label="Case version comparison">
      <div className="change-heading">
        <div>
          <p className="eyebrow">Automatic evidence refresh · no new AI prompt</p>
          <h2>What changed from case v{delta.from_version} to v{delta.to_version}</h2>
        </div>
        <span className="version-transition">
          <History size={16} />
          Immutable v{previousCase.version} retained
        </span>
      </div>

      <div className="before-after">
        <article>
          <span>Before · case v{previousCase.version}</span>
          <strong>Imaging evidence incomplete</strong>
          <p>
            {previousCase.evidence.length} source envelopes were prepared before the late
            imaging delivery.
          </p>
          <div className="version-sources">
            {previousCase.evidence.slice(0, 3).map((item) => (
              <button
                key={item.source_identifier}
                onClick={() => onInspectSource(item.source_identifier, previousCase.version)}
              >
                <Link2 size={13} />
                {item.source_format}
              </button>
            ))}
          </div>
        </article>
        <GitCompare size={22} aria-hidden="true" />
        <article className="after">
          <span>After · case v{preparedCase.version}</span>
          <strong>Baseline and restaging imaging linked</strong>
          <p>
            {preparedCase.evidence.length} source envelopes now support longitudinal review.
          </p>
          <div className="version-sources">
            {delta.added_evidence.map((item) => (
              <button
                key={item.evidence_id}
                onClick={() => onInspectSource(item.evidence_id, preparedCase.version)}
              >
                <Link2 size={13} />
                {item.label}
              </button>
            ))}
          </div>
        </article>
      </div>

      <div className="delta-grid">
        <article>
          <h3>Added evidence</h3>
          {delta.added_evidence.map((item) => (
            <button
              className="delta-source"
              key={item.evidence_id}
              onClick={() => onInspectSource(item.evidence_id, preparedCase.version)}
            >
              <strong>{item.label}</strong>
              <small>{item.source_institution} · {item.source_format}</small>
            </button>
          ))}
        </article>
        <article>
          <h3>Changed findings & conclusions</h3>
          {delta.changed_findings.map((item) => (
            <div className="delta-item" key={item.subject}>
              <strong>{item.subject}</strong>
              <p><b>Before:</b> {item.before}</p>
              <p><b>After:</b> {item.after}</p>
              {item.conclusion_requires_reassessment && (
                <small>Human conclusion requires reassessment</small>
              )}
            </div>
          ))}
        </article>
        <article>
          <h3>Remaining uncertainty</h3>
          <ul>
            {delta.remaining_uncertainty.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </article>
        <article>
          <h3>Affected human questions</h3>
          <ol>
            {delta.affected_human_questions.map((item) => <li key={item}>{item}</li>)}
          </ol>
        </article>
      </div>
    </section>
  )
}

function SourceInspector({
  evidence,
  onClose,
}: {
  evidence: EvidenceEnvelope
  onClose: () => void
}) {
  return (
    <aside className="source-inspector" aria-label="Source evidence inspector">
      <div className="source-inspector-head">
        <div>
          <p className="eyebrow">Original fixture inspection</p>
          <h2>{evidence.source_format}</h2>
        </div>
        <button onClick={onClose} aria-label="Close source inspector">
          ×
        </button>
      </div>
      <dl>
        <div>
          <dt>Institution</dt>
          <dd>{evidence.source_institution}</dd>
        </div>
        <div>
          <dt>Source ID</dt>
          <dd>{evidence.source_identifier}</dd>
        </div>
        <div>
          <dt>Observed</dt>
          <dd>{new Date(evidence.observed_at).toLocaleString()}</dd>
        </div>
        <div>
          <dt>Transformation</dt>
          <dd>{evidence.transformation_status}</dd>
        </div>
        <div>
          <dt>Fixture</dt>
          <dd>{evidence.retrieval_reference}</dd>
        </div>
      </dl>
      <div className="source-facts">
        {evidence.facts.map((fact) => (
          <article key={`${fact.key}-${fact.source_pointer}`}>
            <FileSearch size={16} />
            <div>
              <strong>{fact.label}</strong>
              <p>{fact.raw_value}</p>
              <small>{fact.source_pointer}</small>
            </div>
          </article>
        ))}
      </div>
      <div className="original-record">
        <div>
          <strong>Preserved original record</strong>
          <small>{evidence.original_media_type}</small>
        </div>
        <pre>{evidence.original_content}</pre>
      </div>
      <small className="hash">SHA-256 {evidence.content_hash}</small>
    </aside>
  )
}

export default App
