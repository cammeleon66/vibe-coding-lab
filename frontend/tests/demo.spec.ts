import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import path from 'node:path'

const evidenceDirectory = path.resolve('..', 'docs', 'demo', 'evidence')
const presenterBeatSeconds = [8, 14, 14, 18, 24, 12]

async function reset(page: Page) {
  const response = await page.request.post('/api/reset')
  expect(response.ok()).toBe(true)
}

async function openReferral(page: Page) {
  await page.getByRole('button', { name: 'Find European expertise' }).click()
  await expect(page.getByText('Rehearsal reset to a clean synthetic case.')).toHaveCount(0)
  await expect(page.getByText('Three possible rooms. One strongest fit.')).toBeVisible()
  await page.getByRole('button', { name: 'Request specialist collaboration' }).click()
  await expect(page.getByText('Collaboration workspace opened')).toBeVisible()
}

async function prepareCase(page: Page) {
  await openReferral(page)
  await page.getByRole('button', { name: 'Prepare clinical workspace' }).click()
  await expect(page.getByText('Evidence together. Origins intact.')).toBeVisible()
}

async function updateCase(page: Page) {
  await prepareCase(page)
  await page.getByRole('button', { name: 'Receive late imaging evidence' }).click()
  await expect(page.getByText('What changed from case v1 to v2')).toBeVisible()
}

async function completeClinicalPath(page: Page) {
  await updateCase(page)
  const review = page.getByRole('region', { name: 'Human review and MDO handoff' })
  await review.getByLabel('Considered human opinion').fill(
    'The source-linked imaging update warrants multidisciplinary reassessment; no automated resectability conclusion is recorded.',
  )
  const conditions = review.locator('.review-condition')
  for (let index = 0; index < (await conditions.count()); index += 1) {
    const condition = conditions.nth(index)
    await condition.getByRole('checkbox').check()
    await condition.getByLabel('Resolution note').fill(
      'Reviewed explicitly for this synthetic rehearsal and carried into the MDO record.',
    )
  }
  await review.getByRole('button', { name: 'Save opinion for case v2' }).click()
  await expect(review.getByText('Ready to create handoff')).toBeVisible()
  await review.getByRole('button', { name: 'Create MDO handoff manifest' }).click()
  await expect(page.getByText('Clinical presenter path complete')).toBeVisible()
}

async function expectNoSeriousAccessibilityViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const violations = results.violations.filter((item) =>
    ['critical', 'serious'].includes(item.impact ?? ''),
  )
  expect(violations).toEqual([])
}

test.beforeEach(async ({ page }) => {
  await reset(page)
})

test('rehearses the complete presenter path from clean state in under 120 seconds', async ({
  page,
}, testInfo) => {
  const plannedPresenterSeconds = presenterBeatSeconds.reduce((total, beat) => total + beat, 0)
  expect(plannedPresenterSeconds).toBeGreaterThanOrEqual(60)
  expect(plannedPresenterSeconds).toBeLessThanOrEqual(120)
  const startedAt = Date.now()
  await page.goto('/')
  await expect(page.getByText('Find the right room before moving the case.')).toBeVisible()

  await page.getByRole('button', { name: 'Preflight' }).click()
  await expect(page.getByText('Local rehearsal ready')).toBeVisible()
  await expect(page.getByText('All required local checks passed.')).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).click()
  await page.getByRole('button', { name: 'Reset' }).click()
  await expect(page.getByRole('status')).toContainText(
    'Rehearsal reset to a clean synthetic case',
  )

  await completeClinicalPath(page)

  const elapsedSeconds = (Date.now() - startedAt) / 1000
  expect(elapsedSeconds).toBeLessThan(120)
  expect(elapsedSeconds).toBeGreaterThan(0)
  await expect(page.getByRole('link', { name: 'Launch separate MDO demonstration' })).toHaveAttribute(
    'href',
    /case_id=CRC-EU-001/,
  )
  await page.getByText('Clinical presenter path complete').scrollIntoViewIfNeeded()
  await page.screenshot({
    path: path.join(evidenceDirectory, `completed-${testInfo.project.name}.jpg`),
    type: 'jpeg',
    quality: 76,
  })
})

