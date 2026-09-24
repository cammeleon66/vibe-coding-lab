import type {
  ActivityResponse,
  Chart,
  CohortQuery,
  Expert,
  FanOutResult,
  InboxCase,
  PackageAsSent,
  Patient,
  PeerReview,
  Progress,
  SitesResponse,
} from './types'

export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const detail = typeof payload?.detail === 'string' ? payload.detail : null
    throw new ApiError(detail ?? `Request failed with status ${response.status}.`, response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const post = <T,>(url: string, body: unknown = {}) =>
  requestJson<T>(url, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  sites: () => requestJson<SitesResponse>('/api/sites'),
  progress: () => requestJson<Progress>('/api/federation/progress'),
  activity: () => requestJson<ActivityResponse>('/api/federation/activity'),
  experts: (q: string) =>
    requestJson<Expert[]>(`/api/federation/experts?q=${encodeURIComponent(q)}`),
  packageAsSent: (caseId: string) =>
    requestJson<PackageAsSent>(`/api/federation/peer-reviews/${caseId}/package`),
  connectivity: (site: 'nl' | 'de', online: boolean) =>
    post<{ site: string; online: boolean }>(`/api/sites/${site}/connectivity`, { online }),
  reset: () => post<{ generation: number; pending_reset: string[] }>('/api/reset'),
  nl: {
    patients: () => requestJson<Patient[]>('/api/nl/patients'),
    chart: (id: string) => requestJson<Chart>(`/api/nl/patients/${id}`),
    reviews: () => requestJson<PeerReview[]>('/api/nl/peer-reviews'),
    send: (body: { patient_id: string; expert_id: string; categories: string[]; question: string }) =>
      post<PeerReview>('/api/nl/peer-reviews', body),
    resend: (caseId: string) => post<PeerReview>(`/api/nl/peer-reviews/${caseId}/resend`),
  },
  de: {
    inbox: () => requestJson<InboxCase[]>('/api/de/inbox'),
    case: (caseId: string) => requestJson<InboxCase>(`/api/de/inbox/${caseId}`),
    compare: (caseId: string, query: CohortQuery = {}) =>
      post<InboxCase>(`/api/de/inbox/${caseId}/cohort-query`, { query }),
    opinion: (caseId: string, opinion: string, includeCohort: boolean) =>
      post<InboxCase>(`/api/de/inbox/${caseId}/opinion`, {
        opinion,
        include_cohort_evidence: includeCohort,
      }),
  },
  research: (query: CohortQuery) => post<FanOutResult>('/api/research/cohort-queries', { query }),
}
