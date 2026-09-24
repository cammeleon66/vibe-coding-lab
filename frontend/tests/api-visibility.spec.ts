import { expect, test } from '@playwright/test'

test('keeps federated API activity visible after source checks complete', async ({ page }) => {
  await page.request.post('/api/reset')
  await page.goto('/')
  await page.getByRole('button', { name: 'Open Milan workspace' }).click()
  await page.getByRole('button', { name: 'Prepare specialist referral' }).click()
  await expect(page.getByText('Local data check complete')).toBeVisible()
  await page.getByRole('button', { name: 'Confirm referral and destination' }).click()

  const apiActivity = page.getByRole('complementary', { name: 'API activity' })
  await expect(apiActivity).toBeVisible()
  await expect(
    apiActivity.getByText('POST /api/journey/actions', { exact: false }).first(),
  ).toBeVisible()
})
