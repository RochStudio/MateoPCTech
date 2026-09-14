const { test, expect } = require('@playwright/test');

for (const mode of ['dark', 'light']) {
  for (const width of [320, 1360]) {
    test(`welcome without quick-links panel: ${mode} ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.emulateMedia({ colorScheme: mode });
      await page.goto('/');
      const hero = page.locator('.hero');
      await expect(page.locator('.hero-copy > .eyebrow')).toHaveText('Welcome');
      await expect(page.locator('.hero-toolkit, .toolkit-links, .hardware-art, .chip')).toHaveCount(0);
      await expect(hero.locator(':scope > *')).toHaveCount(1);
      await expect(hero.getByRole('heading', { level: 1 })).toBeVisible();
      const links = hero.getByRole('link');
      await expect(links).toHaveCount(2);
      await expect(links.nth(0)).toHaveAttribute('href', '/youtube');
      await expect(links.nth(1)).toHaveAttribute('href', '/roch-tools');
      await expect(page.getByRole('heading', { name: 'Latest Videos' })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await links.nth(0).focus();
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL('/youtube');
      await expect(page.locator('html')).toHaveAttribute('data-theme', mode);
    });
  }
}
