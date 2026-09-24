import { useMemo, useState } from 'react'
import { Activity, CheckCircle2, CircleOff, FileSearch, Plug, RotateCcw, Server, Unplug } from 'lucide-react'
import { api } from '../api/client'
import type { AuditEvent, PackageAsSent, SitesResponse } from '../api/types'
import { formatTime, SERVICE_NAMES, STEP_LABELS, useLoad } from '../lib'

const OPERATIONS: Record<string, string> = {
  peer_review: 'Care sharing · peer review',
  peer_review_opinion: 'Care sharing · opinion returned',
  cohort_query: 'Federated analytics · cohort query',
  connectivity: 'Operations · site connectivity',
  reset: 'Reset',
}

function SiteCards({
  sites,
  error,
  busy,
  onToggle,
}: {
  sites: SitesResponse | null
  error: string | null
  busy: string | null
  onToggle: (site: 'nl' | 'de', online: boolean) => void
}) {
  return (
    <section aria-label="Site health" className="site-cards">
      {error && <p className="alert danger">{error}</p>}
      {sites?.sites.map((site) => (
        <article key={site.site} className={`site-card ${site.reachable ? 'up' : 'down'}`}>
          <header>
            {site.reachable ? <Server aria-hidden size={18} /> : <CircleOff aria-hidden size={18} />}
            <strong>{site.name}</strong>
            <span className={`pill ${site.reachable ? 'ok' : 'danger'}`}>{site.reachable ? 'Online' : 'Unavailable'}</span>
          </header>
          <p className="muted small">{site.role} · separate service</p>
          <dl>
            <div>
              <dt>Latency</dt>
              <dd>{site.reachable ? `${site.latency_ms} ms` : '—'}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{site.version ?? '—'}</dd>
            </div>
            <div>
              <dt>Generation</dt>
              <dd>{site.generation ?? '—'}</dd>
            </div>
            <div>
              <dt>State</dt>
              <dd>{!site.reachable ? site.error ?? 'no answer' : site.warm === false ? 'cold start' : 'warm'}</dd>
            </div>
          </dl>
          {site.site !== 'hub' && (
            <button
              type="button"
              className={site.isolated || !site.reachable ? 'primary' : 'secondary danger-outline'}
              disabled={busy !== null}
              onClick={() => onToggle(site.site as 'nl' | 'de', (!!site.isolated || !site.reachable))}
            >
              {site.isolated || !site.reachable ? <Plug aria-hidden size={16} /> : <Unplug aria-hidden size={16} />}{' '}
              {busy === site.site ? 'Switching…' : site.isolated || !site.reachable ? `Bring ${site.name} online` : `Take ${site.name} offline`}
            </button>
          )}
        </article>
      ))}
      {sites && sites.pending_reset.length > 0 && (
        <p className="alert warn">Reset pending at: {sites.pending_reset.map((s) => SERVICE_NAMES[s] ?? s).join(', ')}</p>
      )}
      {sites && (
        <p className="muted small catalogue-note">
          Catalogue only (not connected in this demo): {sites.catalogue_only.map((item) => item.name).join(' · ')}
        </p>
      )}
    </section>
  )
}

