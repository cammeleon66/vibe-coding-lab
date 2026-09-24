import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const roles = [
  {
    id: 'milan',
    clinician_name: 'Dr Luca Bianchi',
    institution: 'Istituto Nazionale dei Tumori, Milan',
    specialty: 'Medical oncology',
    responsibilities: [
      'Select the patient',
      'Approve referral sharing',
      'Approve later evidence updates',
    ],
    available: true,
    unavailable_reason: null,
    recommended: true,
  },
  {
    id: 'utrecht',
    clinician_name: 'Dr Eva van Dijk',
    institution: 'UMC Utrecht',
    specialty: 'Colorectal oncology',
    responsibilities: [
      'Review incoming referral',
      'Request missing evidence',
      'Record the specialist opinion',
    ],
    available: false,
    unavailable_reason: 'Utrecht has no incoming referral yet.',
    recommended: false,
  },
]

const patients = [
  {
    case_id: 'CRC-EU-001',
    display_name: 'Giulia Moretti',
    age_band: '50-59',
    diagnosis: 'Metastatic colorectal cancer with liver-limited metastases',
    care_status: 'Referral decision due',
    current_plan: 'Review conversion therapy response and liver resectability.',
    last_updated: '23 September 2026',
    referral_candidate: true,
    synthetic: true,
  },
  {
    case_id: 'CRC-EU-014',
    display_name: 'Paolo Ricci',
    age_band: '60-69',
    diagnosis: 'Resected stage III colorectal cancer',
    care_status: 'Surveillance',
    current_plan: 'Continue local surveillance; no external referral is due.',
    last_updated: '22 September 2026',
    referral_candidate: false,
    synthetic: true,
  },
  {
    case_id: 'CRC-EU-022',
    display_name: 'Anna Greco',
    age_band: '40-49',
    diagnosis: 'Locally advanced rectal cancer',
    care_status: 'Local MDO review',
    current_plan: 'Complete local staging before considering an external referral.',
    last_updated: '21 September 2026',
    referral_candidate: false,
    synthetic: true,
  },
]

const initialSnapshot = {
  active_role: null,
  selected_patient_id: null,
  roles,
  patients,
  stages: [
    { id: 'patient', label: 'Patient', status: 'current', prerequisite: null },
    {
      id: 'local_data',
      label: 'Local data',
      status: 'locked',
      prerequisite: 'Select the referral patient first.',
    },
    {
      id: 'referral',
      label: 'Referral',
      status: 'locked',
      prerequisite: 'Complete the Milan data check first.',
    },
    {
      id: 'utrecht_review',
      label: 'Utrecht review',
      status: 'locked',
      prerequisite: 'Dr Bianchi must approve and send case version 1 first.',
    },
    {
      id: 'evidence_update',
      label: 'Evidence update',
      status: 'locked',
      prerequisite: 'Dr van Dijk must request the missing imaging first.',
    },
    {
      id: 'mdo_outcome',
      label: 'MDO outcome',
      status: 'locked',
      prerequisite: 'Dr Bianchi must approve case version 2 first.',
    },
  ],
  activity: [],
}

const milanSnapshot = {
  ...initialSnapshot,
  active_role: 'milan',
  activity: [
    {
      id: 'ACT-1',
      kind: 'workspace_opened',
      actor: 'Dr Luca Bianchi',
      institution: 'Istituto Nazionale dei Tumori, Milan',
      title: 'Opened the Milan workspace',
      detail: 'The synthetic role determines the available actions.',
      occurred_at: '2026-09-24T08:00:00Z',
    },
  ],
}

const selectedSnapshot = {
  ...milanSnapshot,
  selected_patient_id: 'CRC-EU-001',
  stages: [
    { id: 'patient', label: 'Patient', status: 'complete', prerequisite: null },
    { id: 'local_data', label: 'Local data', status: 'current', prerequisite: null },
    ...initialSnapshot.stages.slice(2),
  ],
  activity: [
    ...milanSnapshot.activity,
    {
      id: 'ACT-2',
      kind: 'patient_selected',
      actor: 'Dr Luca Bianchi',
      institution: 'Istituto Nazionale dei Tumori, Milan',
      title: 'Selected Giulia Moretti for referral preparation',
      detail: 'Review conversion therapy response and liver resectability.',
      occurred_at: '2026-09-24T08:01:00Z',
    },
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

describe('referral journey foundation', () => {
  it('starts with explicit Milan and Utrecht clinical roles', async () => {
    vi.stubGlobal('fetch', vi.fn(() => response(initialSnapshot)))

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Choose a clinical workspace' }))
      .toBeInTheDocument()
    expect(screen.getByText('Dr Luca Bianchi')).toBeInTheDocument()
    expect(screen.getByText('Dr Eva van Dijk')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Utrecht has no incoming referral yet.' }),
    ).toBeDisabled()
    expect(screen.getByText(/not a production sign-in system/i)).toBeInTheDocument()
  })

  it('opens the Milan worklist and keeps non-referral patients visible', async () => {
    const fetchMock = vi.fn((url: string, _options?: RequestInit) => {
      if (url === '/api/journey') return response(initialSnapshot)
      if (url === '/api/journey/actions') return response(milanSnapshot)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Open Milan workspace' }))

    expect(await screen.findByRole('heading', { name: 'Active patients' })).toBeInTheDocument()
    expect(screen.getByText('Giulia Moretti')).toBeInTheDocument()
    expect(screen.getByText('Paolo Ricci')).toBeInTheDocument()
    expect(screen.getByText('Anna Greco')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'No external referral due' })).toHaveLength(2)
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      type: 'enter_role',
      role: 'milan',
    })
  })

  it('selects the referral patient and advances to the local-data stage', async () => {
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url === '/api/journey') return response(initialSnapshot)
      if (url === '/api/journey/actions') {
        const body = JSON.parse(String(options?.body))
        return response(body.type === 'enter_role' ? milanSnapshot : selectedSnapshot)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Open Milan workspace' }))
    await user.click(
      await screen.findByRole('button', { name: 'Prepare specialist referral' }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Patient selected for referral preparation',
      }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Active patients' })).not.toBeInTheDocument()
    expect(screen.getByText('Selected Giulia Moretti for referral preparation')).toBeInTheDocument()
    expect(screen.getByText('Ready for local data check')).toBeInTheDocument()
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('Local data')
  })

  it('explains a locked future stage instead of appearing unresponsive', async () => {
    vi.stubGlobal('fetch', vi.fn(() => response(initialSnapshot)))
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: /MDO outcome/ }))

    expect(
      await screen.findByText('Dr Bianchi must approve case version 2 first.'),
    ).toBeInTheDocument()
  })

  it('shows restore failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => response({ detail: 'State store unavailable.' }, 503)),
    )

    render(<App />)

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('State store unavailable.'),
    )
  })
})
