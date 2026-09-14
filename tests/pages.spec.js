const { test, expect } = require('@playwright/test');

const pages = [
  ['/youtube', 'Mateo PC Tech', '.video-grid', 4],
  ['/roch-tools', 'Roch Tools', '.catalog > .card', 5],
  ['/skool', 'Mateo PC Tech Community', '.community-card .benefits', 1],
  ['/discord', 'Discord', '.discord-mark', 1],
  ['/parts', 'Recommended Parts', '.board-groups > .board-group', 3],
  ['/404', '404 — Page Not Found', '.not-found .card', 1],
];
for (const [url, title, selector, count] of pages) {
  test(`${url} has the approved page structure and a meaningful main heading`, async ({ page }) => {
    await page.goto(url);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(title);
    await expect(page.locator(selector)).toHaveCount(count);
    await expect(page.getByRole('button', { name: 'Switch to light mode' })).toBeVisible();
  });
}
