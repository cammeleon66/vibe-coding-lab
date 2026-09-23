import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const centre = {
  id: 'utrecht-crc',
  name: 'UMC Utrecht',
  city: 'Utrecht',
  country: 'Netherlands',
  network_context: 'European colorectal and liver-metastasis expertise',
  profile_label: 'Simulated demonstration profile',
  expertise_tags: ['metastatic colorectal cancer', 'conversion therapy'],
  accepted_evidence: ['pathology'],
  languages: ['Dutch', 'English'],
  synthetic_availability: 'Demonstration review slot available within two working days.',
  referral_pathway: 'Synthetic specialist review.',
  requirements: [
    {
      key: 'baseline-ct',
      label: 'Original baseline liver CT',
      evidence_type: 'baseline_ct',
      rationale: 'Baseline lesion mapping is required.',
    },
  ],
  clinicians: [
    {
      id: 'eva-van-dijk',
      name: 'Dr Eva van Dijk',
      role: 'Colorectal medical oncologist',
      specialties: ['conversion therapy'],
      languages: ['Dutch', 'English'],
      fictional: true,
      eligible: true,
    },
  ],
  simulated: true,
}

const matchResponse = {
  need: {
    case_id: 'CRC-EU-001',
    diagnosis: 'Metastatic colorectal cancer with liver-limited metastases',
    decision_focus: 'Conversion therapy and liver-metastasis resectability',
    referring_country: 'Italy',
    preferred_languages: ['Italian', 'English'],
    available_evidence: ['pathology'],
  },
  matches: [
    {
      centre,
      score: 100,
      reasons: [
        {
          label: 'Synthetic availability',
          detail: centre.synthetic_availability,
          status: 'match',
        },
      ],
      conditions: ['Provide Original baseline liver CT before final review.'],
    },
  ],
  limitations: [
    'This is a curated synthetic directory, not an exhaustive European registry.',
    'Credentials, permissions, availability and interoperability are simulated.',
  ],
}

