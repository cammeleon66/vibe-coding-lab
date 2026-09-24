import { useState } from 'react'
import { AlertTriangle, ArrowRight, CircleOff, FlaskConical, History, Network, Server, ShieldCheck } from 'lucide-react'
import { api } from '../api/client'
import type { CohortQuery, FanOutResult, SitesResponse } from '../api/types'
import { formatTime } from '../lib'
import { pool, pct } from '../evidence'
import { CohortTable } from './shared'

type Criteria = Required<Pick<CohortQuery, 'kras_variant' | 'min_prior_lines'>>

const PRESETS: { label: string; query: Criteria }[] = [
  { label: "Like Maria's case", query: { kras_variant: 'G12C', min_prior_lines: 2 } },
  { label: 'All KRAS G12C mCRC', query: { kras_variant: 'G12C', min_prior_lines: 0 } },
  { label: 'Any KRAS, later line', query: { kras_variant: 'any', min_prior_lines: 2 } },
]

const LOOP = [
  ['One patient', "Maria's record never leaves UMC Utrecht"],
  ["Europe's expertise", 'A minimised case reaches the right expert'],
  ['Local evidence', 'Heidelberg computes; only aggregates travel'],
  ['New question', 'The case becomes a federated research query'],
]

interface Run {
  at: string
  query: Criteria
  result: FanOutResult
}

function NetworkMap({ sites }: { sites: SitesResponse | null }) {
  const connected = sites?.sites.filter((site) => site.site !== 'hub') ?? []
  return (
    <section className="panel network-map" aria-label="Research network">
      <h2>
        <Network aria-hidden size={16} /> Research network
      </h2>
      <ul>
        {connected.map((site) => (
          <li key={site.site} className={site.reachable ? 'node up' : 'node down'}>
            {site.reachable ? <Server aria-hidden size={16} /> : <CircleOff aria-hidden size={16} />}
            <strong>{site.name}</strong>
            <span className="small">{site.reachable ? 'Connected · cohort engine online' : 'Unavailable'}</span>
          </li>
        ))}
        {sites?.catalogue_only.map((site) => (
          <li key={site.site} className="node catalogue">
            <CircleOff aria-hidden size={16} />
            <strong>{site.name}</strong>
            <span className="small">Catalogue only · not connected in this demo</span>
          </li>
        ))}
      </ul>
      <p className="muted small">The hub holds no patient data. It routes the typed query and applies policy.</p>
    </section>
  )
}

