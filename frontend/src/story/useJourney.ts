import { useCallback, useEffect, useRef, useState } from 'react'
import { journeyApi } from '../api/client'
import type { JourneyAction, JourneySnapshot } from '../api/types'
import { sceneEntryWork } from '../scenes/entryWork'

const AGENT_STEP_PAUSE_MS = import.meta.env.MODE === 'test' ? 0 : 450

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export interface JourneyController {
  snapshot: JourneySnapshot | null
  busy: boolean
  error: string | null
  notice: string | null
  act: (action: JourneyAction) => Promise<JourneySnapshot | null>
  runAgent: (actions: JourneyAction[]) => Promise<JourneySnapshot | null>
  advance: () => Promise<void>
  deliverImagingEvent: () => Promise<void>
  reset: () => Promise<void>
  dismissError: () => void
}

export function useJourney(): JourneyController {
  const [snapshot, setSnapshot] = useState<JourneySnapshot | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const latest = useRef<JourneySnapshot | null>(null)

  const publish = useCallback((next: JourneySnapshot) => {
    latest.current = next
    setSnapshot(next)
  }, [])

  useEffect(() => {
    journeyApi
      .load()
      .then(publish)
      .catch((reason: unknown) => setError(messageOf(reason, 'Could not restore the story.')))
  }, [publish])

  const guarded = useCallback(
    async <T,>(work: () => Promise<T>, fallback: string): Promise<T | null> => {
      setBusy(true)
      setError(null)
      setNotice(null)
      try {
        return await work()
      } catch (reason) {
        setError(messageOf(reason, fallback))
        return null
      } finally {
        setBusy(false)
      }
    },
    [],
  )

  const sequence = useCallback(
    async (actions: JourneyAction[]) => {
      let current = latest.current
      for (const [index, action] of actions.entries()) {
        if (index > 0) await pause(AGENT_STEP_PAUSE_MS)
        current = await journeyApi.act(action)
        publish(current)
      }
      return current
    },
    [publish],
  )

  const act = useCallback(
    (action: JourneyAction) => guarded(() => sequence([action]), 'The action could not be completed.'),
    [guarded, sequence],
  )

  const runAgent = useCallback(
    (actions: JourneyAction[]) => guarded(() => sequence(actions), 'The agent could not finish.'),
    [guarded, sequence],
  )

  const advance = useCallback(async () => {
    const from = latest.current?.storyline.current_scene
    if (!from) return
    await guarded(async () => {
      const moved = await journeyApi.act({ type: 'advance_scene', from_scene: from })
      publish(moved)
      const work = sceneEntryWork(moved.storyline.current_scene, moved)
      if (work.length > 0) {
        await pause(AGENT_STEP_PAUSE_MS)
        await sequence(work)
      }
    }, 'The story could not move on.')
  }, [guarded, publish, sequence])

  const deliverImagingEvent = useCallback(async () => {
    await guarded(async () => {
      await journeyApi.deliverImagingEvent()
      for (let attempt = 0; attempt < 20; attempt += 1) {
        const refreshed = await journeyApi.load()
        publish(refreshed)
        if (refreshed.evidence_update) return
        await pause(750)
      }
      throw new Error('The imaging event was sent but the update has not arrived yet.')
    }, 'The imaging update could not be delivered.')
  }, [guarded, publish])

  const reset = useCallback(async () => {
    const done = await guarded(async () => {
      await journeyApi.reset()
      publish(await journeyApi.load())
      return true
    }, 'The story could not be reset.')
    if (done) setNotice('The synthetic story has been reset to the beginning.')
  }, [guarded, publish])

  return {
    snapshot,
    busy,
    error,
    notice,
    act,
    runAgent,
    advance,
    deliverImagingEvent,
    reset,
    dismissError: () => setError(null),
  }
}

function messageOf(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback
}
