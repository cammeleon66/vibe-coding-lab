import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { writeFileSync } from 'node:fs'

const live = Boolean(process.env.DEMO_ACCESS_CODE)

// CAPTURE_SNAPSHOTS=1 records the final snapshot of every scene for the vitest fixtures.
function recordSceneSnapshots(page: Page) {
  const byScene: Record<string, unknown> = {}
  page.on('response', async (response) => {
    if (!/\/api\/journey(\/actions)?$/.test(response.url()) || !response.ok()) return
    const snapshot = (await response.json()) as { storyline: { current_scene: string } }
    byScene[snapshot.storyline.current_scene] = snapshot
  })
  return () =>
    writeFileSync('src/test/sceneSnapshots.json', `${JSON.stringify(byScene, null, 1)}\n`)
}

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const violations = results.violations
    .filter((item) => ['critical', 'serious'].includes(item.impact ?? ''))
    .map((item) => `${item.id}: ${item.nodes.map((node) => node.target.join(' ')).join(', ')}`)
  expect(violations).toEqual([])
}

async function capture(page: Page, name: string, project: string) {
  await page.screenshot({
    path: `../docs/demo/evidence/${live ? 'live-' : ''}${name}-${project}.png`,
    fullPage: true,
  })
}

async function onStep(page: Page, step: number, title: string) {
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
  await expect(page.getByText(`Step ${step} of 14`)).toBeVisible()
}

async function advance(page: Page, label: string) {
  const button = page.locator('.ehr-toolbar').getByRole('button', { name: label })
  await expect(button).toBeEnabled({ timeout: 15_000 })
  await button.click()
}

test.beforeEach(async ({ page }) => {
  const accessCode = process.env.DEMO_ACCESS_CODE
  if (accessCode) {
    await page.goto('/')
    await page.getByLabel('Demo access code').fill(accessCode)
    await page.getByRole('button', { name: 'Open workspace' }).click()
    await expect(page).not.toHaveURL(/\/demo-access/)
  }
  const response = await page.request.post('/api/reset')
  expect(response.ok()).toBe(true)
})

