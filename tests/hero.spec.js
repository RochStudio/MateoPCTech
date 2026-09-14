const { test, expect } = require('@playwright/test');

for (const mode of ['dark', 'light']) {
  for (const width of [320, 1360]) {
    test(`simplified welcome and useful hero panel: ${mode} ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.emulateMedia({ colorScheme: mode });
      await page.goto('/');
      await expect(page.locator('.hero-copy > .eyebrow')).toHaveText('Welcome');
      await expect(page.locator('.hardware-art, .chip')).toHaveCount(0);
      const panel = page.getByRole('region', { name: 'Quick links' });
      await expect(panel).toBeVisible();
      await expect(panel.locator('.eyebrow, h2')).toHaveCount(0);
      const links = panel.getByRole('link');
      await expect(links).toHaveCount(3);
      await expect(links.nth(0)).toHaveAttribute('href', '/youtube');
      await expect(links.nth(1)).toHaveAttribute('href', '/roch-tools');
      await expect(links.nth(2)).toHaveAttribute('href', 'https://www.youtube.com/@MateoBenchmarking');
      const bounds = await panel.boundingBox();
      for (const link of await links.all()) {
        await expect(link).toBeVisible();
        const box = await link.boundingBox();
        expect(box.height).toBeGreaterThanOrEqual(44);
        expect(box.x).toBeGreaterThanOrEqual(bounds.x);
        expect(box.x + box.width).toBeLessThanOrEqual(bounds.x + bounds.width);
      }
      await links.nth(0).focus();
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL('/youtube');
      await expect(page.locator('html')).toHaveAttribute('data-theme', mode);
    });
  }
}
