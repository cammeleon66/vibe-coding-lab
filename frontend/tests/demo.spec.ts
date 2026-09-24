import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

async function reset(page: import('@playwright/test').Page) {
  const response = await page.request.post('/api/reset')
  expect(response.ok()).toBe(true)
}

async function expectNoSeriousAccessibilityViolations(
  page: import('@playwright/test').Page,
) {
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

test('prepares and approves the Milan referral package', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Choose a clinical workspace' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Utrecht has no incoming referral yet.' }))
    .toBeDisabled()

  await page.getByRole('button', { name: 'Open Milan workspace' }).click()
  await expect(page.getByRole('heading', { name: 'Active patients' })).toBeVisible()
  await expect(page.getByText('Giulia Moretti')).toBeVisible()
  await expect(page.getByText('Paolo Ricci')).toBeVisible()
  await expect(page.getByText('Anna Greco')).toBeVisible()

  await page.getByRole('button', { name: 'Prepare specialist referral' }).click()
  await expect(
    page.getByRole('heading', { name: 'Check available data in Milan' }),
  ).toBeVisible()
  await expect(page.getByText('Local data check complete')).toBeVisible()
  await expect(page.getByText('Original baseline liver CT')).toBeVisible()
  await expect(page.getByText('Selected Giulia Moretti for referral preparation')).toBeVisible()
  await expect(
    page
      .getByRole('list', { name: 'Referral stages' })
      .getByRole('listitem')
      .filter({ hasText: 'Referral' }),
  ).toHaveAttribute('aria-current', 'step')

  await page.getByRole('button', { name: 'Confirm referral and destination' }).click()
  await expect(
    page.getByRole('heading', { name: 'Prepare referral for specialist review' }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Confirm clinical question' }).click()
  await page.getByRole('button', { name: 'Query expert directory' }).click()
  await expect(page.getByRole('heading', { name: 'UMC Utrecht' })).toBeVisible()
  await page.getByRole('button', { name: 'Select UMC Utrecht' }).click()
  await page.getByRole('button', { name: 'Query Utrecht requirements' }).click()
  await expect(page.getByText('Restaging liver MRI')).toBeVisible()
  await page.getByRole('button', { name: 'Prepare case version 1' }).click()
  await expect(page.getByRole('heading', { name: 'Case version 1' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Shared after approval' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Remains in Milan' })).toBeVisible()
  await page.getByRole('button', { name: 'Approve and send case version 1' }).click()

  await expect(page.getByText('Case version 1 approved and sent')).toBeVisible()
  await expect(
    page
      .getByRole('list', { name: 'Referral stages' })
      .getByRole('listitem')
      .filter({ hasText: 'Utrecht review' }),
  ).toHaveAttribute('aria-current', 'step')

  await page.getByRole('button', { name: 'Continue as Dr Eva van Dijk' }).click()
  await expect(page.getByRole('heading', { name: 'Review incoming referral' })).toBeVisible()
  await expect(page.getByText("Dr Bianchi's referral assessment")).toBeVisible()
  await page.getByRole('button', { name: 'Acknowledge case version 1' }).click()
  await page.getByRole('button', { name: 'Record provisional opinion' }).click()
  await expect(page.getByText('Provisional opinion recorded')).toBeVisible()
  await page.getByRole('button', { name: 'Request missing imaging' }).click()
  await expect(page.getByText('Imaging request sent to Milan')).toBeVisible()
  await expect(
    page
      .getByRole('list', { name: 'Referral stages' })
      .getByRole('listitem')
      .filter({ hasText: 'Evidence update' }),
  ).toHaveAttribute('aria-current', 'step')

  await page.reload()
  await expect(page.getByText('Imaging request sent to Milan')).toBeVisible()
})

test('supports keyboard navigation and has no serious accessibility violations', async ({
  page,
}) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Choose a clinical workspace' })).toBeVisible()

  await page.getByRole('button', { name: 'Clinical roles' }).focus()
  await expect(page.getByRole('button', { name: 'Clinical roles' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Reset' })).toBeFocused()

  await expectNoSeriousAccessibilityViolations(page)
  await page.getByRole('button', { name: 'Open Milan workspace' }).click()
  await expectNoSeriousAccessibilityViolations(page)
})