function response(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(payload === undefined ? null : JSON.stringify(payload), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('expert discovery and referral', () => {
  it('uses the presenter-edited clinical need and explains synthetic availability', async () => {
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url === '/api/referrals/current') return response(null)
      if (url === '/api/cases/current') return response(null)
      if (url === '/api/expert-matches') return response(matchResponse)
      throw new Error(`Unexpected request: ${url} ${options?.method}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    const question = await screen.findByLabelText('Clinical question')
    await user.clear(question)
    await user.type(question, 'Could surgery become feasible after conversion therapy?')
    await user.click(screen.getByRole('button', { name: /find european expertise/i }))

    expect((await screen.findAllByText('UMC Utrecht')).length).toBeGreaterThan(0)
    expect(screen.getByText(centre.synthetic_availability)).toBeInTheDocument()
    expect(screen.getByText('Score 100')).toBeInTheDocument()

    const request = fetchMock.mock.calls.find(([url]) => url === '/api/expert-matches')
    expect(JSON.parse(String(request?.[1]?.body)).decision_focus).toBe(
      'Could surgery become feasible after conversion therapy?',
    )
  })

  it('sends the selected clinician, sender, and urgency with the referral', async () => {
    const referral = {
      id: 'REF-1234',
      version: 1,
      created_at: '2026-09-23T10:00:00Z',
      need: matchResponse.need,
      urgency: 'urgent',
      sender: {
        clinician_name: 'Dr Luca Bianchi',
        institution: 'Istituto Nazionale dei Tumori, Milan',
        country: 'Italy',
      },
      centre,
      clinician: centre.clinicians[0],
      requirements: [
        {
          key: 'baseline-ct',
          label: 'Original baseline liver CT',
          rationale: 'Baseline lesion mapping is required.',
          status: 'missing',
        },
      ],
      status: 'collaboration_requested',
      responsibility: {
        actor: 'Istituto Nazionale dei Tumori, Milan',
        action: 'Release the required synthetic evidence.',
      },
      limitations: ['Synthetic demonstration referral.'],
    }
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url === '/api/referrals/current') return response(null)
      if (url === '/api/cases/current') return response(null)
      if (url === '/api/expert-matches') return response(matchResponse)
      if (url === '/api/referrals') return response(referral, 201)
      throw new Error(`Unexpected request: ${url} ${options?.method}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.selectOptions(await screen.findByLabelText('Urgency'), 'urgent')
    await user.click(screen.getByRole('button', { name: /find european expertise/i }))
    await screen.findAllByText('UMC Utrecht')
    await user.click(screen.getByRole('button', { name: /request specialist collaboration/i }))

    expect(await screen.findByText(/collaboration workspace opened/i)).toBeInTheDocument()
    const request = fetchMock.mock.calls.find(([url]) => url === '/api/referrals')
    const body = JSON.parse(String(request?.[1]?.body))
    expect(body).toMatchObject({
      clinician_id: 'eva-van-dijk',
      urgency: 'urgent',
      sender: {
        clinician_name: 'Dr Luca Bianchi',
        institution: 'Istituto Nazionale dei Tumori, Milan',
      },
    })
  })

  it('shows restore failures rather than silently starting a fresh rehearsal', async () => {
    vi.stubGlobal('fetch', vi.fn(() => response({ detail: 'State store unavailable.' }, 503)))

    render(<App />)

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('State store unavailable.'),
    )
  })
})

const referral = {
  id: 'REF-1234',
  version: 1,
  created_at: '2026-09-23T10:00:00Z',
  need: matchResponse.need,
  urgency: 'expedited',
  sender: {
    clinician_name: 'Dr Luca Bianchi',
    institution: 'Istituto Nazionale dei Tumori, Milan',
    country: 'Italy',
  },
  centre,
  clinician: centre.clinicians[0],
  requirements: [],
  status: 'collaboration_requested',
  responsibility: { actor: 'Milan', action: 'Release evidence.' },
  limitations: [],
}

const evidence = {
  source_institution: 'Istituto Nazionale dei Tumori, Milan',
  source_identifier: 'MIL-CDA-001',
  source_format: 'CDA/XML',
  observed_at: '2025-03-03T09:00:00Z',
  received_at: '2026-09-23T10:00:00Z',
  content_hash: 'abc123',
  transformation_status: 'transformed',
  facts: [
    {
      key: 'diagnosis_date',
      label: 'Diagnosis date',
      category: 'diagnosis',
      raw_value: '14/02/2025',
      normalized_value: '2025-02-14',
      transformation: 'Converted DD/MM/YYYY to ISO 8601.',
      source_pointer: '/ClinicalDocument/problem/effectiveTime',
    },
  ],
  warnings: ['Italian date format was normalized.'],
  unmapped_values: [],
  retrieval_reference: 'fixtures/milan/referral.cda.xml',
  original_media_type: 'application/xml',
  original_content: '<ClinicalDocument />',
}

const preparedCase = {
  case_id: 'CRC-EU-001',
  referral_id: 'REF-1234',
  version: 1,
  prepared_at: '2026-09-23T10:10:00Z',
  clinical_question: 'Conversion therapy and liver-metastasis resectability',
  evidence: [evidence],
  claims: [
    {
      id: 'diagnosis-date-1',
      label: 'Diagnosis date',
      category: 'diagnosis',
      raw_value: '14/02/2025',
      normalized_value: '2025-02-14',
      kind: 'normalized_value',
      transformation: 'Converted DD/MM/YYYY to ISO 8601.',
      provenance: [
        {
          evidence_id: 'MIL-CDA-001',
          source_pointer: '/ClinicalDocument/problem/effectiveTime',
          source_institution: 'Istituto Nazionale dei Tumori, Milan',
          source_format: 'CDA/XML',
          observed_at: '2025-03-03T09:00:00Z',
          transformation_status: 'transformed',
        },
      ],
    },
  ],
  conflicts: [
    {
      id: 'conflict-diagnosis-date',
      field: 'diagnosis_date',
      description: 'Diagnosis date differs across source institutions.',
      claim_ids: ['diagnosis-date-1', 'diagnosis-date-2'],
      resolution: 'Unresolved; requires source-owner confirmation.',
    },
  ],
  missing: [
    {
      id: 'missing-molecular-profile',
      field: 'molecular_profile',
      description: 'RAS, BRAF and MMR/MSI evidence is missing.',
      severity: 'required',
      required_by: 'UMC Utrecht',
      provenance: [
        {
          evidence_id: 'MIL-CDA-001',
          source_pointer: '$.requirements.molecular',
          source_institution: 'UMC Utrecht',
          source_format: 'review requirements JSON',
          observed_at: '2026-09-23T10:06:00Z',
          transformation_status: 'original',
        },
      ],
    },
  ],
  warnings: ['Italian date format was normalized.'],
  unmapped_values: ['response_code=PRX'],
  synthesis: [
    {
      text: 'Diagnosis date: 2025-02-14.',
      support_ids: ['diagnosis-date-1'],
    },
  ],
  limitations: ['No treatment recommendation is produced.'],
  delta: null,
}

const updatedCase = {
  ...preparedCase,
  version: 2,
  evidence: [
    ...preparedCase.evidence,
    {
      ...evidence,
      source_identifier: '1.2.826.baseline',
      source_format: 'DICOM metadata JSON',
      retrieval_reference: 'fixtures/milan/baseline-ct.dicom-metadata.json',
      original_media_type: 'application/dicom+json',
      original_content: '{"Modality":"CT"}',
      facts: [
        {
          ...evidence.facts[0],
          key: 'original_lesion_sites',
          label: 'Original liver lesion sites',
          category: 'imaging',
          raw_value: 'segments IVa, VII and VIII',
          normalized_value: 'segments IVa, VII and VIII',
          source_pointer: 'LesionSites',
        },
      ],
    },
    {
      ...evidence,
      source_identifier: '1.2.826.restaging',
      source_format: 'DICOM metadata JSON',
      retrieval_reference: 'fixtures/milan/restaging-mri.dicom-metadata.json',
      original_media_type: 'application/dicom+json',
      original_content: '{"Modality":"MR"}',
      facts: [
        {
          ...evidence.facts[0],
          key: 'new_anatomical_evidence',
          label: 'New anatomical evidence',
          category: 'imaging',
          raw_value: 'Segment VIII abuts the right hepatic vein.',
          normalized_value: 'Segment VIII abuts the right hepatic vein.',
          source_pointer: 'NewAnatomicalEvidence',
        },
      ],
    },
  ],
  delta: {
    from_version: 1,
    to_version: 2,
    added_evidence: [
      {
        evidence_id: '1.2.826.baseline',
        label: 'Baseline imaging',
        source_format: 'DICOM metadata JSON',
        source_institution: 'Istituto Nazionale dei Tumori, Milan',
        observed_at: '2025-02-18T10:15:00Z',
      },
      {
        evidence_id: '1.2.826.restaging',
        label: 'Restaging imaging',
        source_format: 'DICOM metadata JSON',
        source_institution: 'Istituto Nazionale dei Tumori, Milan',
        observed_at: '2025-06-30T13:20:00Z',
      },
    ],
    changed_findings: [
      {
        subject: 'Longitudinal liver lesion mapping',
        before: 'No linked baseline lesion map or restaging MRI findings were available.',
        after: 'Original sites mapped; segment VIII abuts the right hepatic vein.',
        conclusion_requires_reassessment: true,
      },
    ],
    remaining_uncertainty: [
      'RAS status is missing.',
      'Resectability remains a human multidisciplinary conclusion.',
    ],
    affected_human_questions: [
      'How does the segment VIII relationship to the right hepatic vein affect planning?',
    ],
  },
}

describe('prepared clinical workspace', () => {
  it('continues a persisted referral and distinguishes source from normalized values', async () => {
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url === '/api/referrals/current') return response(referral)
      if (url === '/api/cases/current') return response(null)
      if (url === '/api/cases/current/prepare') return response(preparedCase)
      if (url === '/api/cases/current/sources/MIL-CDA-001') return response(evidence)
      throw new Error(`Unexpected request: ${url} ${options?.method}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: /prepare clinical workspace/i }),
    )

    expect(await screen.findByText('Evidence together. Origins intact.')).toBeInTheDocument()
    expect(screen.getByText('Source fact')).toBeInTheDocument()
    expect(screen.getByText('Normalized value')).toBeInTheDocument()
    expect(screen.getByText('14/02/2025')).toBeInTheDocument()
    expect(screen.getByText('2025-02-14')).toBeInTheDocument()
    expect(screen.getByText(/unresolved source conflict/i)).toBeInTheDocument()
    expect(screen.getByText(/RAS, BRAF and MMR\/MSI evidence is missing/i)).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', {
        name: /Istituto Nazionale dei Tumori, Milan · CDA\/XML/i,
      }),
    )
    expect(await screen.findByLabelText('Source evidence inspector')).toBeInTheDocument()
    expect(screen.getByText('fixtures/milan/referral.cda.xml')).toBeInTheDocument()
  })

  it('keeps the referral visible and reports preparation failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/referrals/current') return response(referral)
        if (url === '/api/cases/current') return response(null)
        if (url === '/api/cases/current/prepare') {
          return response({ detail: 'Institution source unavailable.' }, 503)
        }
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    const user = userEvent.setup()
    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: /prepare clinical workspace/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Institution source unavailable.',
    )
    expect(screen.getByText(/collaboration workspace opened/i)).toBeInTheDocument()
  })

  it('delivers late imaging without an AI prompt and shows before, after, and delta', async () => {
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url === '/api/referrals/current') return response(referral)
      if (url === '/api/cases/current') return response(preparedCase)
      if (url === '/api/cases/current/update-error') return response(null)
      if (url === '/api/evidence-arrivals') {
        return response({
          event_id: 'local-event-grid-imaging-001',
          duplicate: false,
          prepared_case: updatedCase,
        })
      }
      if (url === '/api/cases/current/sources/MIL-CDA-001?version=1') {
        return response(evidence)
      }
      throw new Error(`Unexpected request: ${url} ${options?.method}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: /receive late imaging evidence/i }),
    )

    expect(await screen.findByText(/what changed from case v1 to v2/i)).toBeInTheDocument()
    expect(screen.getByText('Before · case v1')).toBeInTheDocument()
    expect(screen.getByText('After · case v2')).toBeInTheDocument()
    expect(screen.getAllByText('Baseline imaging').length).toBeGreaterThan(0)
    expect(screen.getByText('Changed findings & conclusions')).toBeInTheDocument()
    expect(screen.getByText('Remaining uncertainty')).toBeInTheDocument()
    expect(screen.getByText('Affected human questions')).toBeInTheDocument()
    expect(screen.getByText(/human conclusion requires reassessment/i)).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).toLowerCase().includes('ai'))).toBe(
      false,
    )

    await user.click(screen.getByRole('button', { name: 'CDA/XML' }))
    expect(await screen.findByLabelText('Source evidence inspector')).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(
        ([url]) => url === '/api/cases/current/sources/MIL-CDA-001?version=1',
      ),
    ).toBe(true)
  })

  it('keeps case v1 visible and explicitly reports an evidence update failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/referrals/current') return response(referral)
        if (url === '/api/cases/current') return response(preparedCase)
        if (url === '/api/cases/current/update-error') return response(null)
        if (url === '/api/evidence-arrivals') {
          return response({ detail: 'Synthetic imaging parser failed.' }, 422)
        }
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    const user = userEvent.setup()
    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: /receive late imaging evidence/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Synthetic imaging parser failed.',
    )
    expect(screen.getByText(/case v1 preserved/i)).toBeInTheDocument()
    expect(screen.getByText('Prepared clinical workspace · case v1')).toBeInTheDocument()
    expect(screen.queryByText(/what changed from case v1 to v2/i)).not.toBeInTheDocument()
  })
})

