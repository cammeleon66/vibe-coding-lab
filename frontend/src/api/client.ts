import type { JourneyAction, JourneySnapshot } from './types'

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const detail = typeof payload?.detail === 'string' ? payload.detail : null
    throw new Error(detail ?? `Request failed with status ${response.status}.`)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const journeyApi = {
  load: () => requestJson<JourneySnapshot>('/api/journey'),
  act: (action: JourneyAction) =>
    requestJson<JourneySnapshot>('/api/journey/actions', {
      method: 'POST',
      body: JSON.stringify(action),
    }),
  reset: () => requestJson<void>('/api/reset', { method: 'POST' }),
  deliverImagingEvent: () =>
    requestJson<unknown>('/api/evidence-arrivals', {
      method: 'POST',
      body: JSON.stringify({
        event_id: 'journey-imaging-001',
        occurred_at: new Date().toISOString(),
      }),
    }),
}
