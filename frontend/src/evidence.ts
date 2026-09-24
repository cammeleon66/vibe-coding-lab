import type { ArmAggregate, FanOutResult } from './api/types'

export const pct = (value: number | null) => (value == null ? '—' : `${Math.round(value * 100)}%`)

export interface Pooled {
  label: string
  n: number
  responders: number
  sites: number
  excluded: string[]
  pfs: number[]
}

export function pool(result: FanOutResult): Pooled[] {
  const byArm = new Map<string, Pooled>()
  for (const site of result.results) {
    for (const arm of site.arms) {
      const entry = byArm.get(arm.arm) ?? { label: arm.label, n: 0, responders: 0, sites: 0, excluded: [], pfs: [] }
      if (arm.suppressed || arm.n == null) {
        entry.excluded.push(site.name ?? site.site)
      } else {
        entry.n += arm.n
        entry.responders += Math.round((arm.response_rate ?? 0) * arm.n)
        entry.sites += 1
        if (arm.median_pfs_months != null) entry.pfs.push(arm.median_pfs_months)
      }
      byArm.set(arm.arm, entry)
    }
  }
  return [...byArm.values()]
}

export function evidenceLine(arm: ArmAggregate, site: string) {
  const pfs = arm.median_pfs_months != null ? `, median PFS ${arm.median_pfs_months} months` : ''
  return `- ${arm.label} (${site}, n=${arm.n_display}): response ${pct(arm.response_rate)}${pfs}`
}

export function composeOpinion(fields: {
  recommendation: string
  rationale: string
  evidence: string[]
  caveats: string
}) {
  return [
    `Recommendation: ${fields.recommendation}`,
    `Rationale: ${fields.rationale}`,
    fields.evidence.length
      ? `Comparable patients (aggregate only, computed locally):\n${fields.evidence.join('\n')}`
      : 'Comparable patients: no local evidence cited.',
    `Check before deciding: ${fields.caveats}`,
    'Synthetic peer-review opinion for discussion at your MDO. The final decision rests with the treating team.',
  ].join('\n\n')
}
