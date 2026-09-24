import { useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Lock, Search, Send, UserRound } from 'lucide-react'
import { api } from '../api/client'
import type { Chart, Expert, FhirResource, PeerReview } from '../api/types'
import { formatTime, useLoad } from '../lib'
import { CohortTable } from './shared'

const TABS = ['overview', 'timeline', 'pathology', 'imaging', 'molecular', 'treatment', 'mdo'] as const
type Tab = (typeof TABS)[number]
const TAB_LABELS: Record<Tab, string> = {
  overview: 'Overview',
  timeline: 'Timeline',
  pathology: 'Pathology',
  imaging: 'Imaging',
  molecular: 'Molecular',
  treatment: 'Treatment',
  mdo: 'MDO',
}
const HIDDEN_FIELDS = new Set(['resourceType', 'id', 'meta', 'subject', 'effectiveDate', 'text', 'contained', 'presentedForm', 'dicomTags'])

function ResourceCard({ resource }: { resource: FhirResource }) {
  const fields = Object.entries(resource).filter(([key]) => !HIDDEN_FIELDS.has(key))
  return (
    <article className="resource">
      <header>
        <strong>{resource.meta.title}</strong>
        <span className="muted">
          {resource.resourceType} · {resource.effectiveDate}
        </span>
      </header>
      <dl>
        {fields.map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd>
          </div>
        ))}
      </dl>
    </article>
  )
}

function PeerReviewStatus({
  review,
  onResend,
  onShowControlRoom,
}: {
  review: PeerReview
  onResend: () => void
  onShowControlRoom: () => void
}) {
  if (review.status === 'delivery_failed') {
    return (
      <div className="alert danger" role="alert">
        <AlertTriangle aria-hidden size={18} />
        <div>
          <strong>{review.error}</strong>
          <p>
            The case package is still only in UMC Utrecht. Correlation <code>{review.correlation_id}</code>
          </p>
        </div>
        <button type="button" className="secondary" onClick={onResend}>
          Resend secure case
        </button>
      </div>
    )
  }
  if (review.status === 'opinion_received' && review.opinion) {
    const cohort = review.opinion.cohort?.results ?? []
    return (
      <section className="loop" aria-label="European peer review received">
        <h3>
          <CheckCircle2 aria-hidden size={18} /> European peer review received
        </h3>
        <div className="loop-grid">
          <div>
            <span className="eyebrow">My patient</span>
            <p>Maria Janssen · stays in UMC Utrecht</p>
            <p className="muted">Shared as {review.case_id}: {review.report.shared_resources} of {review.report.source_resources} resources</p>
          </div>
          <div>
            <span className="eyebrow">European expert opinion</span>
            <p className="opinion-text">{review.opinion.text}</p>
            <p className="muted">
              {review.opinion.author}, {review.opinion.institution}
            </p>
          </div>
          <div>
            <span className="eyebrow">European real-world evidence</span>
            {cohort.length ? (
              cohort.map((result) => <CohortTable key={result.site} result={result} compact />)
            ) : (
              <p className="muted">No cohort evidence attached.</p>
            )}
          </div>
        </div>
      </section>
    )
  }
  return (
    <div className="alert success" role="status">
      <CheckCircle2 aria-hidden size={18} />
      <div>
        <strong>Secure case delivered to {review.expert.clinician}, {review.expert.institution}</strong>
        <p>
          Awaiting peer review · sent {formatTime(review.created_at)} · {review.report.source_resources} →{' '}
          {review.report.shared_resources} resources · correlation <code>{review.correlation_id}</code>
        </p>
      </div>
      <button type="button" className="link" onClick={onShowControlRoom}>
        What crossed the boundary?
      </button>
    </div>
  )
}