export function ResearchView({ sites, onChanged }: { sites: SitesResponse | null; onChanged: () => void }) {
  const [query, setQuery] = useState<Criteria>(PRESETS[0].query)
  const [runs, setRuns] = useState<Run[]>([])
  const [shown, setShown] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async (event?: React.FormEvent) => {
    event?.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const result = await api.research(query)
      setRuns((list) => [{ at: new Date().toISOString(), query, result }, ...list].slice(0, 8))
      setShown(0)
      onChanged()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(false)
    }
  }

  const current = runs[shown]
  const result = current?.result
  const total = result?.results.reduce((sum, item) => sum + item.records_queried_locally, 0) ?? 0
  const scanned = result?.results.reduce((sum, item) => sum + item.records_scanned, 0) ?? 0

  return (
    <div className="research">
      <h1>
        <FlaskConical aria-hidden size={20} /> Turn this case into a research question
      </h1>
      <p className="muted">
        The question travels to each connected hospital; each computes locally; only aggregates return. There is no
        central database.
      </p>
      <div className="research-top">
        <form className="panel research-form" onSubmit={run} aria-label="Federated query">
          <h2>Question</h2>
          <div className="presets" role="group" aria-label="Presets">
            {PRESETS.map((preset) => (
              <button
                key={preset.label}
                type="button"
                className="chip"
                aria-pressed={
                  preset.query.kras_variant === query.kras_variant && preset.query.min_prior_lines === query.min_prior_lines
                }
                onClick={() => setQuery(preset.query)}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <div className="criteria">
            <div>
              <span className="field-label">Diagnosis</span>
              <span>Metastatic colorectal cancer</span>
            </div>
            <label>
              KRAS variant
              <select
                value={query.kras_variant}
                onChange={(event) => setQuery({ ...query, kras_variant: event.target.value as Criteria['kras_variant'] })}
              >
                <option value="G12C">G12C</option>
                <option value="G12D">G12D</option>
                <option value="G12V">G12V</option>
                <option value="any">Any</option>
              </select>
            </label>
            <label>
              Minimum prior lines
              <select
                value={query.min_prior_lines}
                onChange={(event) => setQuery({ ...query, min_prior_lines: Number(event.target.value) })}
              >
                {[0, 1, 2, 3].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="muted small">Outcomes: best response rate and median progression-free survival per treatment.</p>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? 'Querying sites…' : 'Run federated query'}
          </button>
        </form>
        <NetworkMap sites={sites} />
      </div>
      {error && (
        <p className="alert danger" role="alert">
          {error}
        </p>
      )}
      {!result && (
        <p className="empty panel">
          Pick a question and run it. Each hospital answers from its own data; you will see pooled outcomes, per-site
          results and exactly what travelled.
        </p>
      )}
      {result && (
        <section aria-label="Federated result" className="panel">
          {!result.complete && (
            <p className="alert danger" role="alert">
              <AlertTriangle aria-hidden size={16} /> {result.unavailable.map((item) => item.detail).join('; ')}
            </p>
          )}
          <div className="stats">
            <div>
              <strong>{total}</strong>
              <span>matching patients</span>
            </div>
            <div>
              <strong>{result.results.length}</strong>
              <span>sites answered</span>
            </div>
            <div>
              <strong>{scanned}</strong>
              <span>records scanned locally</span>
            </div>
            <div className="zero">
              <strong>{result.records_transferred}</strong>
              <span>records transferred</span>
            </div>
          </div>
          <h2>Pooled outcomes across the network</h2>
          {pool(result).length === 0 ? (
            <p className="muted">No matching treated patients with outcomes for this question.</p>
          ) : (
            <table className="pooled">
              <caption className="sr-only">Pooled outcomes per treatment</caption>
              <thead>
                <tr>
                  <th scope="col">Treatment</th>
                  <th scope="col">Patients</th>
                  <th scope="col">Pooled response</th>
                  <th scope="col">Median PFS by site</th>
                </tr>
              </thead>
              <tbody>
                {pool(result).map((row) => (
                  <tr key={row.label}>
                    <th scope="row">{row.label}</th>
                    <td>
                      {row.n}
                      {row.excluded.length > 0 && (
                        <span className="muted small"> (+ suppressed at {row.excluded.join(', ')})</span>
                      )}
                    </td>
                    <td>{row.n ? pct(row.responders / row.n) : 'suppressed'}</td>
                    <td>{row.pfs.length ? row.pfs.map((value) => `${value} mo`).join(' · ') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <h2>Per site</h2>
          <div className="research-grid">
            {result.results.map((item) => (
              <CohortTable key={item.site} result={item} />
            ))}
          </div>
          <ul className="not-connected">
            {result.not_connected.map((item) => (
              <li key={item.site}>
                {item.name}: <span className="muted">not connected in this demo — excluded from totals</span>
              </li>
            ))}
          </ul>
          <details className="travelled">
            <summary>
              <ShieldCheck aria-hidden size={16} /> What travelled
            </summary>
            <div className="travelled-grid">
              <div>
                <span className="field-label">Out: typed query (no free SQL)</span>
                <pre className="json" tabIndex={0}>{JSON.stringify(result.query ?? current.query, null, 2)}</pre>
              </div>
              <div>
                <span className="field-label">Back: aggregates only</span>
                <pre className="json" tabIndex={0}>
                  {JSON.stringify(
                    result.results.map((item) => ({
                      site: item.site,
                      query_digest: item.query_digest,
                      records_transferred: item.records_transferred,
                      k_threshold: item.k_threshold,
                      arms: item.arms.map((arm) => ({ arm: arm.arm, n: arm.n_display })),
                    })),
                    null,
                    2,
                  )}
                </pre>
              </div>
            </div>
            <p className="muted small">
              Correlation <code>{result.correlation_id}</code> — follow it in the Control room.
            </p>
          </details>
        </section>
      )}
      {runs.length > 1 && (
        <section className="panel" aria-label="Query history">
          <h2>
            <History aria-hidden size={16} /> Query history
          </h2>
          <ul className="history">
            {runs.map((item, index) => (
              <li key={item.result.correlation_id}>
                <button type="button" className="link" aria-current={index === shown} onClick={() => setShown(index)}>
                  {formatTime(item.at)} · KRAS {item.query.kras_variant} · ≥{item.query.min_prior_lines} lines ·{' '}
                  {item.result.results.reduce((sum, r) => sum + r.records_queried_locally, 0)} patients
                  {item.result.complete ? '' : ' · incomplete'}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="closing" aria-label="Closing loop">
        <ol>
          {LOOP.map(([title, text], index) => (
            <li key={title}>
              <strong>{title}</strong>
              <span>{text}</span>
              {index < LOOP.length - 1 && <ArrowRight aria-hidden size={18} className="arrow" />}
            </li>
          ))}
        </ol>
        <p className="tagline">Data stays. Insights travel.</p>
      </section>
    </div>
  )
}
