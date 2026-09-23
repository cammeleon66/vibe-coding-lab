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