function EventDetail({ event }: { event: AuditEvent }) {
  const [pkg, setPkg] = useState<PackageAsSent | null>(null)
  const [error, setError] = useState<string | null>(null)
  const canRetrieve = event.operation === 'peer_review' && event.snapshot != null && event.step === 'VERIFIED'
  const caseId = typeof event.detail === 'string' ? /case (case-[0-9a-f]+)/.exec(event.detail)?.[1] : undefined
  return (
    <section className="event-detail" aria-label="Event detail">
      <h3>
        {STEP_LABELS[event.step] ?? event.step} · {SERVICE_NAMES[event.service]}
      </h3>
      <dl className="kv">
        <div>
          <dt>Time</dt>
          <dd>{event.timestamp}</dd>
        </div>
        <div>
          <dt>Source → destination</dt>
          <dd>
            {SERVICE_NAMES[event.source] ?? event.source} → {SERVICE_NAMES[event.destination] ?? event.destination}
          </dd>
        </div>
        <div>
          <dt>Correlation ID</dt>
          <dd>
            <code>{event.correlation_id}</code>
          </dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{event.status}</dd>
        </div>
        {event.body_sha256 && (
          <div>
            <dt>Body SHA-256</dt>
            <dd>
              <code>{event.body_sha256.slice(0, 24)}…</code>
            </dd>
          </div>
        )}
      </dl>
      <p>{event.detail}</p>
      {event.policy && (
        <ul className="reasons">
          {event.policy.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      {Object.keys(event.manifest).length > 0 && (
        <p className="muted small">
          Manifest: {Object.entries(event.manifest).map(([type, count]) => `${type} × ${count}`).join(', ')}
        </p>
      )}
      {event.snapshot != null ? (
        <>
          <h4>What crossed the boundary (redacted snapshot)</h4>
          <pre className="json" tabIndex={0}>{JSON.stringify(event.snapshot, null, 2)}</pre>
        </>
      ) : null}
      {canRetrieve && caseId && (
        <>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              api
                .packageAsSent(caseId)
                .then(setPkg)
                .catch((caught: Error) => setError(caught.message))
            }
          >
            <FileSearch aria-hidden size={16} /> Retrieve full package from UMC Utrecht
          </button>
          {error && <p className="alert danger">{error}</p>}
          {pkg && (
            <>
              <p className={pkg.matches_audit ? 'alert success' : 'alert danger'}>
                <CheckCircle2 aria-hidden size={16} /> Retrieved from {pkg.retrieved_from} · SHA-256{' '}
                {pkg.matches_audit ? 'matches the hub audit event' : 'does NOT match the audit event'}
              </p>
              <pre className="json" tabIndex={0}>{JSON.stringify(pkg.bundle, null, 2)}</pre>
            </>
          )}
        </>
      )}
    </section>
  )
}

export function ControlRoom({
  sites,
  sitesError,
  onChanged,
}: {
  sites: SitesResponse | null
  sitesError: string | null
  onChanged: () => void
}) {
  const activity = useLoad(api.activity, 3000)
  const [selected, setSelected] = useState<AuditEvent | null>(null)
  const [resetting, setResetting] = useState(false)
  const [switching, setSwitching] = useState<string | null>(null)
  const [switchError, setSwitchError] = useState<string | null>(null)

  const toggle = async (site: 'nl' | 'de', online: boolean) => {
    setSwitching(site)
    setSwitchError(null)
    try {
      await api.connectivity(site, online)
    } catch (caught) {
      setSwitchError(caught instanceof Error ? caught.message : String(caught))
    }
    onChanged()
    await activity.refresh()
    setSwitching(null)
  }

  const groups = useMemo(() => {
    const byCorrelation = new Map<string, AuditEvent[]>()
    for (const event of activity.data?.events ?? []) {
      if (event.operation === 'reset') continue
      const list = byCorrelation.get(event.correlation_id) ?? []
      list.push(event)
      byCorrelation.set(event.correlation_id, list)
    }
    return [...byCorrelation.entries()].sort((a, b) => b[1][0].timestamp.localeCompare(a[1][0].timestamp))
  }, [activity.data])

  const reset = async () => {
    if (!window.confirm('Reset the demo across UMC Utrecht, Heidelberg and the hub?')) return
    setResetting(true)
    await api.reset().catch(() => undefined)
    setSelected(null)
    await activity.refresh()
    onChanged()
    setResetting(false)
  }

  return (
    <div className="control">
      <div className="control-head">
        <h1>
          <Activity aria-hidden size={20} /> Federation control room
        </h1>
        <button type="button" className="secondary" onClick={() => void reset()} disabled={resetting}>
          <RotateCcw aria-hidden size={16} /> {resetting ? 'Resetting…' : 'Reset demo'}
        </button>
      </div>
      <SiteCards sites={sites} error={switchError ?? sitesError} busy={switching} onToggle={(site, online) => void toggle(site, online)} />
      <p className="muted small runbook">
        <strong>Disconnect test:</strong> “Take … offline” isolates that hospital service at its network edge — it
        refuses all traffic from the hub and its own workstation, exactly like an outage. Then send, compare or run
        research: the failure you see is real. Bring it back online and use “Resend secure case”.
      </p>
      {activity.data && activity.data.unavailable.length > 0 && (
        <p className="alert warn" role="status">
          Audit from {activity.data.unavailable.map((s) => SERVICE_NAMES[s] ?? s).join(', ')} unavailable — showing what the
          other services recorded.
        </p>
      )}
      <div className="monitor">
        <section aria-label="Activity monitor" className="timeline">
          <h2>Activity monitor</h2>
          {groups.length === 0 && <p className="empty small">No federated activity yet in this generation.</p>}
          {groups.map(([correlationId, events]) => (
            <article key={correlationId} className="flow">
              <header>
                <strong>{OPERATIONS[events[0].operation] ?? events[0].operation}</strong>
                <code>{correlationId}</code>
              </header>
              <ol>
                {events.map((event) => (
                  <li key={event.event_id} className={`evt evt-${event.status}`}>
                    <button
                      type="button"
                      aria-pressed={selected?.event_id === event.event_id}
                      onClick={() => setSelected(event)}
                    >
                      <time>{formatTime(event.timestamp)}</time>
                      <span className={`svc svc-${event.service}`}>{SERVICE_NAMES[event.service]}</span>
                      <strong>{STEP_LABELS[event.step] ?? event.step}</strong>
                      <span className="muted">
                        {SERVICE_NAMES[event.source] ?? event.source} → {SERVICE_NAMES[event.destination] ?? event.destination}
                      </span>
                      <span className="detail">{event.detail}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </section>
        <aside className="inspector" aria-label="Inspector">
          {selected ? <EventDetail key={selected.event_id} event={selected} /> : <p className="empty small">Select an event to inspect it.</p>}
        </aside>
      </div>
    </div>
  )
}
