import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Database, Send } from 'lucide-react'
import { api } from '../api/client'
import type { BundleEntry, CohortQuery, InboxCase } from '../api/types'
import { formatTime } from '../lib'
import { composeOpinion, evidenceLine } from '../evidence'
import { CohortTable } from './shared'

type Criteria = Required<Pick<CohortQuery, 'kras_variant' | 'min_prior_lines'>>

const SKIP = new Set(['resourceType', 'id', 'category', 'title', 'subject', 'monthsSinceDiagnosis'])

const OTHER_RECOMMENDATIONS = [
  'Refer for clinical trial enrolment',
  'Continue current local plan',
  'Best supportive care',
]

const MDO_ASKS = [
  'Which later-line strategy would you recommend?',
  'What does experience with comparable patients show?',
  'What should the treating team check before deciding?',
]

function Entry({ entry }: { entry: BundleEntry }) {
  return (
    <article className="resource">
      <header>
        <strong>{entry.title}</strong>
        <span className="muted">
          {entry.resourceType} · month {entry.monthsSinceDiagnosis} since diagnosis
        </span>
      </header>
      <dl>
        {Object.entries(entry)
          .filter(([key]) => !SKIP.has(key))
          .map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd>
            </div>
          ))}
      </dl>
    </article>
  )
}

