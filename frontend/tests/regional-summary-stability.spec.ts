import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  const accessCode = process.env.DEMO_ACCESS_CODE
  if (accessCode) {
    await page.goto('/')
    await page.getByLabel('Demo access code').fill(accessCode)
    await page.getByRole('button', { name: 'Open workspace' }).click()
    await expect(page).not.toHaveURL(/\/demo-access/)
  }
  const reset = await page.request.post('/api/reset')
  expect(reset.ok()).toBe(true)
})

test('patient-summary check keeps the regional screen usable', async ({ page }) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })

  await page.goto('/')
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/journey/actions') &&
      response.request().postData()?.includes('"query_regional_source"') === true,
  )
  await page.getByRole('button', { name: 'Check patient summary' }).click()
  const response = await responsePromise

  expect(response.status()).toBe(200)
  await expect(
    page.getByRole('heading', { name: 'Two Utrecht hospitals need one clear answer' }),
  ).toBeVisible()
  await expect(
    page
      .getByRole('article')
      .filter({ hasText: 'Patient-summary service' })
      .getByRole('code'),
  ).toHaveText('GET /fhir/Patient/CRC-NL-042/$summary')
  await expect(page.getByRole('button', { name: 'Check source imaging' })).toBeEnabled()
  expect(pageErrors).toEqual([])
  expect(consoleErrors).toEqual([])
})
