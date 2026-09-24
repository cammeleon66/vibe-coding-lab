import type { JourneyAction, JourneySnapshot } from '../api/types'

export interface SceneProps {
  snapshot: JourneySnapshot
  busy: boolean
  /** True when the presenter is looking back at an earlier step. */
  readOnly: boolean
  act: (action: JourneyAction) => Promise<JourneySnapshot | null>
  runAgent: (actions: JourneyAction[]) => Promise<JourneySnapshot | null>
  deliverImagingEvent: () => Promise<void>
  reset: () => Promise<void>
}
