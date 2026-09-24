export type JourneyRole = 'milan' | 'utrecht'

export type SceneId =
  | 'local_problem'
  | 'local_search'
  | 'local_approval'
  | 'local_result'
  | 'scale_network'
  | 'cross_patient'
  | 'cross_sources'
  | 'cross_question'
  | 'cross_destination'
  | 'cross_package'
  | 'utrecht_review'
  | 'milan_update'
  | 'utrecht_mdo'
  | 'closing_outcome'

export type ChapterId = 'local' | 'network' | 'cross_border'
export type StoryStatus = 'complete' | 'current' | 'upcoming'
export type RegionalSourceId = 'utrecht_patient_summary' | 'utrecht_imaging'
export type FederatedSourceId = 'milan_ehr' | 'milan_documents' | 'milan_pacs'

export interface StoryActor {
  name: string
  role: string
  institution: string
  kind: 'clinician' | 'network'
}

export interface StoryChapter {
  id: ChapterId
  title: string
  scope: string
  status: StoryStatus
}

export interface StoryScene {
  id: SceneId
  chapter: ChapterId
  title: string
  status: StoryStatus
  actor: StoryActor
}

export interface AgentStep {
  label: string
  detail: string
  status: 'done' | 'pending'
  call: string | null
}

export interface AgentBrief {
  name: string
  works_for: string
  summary: string
  steps: AgentStep[]
  boundary: string
}

export interface Handoff {
  from_actor: StoryActor
  to_actor: StoryActor
  carried: string
}

export interface SystemCall {
  id: string
  scene: SceneId
  system: string
  endpoint: string
  status: '200 OK' | 'Failed'
  detail: string
}

export interface Storyline {
  chapters: StoryChapter[]
  scenes: StoryScene[]
  current_scene: SceneId
  current_index: number
  actor: StoryActor
  can_advance: boolean
  advance_label: string | null
  blocked_reason: string | null
  agent: AgentBrief | null
  handoff: Handoff | null
  system_calls: SystemCall[]
}

export interface SourceRecord {
  id: string
  label: string
  status: 'available' | 'missing'
  detail: string
}

export interface RegionalSourceCheck {
  source_id: RegionalSourceId
  source_label: string
  endpoint: string
  owner_institution: string
  requesting_institution: string
  status: 'complete'
  records: SourceRecord[]
  checked_at: string
}

export interface RegionalExchange {
  patient_label: string
  case_id: string
  requesting_institution: string
  requesting_clinician: string
  source_institution: string
  source_clinician: string
  problem: string
  crosses_boundary: string[]
  stays_at_source: string[]
  source_checks: Partial<Record<RegionalSourceId, RegionalSourceCheck>>
  sharing_approved: boolean
  approved_by: string | null
  shared_result: { title: string; finding: string; impact: string[] } | null
  next_responsibility: string | null
}

export interface JourneyPatient {
  case_id: string
  display_name: string
  age_band: string
  diagnosis: string
  care_status: string
  current_plan: string
  last_updated: string
  referral_candidate: boolean
}

export interface JourneyActivity {
  id: string
  kind: string
  actor: string
  institution: string
  title: string
  detail: string
  occurred_at: string
}

export interface SourceCheck {
  source_id: FederatedSourceId
  source_label: string
  endpoint: string
  patient_id: string
  status: 'complete' | 'failed'
  records: SourceRecord[]
  checked_at: string
  error: string | null
}

export interface Requirement {
  key: string
  label: string
  rationale: string
  status: 'present' | 'missing'
}

export interface Destination {
  centre_id: string
  centre_name: string
  city: string
  country: string
  clinician_id: string
  clinician_name: string
  score: number
  reasons: { label: string; detail: string; status: 'match' | 'condition' }[]
  limitations: string[]
}

export interface ReferralPackage {
  case_version: number
  clinical_question: string
  centre_name: string
  clinician_name: string
  requirements: Requirement[]
  structured_context: string[]
  retained_in_milan: string[]
  provenance_links: number
  missing_evidence: string[]
  approved: boolean
  approved_by: string | null
  referral_assessment: string | null
}

export interface JourneySnapshot {
  storyline: Storyline
  regional_exchange: RegionalExchange
  active_role: JourneyRole | null
  selected_patient_id: string | null
  patients: JourneyPatient[]
  activity: JourneyActivity[]
  source_checks: SourceCheck[]
  clinical_question: string | null
  destinations: Destination[]
  selected_centre_id: string | null
  requirements: Requirement[]
  package: ReferralPackage | null
  acknowledged_versions: number[]
  provisional_opinion: string | null
  evidence_request: {
    case_version: number
    requested_evidence: string[]
    clinical_reason: string
    requested_by: string
    requested_at: string
  } | null
  update_available_version: number | null
  update_approved_versions: number[]
  final_opinion: string | null
  mdo_outcome: {
    case_version: number
    specialist: string
    final_opinion: string
    scheduled_for: string
    accepted_at: string
    next_responsible_actor: string
    next_action: string
  } | null
  evidence_update: {
    case_version: number
    previous_version: number
    added_evidence: string[]
    changed_findings: string[]
    remaining_uncertainty: string[]
  } | null
}

export type JourneyAction =
  | { type: 'advance_scene'; from_scene: SceneId }
  | { type: 'query_regional_source'; source_id: RegionalSourceId }
  | { type: 'approve_regional_exchange' }
  | { type: 'select_patient'; patient_id: string }
  | { type: 'query_source'; source_id: FederatedSourceId }
  | { type: 'confirm_referral_question'; question: string }
  | { type: 'query_expert_directory' }
  | { type: 'select_destination'; centre_id: string; clinician_id: string }
  | { type: 'query_requirements' }
  | { type: 'prepare_referral_package' }
  | { type: 'approve_referral_package'; referral_assessment: string }
  | { type: 'acknowledge_case_version'; case_version: number }
  | { type: 'record_provisional_opinion'; opinion: string }
  | { type: 'request_evidence'; requested_evidence: string[]; clinical_reason: string }
  | { type: 'approve_evidence_update'; case_version: number }
  | { type: 'record_final_opinion'; opinion: string }
  | { type: 'accept_mdo_outcome'; scheduled_for: string; next_action: string }
