import type { ComponentType } from 'react'
import type { SceneId } from '../api/types'
import { LocalApprovalScene, LocalProblemScene, LocalResultScene, LocalSearchScene } from './LocalScenes'
import {
  CrossDestinationScene,
  CrossPackageScene,
  CrossPatientScene,
  CrossQuestionScene,
  CrossSourcesScene,
  MilanUpdateScene,
} from './MilanScenes'
import { ScaleNetworkScene } from './NetworkScene'
import type { SceneProps } from './types'
import { ClosingOutcomeScene, UtrechtMdoScene, UtrechtReviewScene } from './UtrechtScenes'

/** One screen per scene. The backend decides which scene is current. */
export const sceneComponents: Record<SceneId, ComponentType<SceneProps>> = {
  local_problem: LocalProblemScene,
  local_search: LocalSearchScene,
  local_approval: LocalApprovalScene,
  local_result: LocalResultScene,
  scale_network: ScaleNetworkScene,
  cross_patient: CrossPatientScene,
  cross_sources: CrossSourcesScene,
  cross_question: CrossQuestionScene,
  cross_destination: CrossDestinationScene,
  cross_package: CrossPackageScene,
  utrecht_review: UtrechtReviewScene,
  milan_update: MilanUpdateScene,
  utrecht_mdo: UtrechtMdoScene,
  closing_outcome: ClosingOutcomeScene,
}