test('supports keyboard navigation, source-dialog escape, and automated accessibility', async ({
  page,
}) => {
  await page.goto('/')
  await expect(page.getByText('Find the right room before moving the case.')).toBeVisible()
  await page.getByLabel('Clinical question').fill('A presenter edit that must not survive reset.')
  await page.getByLabel('Urgency').selectOption('urgent')
  await page.getByRole('button', { name: 'Reset' }).click()
  await expect(page.getByRole('status')).toContainText('Rehearsal reset to a clean synthetic case')
  await expect(page.getByLabel('Clinical question')).toHaveValue(
    'Conversion therapy and liver-metastasis resectability',
  )
  await expect(page.getByLabel('Urgency')).toHaveValue('expedited')
  await expectNoSeriousAccessibilityViolations(page)

  await page.getByRole('link', { name: 'European Oncology Exchange' }).focus()
  await expect(page.getByRole('link', { name: 'European Oncology Exchange' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Preflight' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByLabel('Presenter preflight')).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).click()

  await prepareCase(page)
  const sourceTrigger = page
    .getByRole('button', { name: /Istituto Nazionale dei Tumori, Milan · CDA\/XML/ })
    .first()
  await sourceTrigger.click()
  await expect(page.getByRole('dialog', { name: 'Source evidence inspector' })).toBeVisible()
  await expect(page.locator('main')).toHaveAttribute('inert', '')
  await expect(page.getByRole('button', { name: 'Close source inspector' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Close source inspector' })).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(page.getByRole('button', { name: 'Close source inspector' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: 'Source evidence inspector' })).toBeHidden()
  await expect(sourceTrigger).toBeFocused()
  await expectNoSeriousAccessibilityViolations(page)
})

test.describe('visual state evidence', () => {
  test('captures loading, empty, error, update, and completed states', async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name.includes('mobile'), 'Desktop captures hold the state evidence set.')
    await page.route('**/api/referrals/current', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 900))
      await route.continue()
    })
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('Restoring deterministic rehearsal')).toBeVisible()
    await page.screenshot({
      path: path.join(evidenceDirectory, 'state-loading.jpg'),
      type: 'jpeg',
      quality: 76,
    })
    await expect(page.getByText('Find the right room before moving the case.')).toBeVisible()
    await page.unroute('**/api/referrals/current')

    await page.route('**/api/expert-matches', async (route) => {
      const body = route.request().postDataJSON()
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ need: body, matches: [], limitations: ['Synthetic bounded directory.'] }),
      })
    })
    await page.getByRole('button', { name: 'Find European expertise' }).click()
    await expect(page.getByText('No suitable synthetic centre found')).toBeVisible()
    await page.screenshot({
      path: path.join(evidenceDirectory, 'state-empty.jpg'),
      type: 'jpeg',
      quality: 76,
    })
    await page.unroute('**/api/expert-matches')

    await page.route('**/api/expert-matches', (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Synthetic directory unavailable for rehearsal.' }),
      }),
    )
    await page.getByRole('button', { name: 'Find European expertise' }).click()
    await expect(page.getByRole('alert')).toContainText('Synthetic directory unavailable')
    await page.screenshot({
      path: path.join(evidenceDirectory, 'state-error.jpg'),
      type: 'jpeg',
      quality: 76,
    })
    await page.unroute('**/api/expert-matches')

    await reset(page)
    await page.reload()
    await updateCase(page)
    await page.getByText('What changed from case v1 to v2').scrollIntoViewIfNeeded()
    await page.screenshot({
      path: path.join(evidenceDirectory, 'state-update.jpg'),
      type: 'jpeg',
      quality: 76,
    })

    const review = page.getByRole('region', { name: 'Human review and MDO handoff' })
    await review.getByLabel('Considered human opinion').fill(
      'Multidisciplinary reassessment is required; this remains a human conclusion.',
    )
    const conditions = review.locator('.review-condition')
    for (let index = 0; index < (await conditions.count()); index += 1) {
      const condition = conditions.nth(index)
      await condition.getByRole('checkbox').check()
      await condition.getByLabel('Resolution note').fill('Explicitly reviewed in rehearsal.')
    }
    await review.getByRole('button', { name: 'Save opinion for case v2' }).click()
    await review.getByRole('button', { name: 'Create MDO handoff manifest' }).click()
    await page.getByText('Clinical presenter path complete').scrollIntoViewIfNeeded()
    await page.screenshot({
      path: path.join(evidenceDirectory, 'state-completed.jpg'),
      type: 'jpeg',
      quality: 76,
    })
  })
})
