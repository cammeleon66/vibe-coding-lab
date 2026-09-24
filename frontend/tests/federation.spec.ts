import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const live = Boolean(process.env.DEMO_ACCESS_CODE)
const UNAVAILABLE = 'Heidelberg unavailable — federated result incomplete'

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  const violations = results.violations
    .filter((item) => ['critical', 'serious'].includes(item.impact ?? ''))
    .map((item) => `${item.id}: ${item.nodes.map((node) => node.target.join(' ')).join(', ')}`)
  expect(violations).toEqual([])
}

async function capture(page: Page, name: string, project: string) {
  if (process.env.CAPTURE_EVIDENCE)
    await page.screenshot({ path: `../docs/demo/evidence/${live ? 'live-' : ''}${name}-${project}.png`, fullPage: true })
}

async function switchRole(page: Page, name: string) {
  await page.getByRole('navigation', { name: 'Demo role' }).getByRole('button', { name: new RegExp(name) }).click()
}

async function sendCase(page: Page) {
  await switchRole(page, 'NL oncologist')
  await page.getByRole('button', { name: /Maria Janssen/ }).click()
  await page.getByRole('button', { name: 'Request European peer review' }).click()
  await page.getByRole('button', { name: 'Search catalogue' }).click()
  await page.getByRole('button', { name: 'Select Heidelberg' }).click()
  await page.getByRole('button', { name: 'Send secure case' }).click()
}

test.beforeEach(async ({ page }) => {
  const accessCode = process.env.DEMO_ACCESS_CODE
  if (accessCode) {
    await page.goto('/')
    await page.getByLabel('Demo access code').fill(accessCode)
    await page.getByRole('button', { name: 'Open workspace' }).click()
    await expect(page).not.toHaveURL(/\/demo-access/)
  }
  expect((await page.request.post('/api/reset')).ok()).toBe(true)
  await page.goto('/#nl')
})

test('walks the federated network by switching roles', async ({ page }, testInfo) => {
  test.setTimeout(120_000)
  const project = testInfo.project.name

  await expect(page.getByRole('status').filter({ hasText: 'UMC UTRECHT' })).toBeVisible()
  await page.getByRole('button', { name: /Maria Janssen/ }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Maria Janssen' })).toBeVisible()
  await expectAccessible(page)
  await capture(page, '01-nl-chart', project)

  await sendCase(page)
  await expect(page.getByText(/Secure case delivered to Dr Anna Müller/)).toBeVisible()
  await capture(page, '02-nl-sent', project)

  await switchRole(page, 'Heidelberg expert')
  await expect(page.getByRole('status').filter({ hasText: 'HEIDELBERG' })).toBeVisible()
  await page.getByRole('button', { name: /UMC Utrecht · case-/ }).click()
  await expect(page.getByRole('heading', { name: 'The question from the UMC Utrecht MDO' })).toBeVisible()
  await expect(page.locator('main')).not.toContainText('Maria')
  await page.getByRole('button', { name: 'Compare with our patients' }).click()
  await expect(page.getByText(/38\s+matching locally/)).toBeVisible()
  await page.getByRole('row', { name: /KRAS G12C inhibitor combination/ }).getByRole('button', { name: 'Cite' }).click()
  await expect(page.locator('.cited')).toContainText('response 41%')
  await expectAccessible(page)
  await capture(page, '03-de-evidence', project)
  await page.getByRole('button', { name: 'Send opinion to UMC Utrecht' }).click()
  await expect(page.getByText(/Opinion sent to UMC Utrecht/)).toBeVisible()

  await switchRole(page, 'NL oncologist')
  await page.getByRole('button', { name: /Maria Janssen/ }).click()
  await expect(page.getByRole('region', { name: 'European peer review received' })).toBeVisible()
  await expect(page.getByText(/Recommendation: KRAS G12C inhibitor combination/)).toBeVisible()
  await capture(page, '04-nl-opinion', project)

  await switchRole(page, 'Control room')
  await expect(page.getByRole('heading', { name: 'Federation control room' })).toBeVisible()
  await page.getByRole('button', { name: /Signature verified.*case case-/ }).click()
  await page.getByRole('button', { name: 'Retrieve full package from UMC Utrecht' }).click()
  await expect(page.getByText(/SHA-256 matches the hub audit event/)).toBeVisible()
  await expectAccessible(page)
  await capture(page, '05-control-room', project)

  await switchRole(page, 'Researcher')
  await page.getByRole('button', { name: 'Run federated query' }).click()
  await expect(page.getByRole('region', { name: 'Federated result' })).toContainText('records transferred')
  await expect(page.getByRole('table', { name: 'Pooled outcomes per treatment' })).toBeVisible()
  await expect(page.getByText('Data stays. Insights travel.')).toBeVisible()
  await expectAccessible(page)
  await capture(page, '06-research', project)

  await expect(page.getByRole('button', { name: /Presenter checklist 6\/7/ })).toBeVisible({ timeout: 10_000 })
})

test('taking Heidelberg offline fails for real and recovers', async ({ page }, testInfo) => {
  test.setTimeout(120_000)
  await switchRole(page, 'Control room')
  await page.getByRole('button', { name: /Take Universitätsklinikum Heidelberg offline/ }).click()
  await expect(page.getByRole('button', { name: /Bring Universitätsklinikum Heidelberg online/ })).toBeVisible({
    timeout: 15_000,
  })
  await expect(page.locator('.site-card.down')).toContainText('Unavailable')

  await sendCase(page)
  await expect(page.getByRole('alert').filter({ hasText: UNAVAILABLE })).toBeVisible()
  await switchRole(page, 'Heidelberg expert')
  await expect(page.getByRole('alert').filter({ hasText: UNAVAILABLE })).toBeVisible({ timeout: 10_000 })
  await switchRole(page, 'Researcher')
  await page.getByRole('button', { name: 'Run federated query' }).click()
  await expect(page.getByRole('alert').filter({ hasText: UNAVAILABLE })).toBeVisible()
  await capture(page, '07-disconnect', testInfo.project.name)

  await switchRole(page, 'Control room')
  await page.getByRole('button', { name: /Bring Universitätsklinikum Heidelberg online/ }).click()
  await expect(page.getByRole('button', { name: /Take Universitätsklinikum Heidelberg offline/ })).toBeVisible({
    timeout: 15_000,
  })
  await switchRole(page, 'NL oncologist')
  await page.getByRole('button', { name: /Maria Janssen/ }).click()
  await page.getByRole('button', { name: 'Resend secure case' }).click()
  await expect(page.getByText(/Secure case delivered to Dr Anna Müller/)).toBeVisible()
})
