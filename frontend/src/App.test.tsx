import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { JourneySnapshot, SceneId } from './api/types'
import sceneSnapshots from './test/sceneSnapshots.json'

// Real backend snapshots, one per scene, captured with
// `CAPTURE_SNAPSHOTS=1 npx playwright test storyline.spec.ts --project=desktop-chromium`.
const snapshots = sceneSnapshots as unknown as Record<SceneId, JourneySnapshot>
const sceneOrder = snapshots.closing_outcome.storyline.scenes.map((scene) => scene.id)

interface FetchCall {
  url: string
  method: string
  body: unknown
}

function mockBackend(start: SceneId, options: { failActions?: string } = {}) {
  let current = start
  const calls: FetchCall[] = []
  const json = (payload: unknown, status = 200) =>
    new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })

  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = init?.method ?? 'GET'
      const body = init?.body ? (JSON.parse(String(init.body)) as unknown) : undefined
      calls.push({ url, method, body })
      if (url === '/api/journey') return json(snapshots[current])
      if (url === '/api/reset') {
        current = 'local_problem'
        return new Response(null, { status: 204 })
      }
      if (url === '/api/journey/actions') {
        if (options.failActions) return json({ detail: options.failActions }, 409)
        const action = body as { type: string; from_scene?: SceneId }
        if (action.type === 'advance_scene') {
          current = sceneOrder[sceneOrder.indexOf(action.from_scene ?? current) + 1]
        }
        return json(snapshots[current])
      }
      return json({ detail: `Unexpected ${method} ${url}` }, 404)
    }),
  )
  return calls
}

async function expectScene(id: SceneId) {
  const scene = snapshots[id].storyline.scenes.find((item) => item.id === id)!
  expect(await screen.findByRole('heading', { level: 1, name: scene.title })).toBeInTheDocument()
  expect(screen.getByText(new RegExp(`Step ${sceneOrder.indexOf(id) + 1} of 14`))).toBeInTheDocument()
}

beforeEach(() => {
  window.sessionStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('storyline renderer', () => {
  it('has a snapshot for all 14 scenes', () => {
    expect(sceneOrder).toHaveLength(14)
    for (const id of sceneOrder) expect(snapshots[id].storyline.current_scene).toBe(id)
  })

  it.each(sceneOrder.slice(0, -1))('renders %s and advances with the backend label', async (id) => {
    const calls = mockBackend(id)
    const user = userEvent.setup()
    render(<App />)
    await expectScene(id)

    const label = snapshots[id].storyline.advance_label!
    const toolbar = screen.getByRole('contentinfo')
    await user.click(within(toolbar).getByRole('button', { name: label }))

    const next = sceneOrder[sceneOrder.indexOf(id) + 1]
    await expectScene(next)
    expect(calls).toContainEqual({
      url: '/api/journey/actions',
      method: 'POST',
      body: { type: 'advance_scene', from_scene: id },
    })
  })

  it('shows the closing outcome without an advance toolbar', async () => {
    mockBackend('closing_outcome')
    render(<App />)
    await expectScene('closing_outcome')
    expect(screen.getByText(/29 September 2026 at 14:00 CEST/)).toBeInTheDocument()
    expect(screen.queryByRole('contentinfo')).not.toBeInTheDocument()
  })

  it('shows the handover banner when responsibility changes', async () => {
    mockBackend('local_approval')
    render(<App />)
    await expectScene('local_approval')
    expect(screen.getByRole('note', { name: 'Handover' })).toHaveTextContent('Dr Sophie Bakker')
  })

  it('opens completed steps read-only and returns to the current step', async () => {
    mockBackend('closing_outcome')
    const user = userEvent.setup()
    render(<App />)
    await expectScene('closing_outcome')

    const nav = screen.getByRole('navigation', { name: 'Workflow' })
    await user.click(within(nav).getByRole('button', { name: /Stadshaven decides/ }))
    expect(screen.getByRole('heading', { level: 1, name: 'Stadshaven decides what may cross' })).toBeInTheDocument()
    expect(screen.getByText('Read-only view of a completed step.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Return to step 14' }))
    await expectScene('closing_outcome')
  })

  it('does not let the user skip ahead to future steps', async () => {
    mockBackend('local_problem')
    render(<App />)
    await expectScene('local_problem')
    const nav = screen.getByRole('navigation', { name: 'Workflow' })
    expect(within(nav).getByRole('button', { name: /The loop is closed/ })).toBeDisabled()
  })

  it('surfaces a backend error and stays on the current step', async () => {
    mockBackend('local_problem', { failActions: 'The storyline has moved on.' })
    const user = userEvent.setup()
    render(<App />)
    await expectScene('local_problem')
    await user.click(screen.getByRole('button', { name: 'Ask the exchange agent to find it' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The storyline has moved on.')
    await expectScene('local_problem')
  })

  it('resets the story to step 1', async () => {
    const calls = mockBackend('utrecht_review')
    const user = userEvent.setup()
    render(<App />)
    await expectScene('utrecht_review')
    await user.click(screen.getByRole('button', { name: 'Reset' }))
    await expectScene('local_problem')
    await waitFor(() =>
      expect(screen.getByText('The synthetic story has been reset to the beginning.')).toBeInTheDocument(),
    )
    expect(calls.some((call) => call.url === '/api/reset' && call.method === 'POST')).toBe(true)
  })
})