test('walks the full storyline, one screen per step', async ({ page }, testInfo) => {
  test.setTimeout(120_000)
  const project = testInfo.project.name
  const saveSnapshots =
    process.env.CAPTURE_SNAPSHOTS && project === 'desktop-chromium' ? recordSceneSnapshots(page) : null
  await page.goto('/')

  // Chapter 1: two hospitals in Utrecht.
  await onStep(page, 1, 'The MRI is at the hospital around the corner')
  await expect(page.getByLabel('Patient context')).toContainText('Sanne de Vries')
  await expectAccessible(page)
  await capture(page, '01-local-problem', project)
  await advance(page, 'Ask the exchange agent to find it')

  await onStep(page, 2, "The agent asks Stadshaven's own systems")
  await expect(page.getByText('GET /dicom/studies?patient=CRC-NL-042&modality=MR').first()).toBeVisible()
  await expect(page.getByText(/MRI report of 24 September 2026 located/)).toBeVisible()
  await capture(page, '02-local-search', project)
  await advance(page, 'Send the sharing request to Dr Noor Jansen')

  await onStep(page, 3, 'Stadshaven decides what may cross')
  await expect(page.getByRole('note', { name: 'Handover' })).toContainText('Dr Sophie Bakker')
  await expect(page.getByText('Original MRI images')).toBeVisible()
  await expect(page.locator('.ehr-toolbar')).toContainText('Dr Noor Jansen must approve')
  await page.getByRole('button', { name: 'Approve release' }).click()
  await expect(page.getByText(/Released items: 2/)).toBeVisible()
  await expectAccessible(page)
  await capture(page, '03-local-approval', project)
  await advance(page, 'Show what Utrecht receives')

  await onStep(page, 4, "Today's treatment review can go ahead")
  await expect(page.getByText(/largest 2.2 cm, previously 3.1 cm/)).toBeVisible()
  await capture(page, '04-local-result', project)
  await advance(page, 'Now scale the same pattern')

  // Chapter 2: the same pattern across Europe.
  await onStep(page, 5, 'From Utrecht to a European network')
  await expect(page.getByText('Connected centres (2)')).toBeVisible()
  for (const [scope, count] of [
    ['Netherlands', 7],
    ['Germany and Italy', 13],
    ['Europe', 16],
  ] as const) {
    await page.getByRole('button', { name: scope, exact: true }).click()
    await expect(page.getByText(`Connected centres (${count})`)).toBeVisible()
  }
  await expect(page.getByText('Dr Katrin Weber')).toBeVisible()
  await expect(page.getByText('Dr Chiara Rossi')).toBeVisible()
  await expectAccessible(page)
  await capture(page, '05-scale-network', project)
  await advance(page, 'Follow one referral from Milan to Utrecht')

  // Chapter 3: Milan to Utrecht.
  await onStep(page, 6, 'Milan needs a second opinion')
  await page.getByRole('button', { name: "Open Giulia's case" }).click()
  await expect(page.getByLabel('Patient context')).toContainText('Giulia Moretti')
  await expectAccessible(page)
  await capture(page, '06-cross-patient', project)
  await advance(page, "Let the agent check Milan's own sources")

  await onStep(page, 7, 'The agent checks what Milan already holds')
  await expect(page.getByText('Missing evidence (included in referral as known gaps)')).toBeVisible({
    timeout: 15_000,
  })
  await capture(page, '07-cross-sources', project)
  await advance(page, 'Frame the clinical question')

  await onStep(page, 8, 'Dr Bianchi frames the question')
  await page.getByRole('button', { name: 'Confirm the question' }).click()
  await advance(page, 'Find the right expert centre')

  await onStep(page, 9, 'Choosing the expert centre')
  await page.getByRole('button', { name: 'Choose Dr Eva van Dijk' }).click()
  await expectAccessible(page)
  await capture(page, '09-cross-destination', project)
  await advance(page, 'Prepare the referral package')

  await onStep(page, 10, 'Approve exactly what crosses the border')
  await page.getByRole('button', { name: 'Approve and send case version 1' }).click({ timeout: 15_000 })
  await expect(page.getByText(/Case version 1 approved by Dr Luca Bianchi/)).toBeVisible()
  await expectAccessible(page)
  await capture(page, '10-cross-package', project)
  await advance(page, 'Hand over to Dr Eva van Dijk in Utrecht')

  await onStep(page, 11, 'Utrecht reviews and asks for imaging')
  await expect(page.getByLabel('Patient context')).toContainText('Giulia Moretti')
  await page.getByRole('button', { name: 'Acknowledge case version 1' }).click()
  await page.getByRole('button', { name: 'Record provisional opinion' }).click()
  await page.getByRole('button', { name: 'Send the imaging request to Milan' }).click()
  await expectAccessible(page)
  await capture(page, '11-utrecht-review', project)
  await advance(page, 'Hand back to Dr Luca Bianchi in Milan')

  await onStep(page, 12, 'New imaging arrives in Milan')
  await page.getByRole('button', { name: 'Simulate PACS arrival' }).click()
  await expect(page.getByRole('region', { name: 'What changed from version 1 to version 2' })).toBeVisible({
    timeout: 20_000,
  })
  await page.getByRole('button', { name: 'Approve and send case version 2' }).click()
  await expectAccessible(page)
  await capture(page, '12-milan-update', project)
  await advance(page, 'Hand over to Dr Eva van Dijk in Utrecht')

  await onStep(page, 13, 'Utrecht completes the specialist review')
  await page.getByRole('button', { name: 'Acknowledge case version 2' }).click()
  await page.getByRole('button', { name: 'Record specialist opinion' }).click()
  await page.getByRole('button', { name: 'Accept into the MDO' }).click()
  await advance(page, 'Return the outcome to Milan')

  await onStep(page, 14, 'The loop is closed')
  await expect(page.getByText('29 September 2026 at 14:00 CEST')).toBeVisible()
  await expect(page.locator('.ehr-toolbar')).toHaveCount(0)
  await expectAccessible(page)
  await capture(page, '14-closing-outcome', project)
  saveSnapshots?.()

  // Completed steps stay reviewable, read-only.
  await page.getByRole('navigation', { name: 'Workflow' }).getByRole('button', { name: /Stadshaven decides/ }).click()
  await expect(page.getByText('Read-only view of a completed step.')).toBeVisible()
  await page.getByRole('button', { name: 'Return to step 14' }).click()
  await onStep(page, 14, 'The loop is closed')
})

test('shows every hospital system request in the assistant pane and audit log', async ({ page }) => {
  await page.goto('/')
  await advance(page, 'Ask the exchange agent to find it')
  const assistant = page.getByRole('complementary', { name: 'Utrecht exchange agent' })
  await expect(assistant.getByText('GET /fhir/Patient/CRC-NL-042/$summary')).toBeVisible()
  await expect(assistant.getByText('GET /dicom/studies?patient=CRC-NL-042&modality=MR')).toBeVisible()

  await page.getByRole('button', { name: /Audit log \(2\)/ }).click()
  const drawer = page.getByRole('dialog', { name: 'Audit log' })
  await expect(drawer.getByText('Stadshaven patient-summary service')).toBeVisible()
  await expect(drawer.getByText('Stadshaven imaging archive')).toBeVisible()
  await expectAccessible(page)
  await page.keyboard.press('Escape')
  await expect(drawer).toHaveCount(0)
})

test('restores the current step after a reload without repeating agent work', async ({ page }) => {
  await page.goto('/')
  await advance(page, 'Ask the exchange agent to find it')
  await expect(page.getByText(/MRI report of 24 September 2026 located/)).toBeVisible()
  await page.reload()
  await onStep(page, 2, "The agent asks Stadshaven's own systems")
  await expect(page.getByRole('button', { name: 'Resume assistant tasks' })).toHaveCount(0)
  await page.getByRole('button', { name: /Audit log \(2\)/ }).click()
  await expect(page.getByRole('dialog', { name: 'Audit log' }).locator('.call-list li')).toHaveCount(2)
})
