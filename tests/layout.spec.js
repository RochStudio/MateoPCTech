const { test, expect } = require('@playwright/test');

for (const mode of ['dark', 'light']) {
  for (const width of [1050, 1051, 1052, 1360]) {
    test(`homepage video titles stay inside cards without images: ${mode} ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.emulateMedia({ colorScheme: mode });
      await page.route('**/*', route => {
        const request = route.request();
        return request.resourceType() === 'image' && new URL(request.url()).origin !== 'http://127.0.0.1:4173'
          ? route.abort() : route.continue();
      });
      await page.goto('/');
      await expect(page.locator('html')).toHaveAttribute('data-theme', mode);
      const cards = page.locator('.home .latest .video');
      await expect(cards).toHaveCount(2);
      for (const card of await cards.all()) {
        const title = card.locator('.info a');
        await expect(title).toBeVisible();
        const image = card.locator('img');
        await expect.poll(() => image.evaluate(img => img.complete && img.naturalWidth === 0)).toBe(true);
        // Measure before scrolling/focusing the link: that can pan an
        // overflow:hidden card and conceal the initial clipping regression.
        const bounds = await card.boundingBox();
        const link = await title.boundingBox();
        expect(link.width).toBeGreaterThan(0);
        expect(link.height).toBeGreaterThan(0);
        expect(link.x).toBeGreaterThanOrEqual(bounds.x);
        expect(link.y).toBeGreaterThanOrEqual(bounds.y);
        expect(link.x + link.width).toBeLessThanOrEqual(bounds.x + bounds.width);
        expect(link.y + link.height).toBeLessThanOrEqual(bounds.y + bounds.height);
      }
    });
  }
}

test('approved homepage is static, responsive, and styled in both modes', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1360, height: 1000 } });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:4173/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('More performance. Less guesswork.');
  await expect(page.getByRole('link', { name: 'Explore the videos' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Browse Roch Tools' })).toBeVisible();
  await expect(page.locator('.home-cards > .card')).toHaveCount(5);
  await expect(page.locator('.hero')).toHaveCSS('display', 'block');
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(16, 17, 18)');
  await page.setViewportSize({ width: 360, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(247, 247, 248)');
  await expect(page.locator('[data-theme-toggle]')).toBeHidden();
  await context.close();
});
