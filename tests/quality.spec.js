const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const fs = require('node:fs');
const path = require('node:path');
const pages = ['/', '/youtube', '/roch-tools', '/skool', '/discord', '/parts', '/404'];

for (const mode of ['dark', 'light']) {
  for (const width of [320, 768, 1360]) {
    for (const url of pages) {
      test(`${url} ${mode} ${width}px: readable, no overflow, accessible`, async ({ page }) => {
        const errors = [];
        page.on('pageerror', e => errors.push(e.message));
        await page.setViewportSize({ width, height: 1000 });
        await page.emulateMedia({ colorScheme: mode });
        const response = await page.goto(url);
        expect(response.status()).toBe(200);
        await expect(page.locator('html')).toHaveAttribute('data-theme', mode);
        await expect(page.locator('body')).toHaveCSS('background-color', mode === 'dark' ? 'rgb(16, 17, 18)' : 'rgb(247, 247, 248)');
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1);
        await expect(page.getByRole('navigation').getByRole('link')).toHaveCount(6);
        for (const link of await page.getByRole('navigation').getByRole('link').all()) {
          await expect(link).toBeVisible();
          const box = await link.boundingBox();
          expect(box.height).toBeGreaterThanOrEqual(44);
          expect(box.x + box.width).toBeLessThanOrEqual(width);
        }
        await page.evaluate(() => document.querySelectorAll('img').forEach(i => i.loading = 'eager'));
        await expect.poll(() => page.evaluate(() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)), { timeout: 20000 }).toEqual([]);
        const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
        expect(audit.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) }))).toEqual([]);
        expect(errors).toEqual([]);
        const out = path.join('.artifacts', 'screenshots');
        fs.mkdirSync(out, { recursive: true });
        await page.screenshot({ path: path.join(out, `${url === '/' ? 'home' : url.slice(1)}-${mode}-${width}.png`), fullPage: true });
      });
    }
  }
}

test('all local links and resources resolve', async ({ page, request }) => {
  const local = new Set();
  for (const url of pages) {
    await page.goto(url);
    const links = await page.locator('a[href],script[src],link[href]').evaluateAll(nodes => nodes.map(n => n.getAttribute('href') || n.getAttribute('src')).filter(v => v.startsWith('/') && !v.startsWith('//')));
    links.forEach(link => local.add(link));
  }
  for (const url of local) expect((await request.get(url)).status(), url).toBe(200);
});

test('keyboard users can skip navigation and toggle theme', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  const toggle = page.getByRole('button', { name: 'Switch to light mode' });
  await toggle.focus();
  await page.keyboard.press('Space');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});

test('storage restrictions do not break the theme switch', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('Blocked', 'SecurityError'); } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Switch to light mode' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.getByRole('button', { name: 'Switch to dark mode' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});
