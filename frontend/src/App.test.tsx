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

    const question = screen.getByLabelText('Clinical question')
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

    await user.selectOptions(screen.getByLabelText('Urgency'), 'urgent')
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
})
