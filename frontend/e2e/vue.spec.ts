import { test, expect } from '@playwright/test'

test('public portfolio displays the studio and supports navigation', async ({ page }) => {
  await page.goto('/new')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('From place to possibility.')
  await page.getByRole('link', { name: 'Explore our work', exact: true }).click()
  await expect(page).toHaveURL(/#projects$/)
  await expect(page.getByRole('heading', { name: 'Ideas, out in the world.' })).toBeVisible()
})

test('mobile navigation exposes the studio links without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 })
  await page.goto('/new')
  await page.getByRole('button', { name: 'Menu', exact: true }).click()
  await expect(page.getByRole('navigation', { name: 'Mobile navigation' })).toBeVisible()
  await page
    .getByRole('navigation', { name: 'Mobile navigation' })
    .getByRole('link', { name: 'Expertise' })
    .click()
  await expect(page).toHaveURL(/#services$/)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})