function PeerReviewRequest({
  chart,
  onSearched,
  onSent,
}: {
  chart: Chart
  onSearched: () => void
  onSent: (review: PeerReview) => void
}) {
  const [query, setQuery] = useState('KRAS G12C colorectal cancer')
  const [experts, setExperts] = useState<Expert[] | null>(null)
  const [expert, setExpert] = useState<Expert | null>(null)
  const [selected, setSelected] = useState<string[]>(
    chart.sharing_categories.filter((item) => item.default).map((item) => item.id),
  )
  const [question, setQuestion] = useState(
    'Progression after FOLFOX and FOLFIRI with bevacizumab; KRAS G12C, MSS, ECOG 1. What later-line strategy would you recommend we discuss at our MDO?',
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const shareCount = useMemo(
    () => chart.resources.filter((item) => selected.includes(item.meta.category)).length,
    [chart.resources, selected],
  )

  const search = async (event: React.FormEvent) => {
    event.preventDefault()
    setExperts(await api.experts(query))
    onSearched()
  }

  const send = async () => {
    if (!expert) return
    setBusy(true)
    setError(null)
    try {
      const review = await api.nl.send({
        patient_id: chart.patient.id,
        expert_id: expert.id,
        categories: selected,
        question,
      })
      onSent(review)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel" aria-label="Peer review request">
      <h2>Request European peer review</h2>
      <ol className="steps">
        <li>
          <h3>1 · Find European expertise</h3>
          <p className="muted">The federated catalogue holds expert metadata only — no patient data.</p>
          <form className="search" onSubmit={search} role="search">
            <label htmlFor="expert-query" className="sr-only">
              Expertise search
            </label>
            <input id="expert-query" value={query} onChange={(event) => setQuery(event.target.value)} />
            <button type="submit" className="secondary">
              <Search aria-hidden size={16} /> Search catalogue
            </button>
          </form>
          {experts && (
            <ul className="experts" aria-label="Matching experts">
              {experts.map((item) => (
                <li key={item.id} className={expert?.id === item.id ? 'selected' : ''}>
                  <UserRound aria-hidden size={20} />
                  <div>
                    <strong>
                      {item.clinician} · {item.institution}
                    </strong>
                    <span className="muted">
                      {item.country} · {item.expertise}
                    </span>
                  </div>
                  {item.connected ? (
                    <button
                      type="button"
                      className={expert?.id === item.id ? 'primary' : 'secondary'}
                      aria-pressed={expert?.id === item.id}
                      onClick={() => setExpert(item)}
                    >
                      {expert?.id === item.id ? 'Selected' : `Select ${item.institution.split(' ').pop()}`}
                    </button>
                  ) : (
                    <span className="pill muted-pill">Not connected in this demo</span>
                  )}
                </li>
              ))}
              {experts.length === 0 && <li className="muted">No matching expertise.</li>}
            </ul>
          )}
        </li>
        <li className={expert ? '' : 'disabled'} aria-disabled={!expert}>
          <h3>2 · Governed sharing</h3>
          <fieldset disabled={!expert}>
            <legend className="muted">
              Choose what leaves UMC Utrecht. The package is built from an allowlist; identifiers never leave.
            </legend>
            <ul className="categories">
              {chart.sharing_categories.map((item) => (
                <li key={item.id}>
                  <label className={item.shareable ? '' : 'locked'}>
                    <input
                      type="checkbox"
                      checked={selected.includes(item.id)}
                      disabled={!item.shareable}
                      onChange={(event) =>
                        setSelected((value) =>
                          event.target.checked ? [...value, item.id] : value.filter((id) => id !== item.id),
                        )
                      }
                    />
                    {item.label}
                    {!item.shareable && (
                      <span className="pill muted-pill">
                        <Lock aria-hidden size={12} /> Never shared
                      </span>
                    )}
                  </label>
                </li>
              ))}
            </ul>
            <label className="question" htmlFor="peer-question">
              Clinical question
            </label>
            <textarea id="peer-question" rows={3} value={question} onChange={(event) => setQuestion(event.target.value)} />
            <p className="share-summary">
              <strong>{shareCount}</strong> of {chart.resource_count} resources will leave UMC Utrecht, as a new
              pseudonymised case package for {expert ? expert.clinician : 'the selected expert'}.
            </p>
            {error && (
              <p className="alert danger" role="alert">
                {error}
              </p>
            )}
            <button type="button" className="primary" onClick={send} disabled={!expert || busy || selected.length === 0}>
              <Send aria-hidden size={16} /> {busy ? 'Sending…' : 'Send secure case'}
            </button>
          </fieldset>
        </li>
      </ol>
    </section>
  )
}

export function NlWorkspace({
  onOpenedChart,
  onSearched,
  onChanged,
  onShowControlRoom,
}: {
  onOpenedChart: () => void
  onSearched: () => void
  onChanged: () => void
  onShowControlRoom: () => void
}) {
  const patients = useLoad(api.nl.patients)
  const [patientId, setPatientId] = useState<string | null>(null)
  const chart = useLoad(() => (patientId ? api.nl.chart(patientId) : Promise.resolve(null)), 6000, [patientId])
  const [tab, setTab] = useState<Tab>('overview')
  const [requesting, setRequesting] = useState(false)

  const open = (id: string) => {
    setPatientId(id)
    setTab('overview')
    setRequesting(false)
    onOpenedChart()
  }

  const resend = async (caseId: string) => {
    await api.nl.resend(caseId).catch(() => undefined)
    await chart.refresh()
    onChanged()
  }

  const data = chart.data
  const resources = data
    ? tab === 'timeline'
      ? [...data.resources].sort((a, b) => (a.effectiveDate ?? '').localeCompare(b.effectiveDate ?? ''))
      : data.resources.filter((item) => item.meta.tab === tab && item.resourceType !== 'Patient')
    : []

  return (
    <div className="split">
      <aside className="sidebar" aria-label="Worklist">
        <h2>My worklist</h2>
        {patients.error && <p className="alert danger">{patients.error}</p>}
        <ul className="worklist">
          {patients.data?.map((patient) => (
            <li key={patient.id}>
              <button
                type="button"
                disabled={patient.restricted}
                aria-current={patient.id === patientId}
                onClick={() => open(patient.id)}
              >
                <strong>{patient.name}</strong>
                <span>
                  {patient.age}
                  {patient.sex} · {patient.mrn}
                </span>
                <span className="muted">{patient.summary}</span>
                <span className={patient.restricted ? 'pill muted-pill' : 'pill warn'}>
                  {patient.restricted ? 'Not part of this demo' : patient.flag}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <section className="content">
        {!data && <p className="empty">Select a patient from the worklist to open the chart.</p>}
        {data && (
          <>
            <header className="patient-header">
              <div>
                <h1>
                  {data.patient.name[0].given.join(' ')} {data.patient.name[0].family}
                </h1>
                <p>
                  57 y · {data.patient.gender} · born {data.patient.birthDate} · MRN {data.patient.identifier[0].value}
                </p>
                <p className="muted">
                  <Lock aria-hidden size={12} /> Identifiable record — held only in UMC Utrecht ({data.resource_count} resources)
                </p>
              </div>
              <button type="button" className="primary" onClick={() => setRequesting(true)}>
                Request European peer review
              </button>
            </header>
            {data.peer_reviews.map((review) => (
              <PeerReviewStatus
                key={review.case_id}
                review={review}
                onResend={() => void resend(review.case_id)}
                onShowControlRoom={onShowControlRoom}
              />
            ))}
            {requesting ? (
              <PeerReviewRequest
                chart={data}
                onSearched={onSearched}
                onSent={() => {
                  setRequesting(false)
                  void chart.refresh()
                  onChanged()
                }}
              />
            ) : (
              <>
                <div className="tabs" role="tablist" aria-label="Chart sections">
                  {TABS.map((item) => (
                    <button
                      key={item}
                      type="button"
                      role="tab"
                      aria-selected={tab === item}
                      className={tab === item ? 'tab active' : 'tab'}
                      onClick={() => setTab(item)}
                    >
                      {TAB_LABELS[item]}
                    </button>
                  ))}
                </div>
                <div className="resources" role="tabpanel" aria-label={TAB_LABELS[tab]}>
                  {resources.map((resource) => (
                    <ResourceCard key={resource.id} resource={resource} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </section>
    </div>
  )
}