const requiredConditions = [
  {
    issue_id: 'missing-molecular-profile',
    kind: 'required_evidence',
    description: 'RAS, BRAF and MMR/MSI evidence is missing.',
    status: 'open',
    resolution: '',
  },
  {
    issue_id: 'conflict-diagnosis-date',
    kind: 'review',
    description: 'Diagnosis date differs across source institutions.',
    status: 'open',
    resolution: '',
  },
]

const savedOpinion = {
  id: 'OP-REVIEW1',
  case_id: 'CRC-EU-001',
  case_version: 1,
  reviewer: 'Dr Eva van Dijk',
  opinion: 'Suitable for multidisciplinary review after explicit condition resolution.',
  conditions: requiredConditions.map((condition) => ({
    ...condition,
    status: 'resolved',
    resolution: 'Reviewed against the source record.',
  })),
  next_responsibility: {
    actor: 'Utrecht colorectal MDO coordinator',
    action: 'Schedule multidisciplinary review of the versioned synthetic case.',
  },
  recorded_at: '2026-09-23T10:30:00Z',
}

const handoffManifest = {
  id: 'MDO-CRC-EU-001-V1',
  version: 1,
  case_id: 'CRC-EU-001',
  clinical_question: preparedCase.clinical_question,
  evidence_version: 1,
  source_evidence_inventory: ['MIL-CDA-001'],
  unresolved_issues: [],
  opinion_id: savedOpinion.id,
  responsibility: savedOpinion.next_responsibility,
  created_at: '2026-09-23T10:31:00Z',
  synthetic_labels: ['synthetic-case', 'demonstration-only', 'not-for-clinical-use'],
  launch_url:
    'http://localhost:5174?case_id=CRC-EU-001&evidence_version=1&handoff_manifest=MDO-CRC-EU-001-V1',
  separate_backend: true,
  backend_notice:
    'Version one launches the autonomous MDO demonstration with a narrative deep link. The MDO uses a separate backend and does not receive shared runtime state.',
}

