import type { ArmAggregate, CohortAggregate } from '../api/types'
import { pct } from '../evidence'

function Bar({ value, max, label }: { value: number | null; max: number; label: string }) {
  if (value == null) return <span className="muted">suppressed</span>
  return (
    <span className="bar-cell">
      <span className="bar" aria-hidden>
        <span style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
      </span>
      <span>{label}</span>
    </span>
  )
}

export function CohortTable({
  result,
  compact = false,
  cited = [],
  onCite,
}: {
  result: CohortAggregate
  compact?: boolean
  cited?: string[]
  onCite?: (arm: ArmAggregate) => void
}) {
  const name = result.name ?? result.site
  return (
    <div className="cohort">
      <p className="cohort-headline">
        <strong>{name}</strong>
        <span>
          <strong>{result.records_queried_locally}</strong> matching locally ·{' '}
          <strong>{result.records_transferred}</strong> records transferred
        </span>
      </p>
      {result.arms.length === 0 ? (
        <p className="muted small">No matching patients with recorded treatment outcomes for this query.</p>
      ) : (
        <table>
          <caption className="sr-only">Aggregate outcomes computed inside {name}</caption>
          <thead>
            <tr>
              <th scope="col">Treatment</th>
              <th scope="col">Patients</th>
              <th scope="col">Response</th>
              <th scope="col">Median PFS</th>
              {onCite && <th scope="col">Opinion</th>}
            </tr>
          </thead>
          <tbody>
            {result.arms.map((arm) => (
              <tr key={arm.arm} className={arm.suppressed ? 'suppressed' : ''}>
                <th scope="row">{compact ? `Option ${arm.arm}` : arm.label}</th>
                <td>{arm.n_display}</td>
                <td>
                  {compact ? pct(arm.response_rate) : <Bar value={arm.response_rate} max={1} label={pct(arm.response_rate)} />}
                </td>
                <td>
                  {compact ? (
                    arm.median_pfs_months != null ? `${arm.median_pfs_months} mo` : '—'
                  ) : (
                    <Bar
                      value={arm.median_pfs_months}
                      max={12}
                      label={arm.median_pfs_months != null ? `${arm.median_pfs_months} mo` : ''}
                    />
                  )}
                </td>
                {onCite && (
                  <td>
                    {arm.suppressed ? (
                      <span className="muted small">too few to cite</span>
                    ) : (
                      <button
                        type="button"
                        className="link"
                        aria-pressed={cited.includes(arm.arm)}
                        onClick={() => onCite(arm)}
                      >
                        {cited.includes(arm.arm) ? 'Cited ✓' : 'Cite'}
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!compact && (
        <p className="muted small">
          Computed inside {name} over {result.records_scanned} local records. Cells under {result.k_threshold} patients
          suppressed ({result.suppressed_cells}). Synthetic numbers — not clinical evidence.
        </p>
      )}
    </div>
  )
}
