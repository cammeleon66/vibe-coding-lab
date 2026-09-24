import type {
  FederatedSourceId,
  JourneyAction,
  JourneySnapshot,
  RegionalSourceId,
  SceneId,
} from '../api/types'

const regionalSources: RegionalSourceId[] = ['utrecht_patient_summary', 'utrecht_imaging']
const milanSources: FederatedSourceId[] = ['milan_ehr', 'milan_documents', 'milan_pacs']

/**
 * Agent work that starts automatically when a scene opens. The same list tells a
 * restored scene whether the agent still has unfinished work to resume.
 */
export function sceneEntryWork(scene: SceneId, snapshot: JourneySnapshot): JourneyAction[] {
  switch (scene) {
    case 'local_search':
      return regionalSources
        .filter((id) => !snapshot.regional_exchange.source_checks[id])
        .map((source_id) => ({ type: 'query_regional_source', source_id }))
    case 'cross_sources':
      return milanSources
        .filter(
          (id) =>
            !snapshot.source_checks.some(
              (check) => check.source_id === id && check.status === 'complete',
            ),
        )
        .map((source_id) => ({ type: 'query_source', source_id }))
    case 'cross_destination':
      return snapshot.destinations.length === 0 ? [{ type: 'query_expert_directory' }] : []
    case 'cross_package': {
      const work: JourneyAction[] = []
      if (snapshot.requirements.length === 0) work.push({ type: 'query_requirements' })
      if (!snapshot.package) work.push({ type: 'prepare_referral_package' })
      return work
    }
    default:
      return []
  }
}
