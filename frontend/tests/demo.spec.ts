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

test('enters the Milan workspace and selects the referral patient', async ({ page }) => {
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
