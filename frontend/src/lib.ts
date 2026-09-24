import { useCallback, useEffect, useRef, useState } from 'react'

/** Load data and optionally refresh it on an interval. Errors are surfaced, not thrown. */
export function useLoad<T>(load: () => Promise<T>, intervalMs?: number, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const loadRef = useRef(load)
  loadRef.current = load

  const refresh = useCallback(async () => {
    try {
      const value = await loadRef.current()
      setData(value)
      setError(null)
      return value
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
      return null
    }
  }, [])

  useEffect(() => {
    void refresh()
    if (!intervalMs) return
    const timer = window.setInterval(() => void refresh(), intervalMs)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, intervalMs, ...deps])

  return { data, error, refresh, setData }
}

export function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export const STEP_LABELS: Record<string, string> = {
  AUTHORIZED: 'Clinician authorised',
  MINIMISED: 'Minimised',
  MINIMISATION_REFUSED: 'Minimisation refused',
  IDENTIFIERS_REMOVED: 'Identifiers removed',
  BUNDLE_BUILT: 'FHIR bundle built',
  SENT: 'Sent',
  SEND_FAILED: 'Send failed',
  VERIFIED: 'Signature verified',
  POLICY_ALLOWED: 'Policy check passed',
  POLICY_DENIED: 'Policy denied',
  ROUTED: 'Routed',
  DELIVERED: 'Delivered',
  DELIVERY_FAILED: 'Delivery failed',
  RECEIVED: 'Received',
  QUERY_REQUESTED: 'Query requested',
  QUERY_ROUTED: 'Query routed',
  LOCAL_QUERY_EXECUTED: 'Computed locally',
  AGGREGATE_RETURNED: 'Aggregate returned',
  AGGREGATE_RECEIVED: 'Aggregate received',
  SITE_UNAVAILABLE: 'Site unavailable',
  OPINION_SIGNED: 'Opinion signed',
  RESET: 'Reset',
  RECONCILED: 'Reconciled',
  SITE_ISOLATED: 'Operator isolated site',
  SITE_RECONNECTED: 'Operator reconnected site',
  ISOLATED: 'Site went offline',
  RECONNECTED: 'Site back online',
}

export const SERVICE_NAMES: Record<string, string> = {
  nl: 'UMC Utrecht',
  de: 'Heidelberg',
  hub: 'Federation hub',
  'nl+de': 'UMC Utrecht + Heidelberg',
}