describe('human responsibility and MDO handoff', () => {
  it('records version-bound responsibility and creates a controlled continuity manifest', async () => {
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url === '/api/referrals/current') return response(referral)
      if (url === '/api/cases/current') return response(preparedCase)
      if (url === '/api/cases/current/update-error') return response(null)
      if (url === '/api/cases/current/handoffs' && !options?.method) return response([])
      if (url === '/api/cases/current/review') {
        return response({
          current_case_version: 1,
          opinion: null,
          required_conditions: requiredConditions,
          stale: false,
          handoff_ready: false,
          blockers: ['Record a human opinion for case v1.'],
        })
      }
      if (url === '/api/cases/current/reviews') {
        return response(
          {
            current_case_version: 1,
            opinion: savedOpinion,
            required_conditions: savedOpinion.conditions,
            stale: false,
            handoff_ready: true,
            blockers: [],
          },
          201,
        )
      }
      if (url === '/api/cases/current/handoffs' && options?.method === 'POST') {
        return response(handoffManifest, 201)
      }
      throw new Error(`Unexpected request: ${url} ${options?.method}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.type(
      await screen.findByLabelText('Considered human opinion'),
      savedOpinion.opinion,
    )
    for (const checkbox of screen.getAllByRole('checkbox')) {
      await user.click(checkbox)
    }
    for (const note of screen.getAllByPlaceholderText('Required when marked resolved')) {
      await user.type(note, 'Reviewed against the source record.')
    }
    await user.click(screen.getByRole('button', { name: /save opinion for case v1/i }))

    expect(
      await screen.findByText('Ready to create handoff'),
    ).toBeInTheDocument()
    const reviewRequest = fetchMock.mock.calls.find(
      ([url]) => url === '/api/cases/current/reviews',
    )
    expect(JSON.parse(String(reviewRequest?.[1]?.body))).toMatchObject({
      case_version: 1,
      reviewer: 'Dr Eva van Dijk',
      next_responsibility: savedOpinion.next_responsibility,
    })

    await user.click(screen.getByRole('button', { name: /create mdo handoff manifest/i }))

    expect(await screen.findByText('MDO-CRC-EU-001-V1')).toBeInTheDocument()
    expect(screen.getAllByText(preparedCase.clinical_question).length).toBeGreaterThan(1)
    expect(screen.getAllByText(/MDO uses a separate backend/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /launch separate MDO demonstration/i })).toHaveAttribute(
      'href',
      handoffManifest.launch_url,
    )
  })

  it('shows that an older opinion is stale and keeps handoff gated', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/referrals/current') return response(referral)
        if (url === '/api/cases/current') return response(updatedCase)
        if (url === '/api/cases/current/update-error') return response(null)
        if (url === '/api/cases/current/versions/1') return response(preparedCase)
        if (url === '/api/cases/current/handoffs') return response([handoffManifest])
        if (url === '/api/cases/current/review') {
          return response({
            current_case_version: 2,
            opinion: savedOpinion,
            required_conditions: requiredConditions,
            stale: true,
            handoff_ready: false,
            blockers: ['Opinion OP-REVIEW1 applies to case v1; case v2 requires a new review.'],
          })
        }
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    render(<App />)

    expect(await screen.findByText('Previous opinion is stale')).toBeInTheDocument()
    expect(screen.getByText(/covers case v1/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create mdo handoff manifest/i })).toBeDisabled()
    expect(screen.getByText(/case v2 requires a new review/i)).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /launch separate MDO demonstration/i }),
    ).not.toBeInTheDocument()
  })
})

const researchPublication = {
  projection: {
    id: 'RP-CRC-EU-001-V1',
    purpose:
      'Synthetic cohort feasibility for metastatic colorectal cancer collaboration research.',
    version: 1,
    schema_version: 'research-cohort-v1',
    case_version: 1,
    approved_fields: ['synthetic_case_id', 'diagnosis', 'histology', 'systemic_treatment'],
    record: {
      synthetic_case_id: 'CRC-EU-001',
      diagnosis: 'Metastatic colorectal adenocarcinoma with liver metastases',
      histology: 'Moderately differentiated colorectal adenocarcinoma',
      systemic_treatment: 'FOLFOXIRI plus bevacizumab, 6 cycles',
    },
    lineage: [
      {
        field: 'diagnosis',
        prepared_claim_id: 'diagnosis-1',
        source_record_id: 'MIL-CDA-001',
        source_institution: 'Istituto Nazionale dei Tumori, Milan',
        source_format: 'CDA/XML',
        source_pointer: '/ClinicalDocument/diagnosis',
      },
    ],
    excluded_categories: [
      'workflow notes',
      'direct source documents',
      'patient identifiers',
      'human opinions',
      'handoff responsibility',
    ],
    synthetic_only: true,
  },
  receipt: {
    id: 'LOCAL-FABRIC-RP-CRC-EU-001-V1',
    projection_id: 'RP-CRC-EU-001-V1',
    projection_version: 1,
    adapter: 'local-fabric-fake',
    published_at: '2026-09-23T16:00:00Z',
  },
}

function researchWorkspaceFetch(
  researchHandler: (options?: RequestInit) => Promise<Response>,
) {
  return vi.fn((url: string, options?: RequestInit) => {
    if (url === '/api/referrals/current') return response(referral)
    if (url === '/api/cases/current') return response(preparedCase)
    if (url === '/api/cases/current/update-error') return response(null)
    if (url === '/api/cases/current/handoffs') return response([])
    if (url === '/api/cases/current/review') {
      return response({
        current_case_version: 1,
        opinion: null,
        required_conditions: requiredConditions,
        stale: false,
        handoff_ready: false,
        blockers: ['Human opinion is required.'],
      })
    }
    if (url === '/api/research/authorize') return response(undefined, 204)
    if (url === '/api/research/projection') return researchHandler(options)
    throw new Error(`Unexpected request: ${url} ${options?.method}`)
  })
}

describe('research authorization epilogue', () => {
  it('shows a loading state while the authorized projection is retrieved', async () => {
    let resolveResearch: ((value: Response) => void) | undefined
    const pending = new Promise<Response>((resolve) => {
      resolveResearch = resolve
    })
    vi.stubGlobal('fetch', researchWorkspaceFetch(() => pending))
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('Clinical access stops here.')
    await user.type(screen.getByLabelText('Research authorization code'), 'research-code')
    await user.click(screen.getByRole('button', { name: /open synthetic research epilogue/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Loading approved research projection',
    )
    resolveResearch?.(await response(null))
    expect(await screen.findByText('No approved projection published')).toBeInTheDocument()
  })

  it('shows clinical denial, empty state, allowlisted fields, and lineage', async () => {
    const fetchMock = researchWorkspaceFetch((options) =>
      options?.method === 'POST' ? response(researchPublication, 201) : response(null),
    )
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByText('Clinical access stops here.')).toBeInTheDocument()
    expect(screen.getByText(/Clinical role · denied/i)).toBeInTheDocument()
    await user.type(screen.getByLabelText('Research authorization code'), 'research-code')
    await user.click(screen.getByRole('button', { name: /open synthetic research epilogue/i }))

    expect(await screen.findByText('No approved projection published')).toBeInTheDocument()
    const authorization = fetchMock.mock.calls.find(
      ([url]) => url === '/api/research/authorize',
    )
    expect(JSON.parse(String(authorization?.[1]?.body))).toEqual({
      authorization_code: 'research-code',
    })

    await user.click(
      screen.getByRole('button', { name: /publish approved synthetic projection/i }),
    )

    expect(
      await screen.findByText('Cohort feasibility, not the clinical workspace.'),
    ).toBeInTheDocument()
    expect(screen.getByText('research-cohort-v1')).toBeInTheDocument()
    expect(
      screen.getByText('Metastatic colorectal adenocarcinoma with liver metastases'),
    ).toBeInTheDocument()
    expect(screen.getByText(/diagnosis-1 ← MIL-CDA-001/i)).toBeInTheDocument()
    expect(screen.getByText(/workflow notes · direct source documents/i)).toBeInTheDocument()
    expect(screen.queryByText(/preserved original record/i)).not.toBeInTheDocument()
  })

  it('keeps failed publication explicit and hides an unconfirmed cohort', async () => {
    vi.stubGlobal(
      'fetch',
      researchWorkspaceFetch((options) =>
        options?.method === 'POST'
          ? response(
              {
                detail:
                  'The local Fabric publication simulation failed; no projection was published.',
              },
              503,
            )
          : response(null),
      ),
    )
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('Clinical access stops here.')
    await user.type(screen.getByLabelText('Research authorization code'), 'research-code')
    await user.click(screen.getByRole('button', { name: /open synthetic research epilogue/i }))
    await screen.findByText('No approved projection published')
    await user.click(
      screen.getByRole('button', { name: /publish approved synthetic projection/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent('Publication failed')
    expect(screen.getByRole('alert')).toHaveTextContent('no projection was published')
    expect(screen.getByText('No unconfirmed projection is shown.')).toBeInTheDocument()
    expect(screen.queryByText('Feasible synthetic cohort')).not.toBeInTheDocument()
  })

  it('offers an explicit publication update when the clinical case advances', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/referrals/current') return response(referral)
        if (url === '/api/cases/current') return response(updatedCase)
        if (url === '/api/cases/current/update-error') return response(null)
        if (url === '/api/cases/current/versions/1') return response(preparedCase)
        if (url === '/api/cases/current/handoffs') return response([])
        if (url === '/api/cases/current/review') {
          return response({
            current_case_version: 2,
            opinion: null,
            required_conditions: requiredConditions,
            stale: false,
            handoff_ready: false,
            blockers: ['Human opinion is required.'],
          })
        }
        if (url === '/api/research/authorize') return response(undefined, 204)
        if (url === '/api/research/projection') return response(researchPublication)
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('Clinical access stops here.')
    await user.type(screen.getByLabelText('Research authorization code'), 'research-code')
    await user.click(screen.getByRole('button', { name: /open synthetic research epilogue/i }))

    expect(
      await screen.findByText('New clinical evidence is not yet in the research projection'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /publish case v2 projection/i }),
    ).toBeInTheDocument()
  })
})
