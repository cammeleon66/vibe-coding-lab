export type SiteId = 'nl' | 'de' | 'hub'
export type Role = 'nl' | 'de' | 'control' | 'research'

export interface SiteStatus {
  site: SiteId
  name: string
  environment: string
  reachable: boolean
  latency_ms: number
  error?: string | null
  version?: string | null
  generation?: number | null
  synced?: boolean
  warm?: boolean
  isolated?: boolean
  role: string
}

export interface SitesResponse {
  generation: number
  pending_reset: string[]
  synced: boolean
  sites: SiteStatus[]
  catalogue_only: { site: string; name: string }[]
}

export interface Patient {
  id: string
  name: string
  age: number
  sex: string
  mrn: string
  summary: string
  flag: string
  open_peer_reviews: number
  restricted?: boolean
}

export interface FhirResource {
  resourceType: string
  id: string
  meta: { category: string; tab: string; title: string }
  effectiveDate?: string
  [field: string]: unknown
}

export interface SharingCategory {
  id: string
  label: string
  default: boolean
  shareable: boolean
}

export interface BundleEntry {
  resourceType: string
  id: string
  category: string
  title: string
  monthsSinceDiagnosis: number
  [field: string]: unknown
}

export interface Bundle {
  resourceType: 'Bundle'
  subject: { pseudonym: string; ageBand: string; sex: string }
  entry: BundleEntry[]
}

export interface MinimisationReport {
  source_resources: number
  shared_resources: number
  categories: string[]
  identifiers_removed: string[]
  method: string
}

export interface Expert {
  id: string
  site: string
  clinician: string
  institution: string
  country: string
  expertise: string
  connected: boolean
  services: string[]
  score: number
}

export interface ArmAggregate {
  arm: string
  label: string
  n: number | null
  n_display: string
  response_rate: number | null
  median_pfs_months: number | null
  suppressed: boolean
}

export interface CohortAggregate {
  site: string
  name: string
  query_digest: string
  records_scanned: number
  records_queried_locally: number
  records_transferred: number
  k_threshold: number
  suppressed_cells: number
  arms: ArmAggregate[]
}

export interface CohortQuery {
  diagnosis?: 'metastatic_colorectal_cancer'
  kras_variant?: 'G12C' | 'G12D' | 'G12V' | 'any'
  min_prior_lines?: number
}

export interface FanOutResult {
  correlation_id: string
  query?: CohortQuery
  results: CohortAggregate[]
  unavailable: { site: string; detail: string }[]
  complete: boolean
  not_connected: { site: string; name: string }[]
  records_transferred: number
}

export interface Opinion {
  text: string
  author: string
  institution: string
  cohort: { results: CohortAggregate[] } | null
  received_at: string
}

export interface PeerReview {
  case_id: string
  correlation_id: string
  expert: Expert
  question: string
  categories: string[]
  report: MinimisationReport
  bundle: Bundle
  status: 'sending' | 'delivered' | 'delivery_failed' | 'opinion_received'
  created_at: string
  opinion: Opinion | null
  error: string | null
}

export interface Chart {
  patient: FhirResource & {
    name: { family: string; given: string[] }[]
    birthDate: string
    gender: string
    identifier: { system: string; value: string }[]
  }
  resources: FhirResource[]
  resource_count: number
  sharing_categories: SharingCategory[]
  peer_reviews: PeerReview[]
}

export interface InboxCase {
  case_id: string
  correlation_id: string
  from_site: string
  requested_by: string
  question: string
  categories: string[]
  bundle: Bundle
  report: MinimisationReport
  received_at: string
  status: 'new' | 'in_review' | 'completed'
  cohort: (FanOutResult & { correlation_id: string }) | null
  opinion: { text: string; sent_at: string } | null
}

export interface AuditEvent {
  event_id: string
  timestamp: string
  service: SiteId
  source: string
  destination: string
  correlation_id: string
  operation: string
  step: string
  status: string
  detail: string
  policy: { allowed: boolean; reasons: string[] } | null
  manifest: Record<string, number>
  body_sha256: string | null
  snapshot: unknown
}

export interface ActivityResponse {
  events: AuditEvent[]
  unavailable: string[]
  generation: number
}

export interface Progress {
  case_sent: boolean
  cohort_compared: boolean
  opinion_returned: boolean
  research_run: boolean
  disconnect_seen: boolean
}

export interface PackageAsSent {
  case_id: string
  correlation_id: string
  bundle: Bundle
  report: MinimisationReport
  retrieved_from: string
  sha256: string
  matches_audit: boolean
}