export function CaseView({ item, onChanged }: { item: InboxCase; onChanged: (value: InboxCase) => void }) {
  const [busy, setBusy] = useState<'compare' | 'opinion' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [criteria, setCriteria] = useState<Criteria>({ kras_variant: 'G12C', min_prior_lines: 2 })
  const [cited, setCited] = useState<string[]>([])
  const [recommendation, setRecommendation] = useState('')
  const [rationale, setRationale] = useState(
    'KRAS G12C, MSS, ECOG 1; progression after oxaliplatin- and irinotecan-based lines with bevacizumab. A targeted KRAS G12C combination is a reasonable later-line option to discuss.',
  )
  const [caveats, setCaveats] = useState(
    'Local availability and reimbursement of the KRAS G12C combination; open trials at UMC Utrecht; patient preference and organ function.',
  )
  const [includeCohort, setIncludeCohort] = useState(true)

  const results = item.cohort?.results ?? []
  const arms = results.flatMap((result) => result.arms.map((arm) => ({ arm, site: result.name ?? result.site })))
  const recommendationOptions = [
    ...arms.filter(({ arm }) => arm.arm !== 'C').map(({ arm }) => arm.label.replace(/^Option [A-Z] · /, '')),
    ...OTHER_RECOMMENDATIONS,
  ]
  const chosen = recommendation || recommendationOptions[0] || OTHER_RECOMMENDATIONS[0]
  const evidence = arms.filter(({ arm }) => cited.includes(arm.arm)).map(({ arm, site }) => evidenceLine(arm, site))
  const opinion = composeOpinion({ recommendation: chosen, rationale, evidence, caveats })

  const compare = async () => {
    setBusy('compare')
    setError(null)
    try {
      onChanged(await api.de.compare(item.case_id, criteria))
      setCited([])
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(null)
    }
  }

  const send = async () => {
    setBusy('opinion')
    setError(null)
    try {
      onChanged(await api.de.opinion(item.case_id, opinion, includeCohort && !!item.cohort))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(null)
    }
  }

  const byCategory = item.bundle.entry.reduce<Record<string, BundleEntry[]>>((groups, entry) => {
    ;(groups[entry.category] ??= []).push(entry)
    return groups
  }, {})

  return (
    <>
      <header className="patient-header">
        <div>
          <span className="eyebrow">Peer review request · from {item.from_site}</span>
          <h1>Case {item.case_id}</h1>
          <p>
            {item.bundle.subject.sex} · age {item.bundle.subject.ageBand} · requested by {item.requested_by} · received{' '}
            {formatTime(item.received_at)}
          </p>
          <p className="muted">
            Approved case package: {item.report.shared_resources} resources · identifiers removed at source · correlation{' '}
            <code>{item.correlation_id}</code>
          </p>
        </div>
      </header>
      <section className="panel mdo-ask" aria-label="What the MDO asks">
        <h2>The question from the UMC Utrecht MDO</h2>
        <blockquote className="question-quote">{item.question}</blockquote>
        <p className="muted small">Your opinion should answer:</p>
        <ol>
          {MDO_ASKS.map((ask) => (
            <li key={ask}>{ask}</li>
          ))}
        </ol>
      </section>
      {error && (
        <p className="alert danger" role="alert">
          <AlertTriangle aria-hidden size={16} /> {error}
        </p>
      )}
      <div className="case-grid">
        <section aria-label="Approved case package">
          <h2>Approved case package</h2>
          {Object.entries(byCategory).map(([category, entries]) => (
            <div key={category} className="category-group">
              <h3>{category.replaceAll('_', ' ')}</h3>
              {entries.map((entry) => (
                <Entry key={entry.id} entry={entry} />
              ))}
            </div>
          ))}
        </section>
        <section aria-label="Local evidence and opinion">
          <h2>1 · Evidence from our own patients</h2>
          <p className="muted small">
            Define &ldquo;comparable&rdquo;. The query runs inside Heidelberg&apos;s cohort engine; only aggregate outcomes per
            treatment come back.
          </p>
          <div className="criteria">
            <label>
              KRAS variant
              <select
                value={criteria.kras_variant}
                onChange={(event) => setCriteria({ ...criteria, kras_variant: event.target.value as Criteria['kras_variant'] })}
              >
                <option value="G12C">G12C (as this case)</option>
                <option value="G12D">G12D</option>
                <option value="G12V">G12V</option>
                <option value="any">Any KRAS</option>
              </select>
            </label>
            <label>
              Prior lines at least
              <select
                value={criteria.min_prior_lines}
                onChange={(event) => setCriteria({ ...criteria, min_prior_lines: Number(event.target.value) })}
              >
                {[0, 1, 2, 3].map((value) => (
                  <option key={value} value={value}>
                    {value}
                    {value === 2 ? ' (as this case)' : ''}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="secondary" onClick={() => void compare()} disabled={busy !== null}>
              <Database aria-hidden size={16} /> {busy === 'compare' ? 'Querying locally…' : 'Compare with our patients'}
            </button>
          </div>
          {results.map((result) => (
            <CohortTable
              key={result.site}
              result={result}
              cited={cited}
              onCite={(arm) =>
                setCited((list) => (list.includes(arm.arm) ? list.filter((a) => a !== arm.arm) : [...list, arm.arm]))
              }
            />
          ))}
          {item.cohort && (
            <p className="muted small">
              Cite the outcomes that support your opinion. Correlation <code>{item.cohort.correlation_id}</code>
            </p>
          )}

          <h2>2 · Your opinion</h2>
          {item.status === 'completed' && item.opinion ? (
            <div className="alert success" role="status">
              <CheckCircle2 aria-hidden size={18} />
              <div>
                <strong>Opinion sent to UMC Utrecht · {formatTime(item.opinion.sent_at)}</strong>
                <p className="opinion-text">{item.opinion.text}</p>
              </div>
            </div>
          ) : (
            <div className="opinion-form">
              <label>
                Recommendation
                <select value={chosen} onChange={(event) => setRecommendation(event.target.value)}>
                  {recommendationOptions.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label>
                Rationale
                <textarea rows={3} value={rationale} onChange={(event) => setRationale(event.target.value)} />
              </label>
              <div>
                <span className="field-label">Evidence cited</span>
                {evidence.length ? (
                  <ul className="cited">
                    {evidence.map((line) => (
                      <li key={line}>{line.slice(2)}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted small">
                    {item.cohort ? 'Click “Cite” next to a treatment above.' : 'Run the comparison first to cite outcomes.'}
                  </p>
                )}
              </div>
              <label>
                What should the treating team check?
                <textarea rows={2} value={caveats} onChange={(event) => setCaveats(event.target.value)} />
              </label>
              <label className="inline">
                <input
                  type="checkbox"
                  checked={includeCohort && !!item.cohort}
                  disabled={!item.cohort}
                  onChange={(event) => setIncludeCohort(event.target.checked)}
                />
                Attach the aggregate table to the opinion
              </label>
              <details>
                <summary>Preview what UMC Utrecht receives</summary>
                <pre className="json opinion-text" tabIndex={0}>{opinion}</pre>
              </details>
              <button type="button" className="primary" onClick={() => void send()} disabled={busy !== null}>
                <Send aria-hidden size={16} /> {busy === 'opinion' ? 'Sending…' : 'Send opinion to UMC Utrecht'}
              </button>
            </div>
          )}
        </section>
      </div>
    </>
  )
}
