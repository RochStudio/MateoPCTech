# Mateo PC Tech

Static HTML/CSS site for [mateopctech.com](https://mateopctech.com). No frontend framework, runtime package, or production build step is required.

## Design and themes

The shared `style.css` implements the approved **D** direction: graphite surfaces, restrained red accents, horizontal homepage video cards, and consistent tool/community layouts. Light mode uses the same layout and red identity with light surfaces; it is not the separate C concept.

`theme.js` runs before the stylesheet to apply a saved preference before first paint. With no saved preference, it follows the operating system. The header button changes mode and stores `mateopctech-theme` in local storage. If storage is blocked, the button still works for the current page. Without JavaScript, the content and navigation remain usable, CSS follows system appearance, and the inactive theme control stays hidden.

All six content pages and the 404 page share the theme control, keyboard skip link, footer, and responsive navigation. On mobile the six navigation links stay visible; no JavaScript menu is required. Colors use CSS variables, interactive controls have visible focus states, and motion is limited to short button feedback that respects reduced-motion preferences.

## Local preview

Requires Python 3.10+:

```sh
python scripts/serve.py --port 4174
```

Open **http://127.0.0.1:4174**. This loopback-only development server supports the site's extensionless page URLs. It is not a production server. Stop with Ctrl+C.

## Verification

Development tooling requires Node.js 20+ and Python 3.10+:

```sh
npm ci
npx playwright install chromium
npm run test:content
npm test
```

- Content tests retain the original page copy, links, requirements, prices, metadata, and ordered recommendation lists.
- Video-updater tests rebuild each generated region in a temporary file and confirm surrounding layouts are untouched and a second rebuild is idempotent.
- Playwright checks all seven pages in both themes at 320, 768, and 1360 CSS pixels; axe runs WCAG 2/2.1 A/AA checks for every combination.
- Tests also cover reload/navigation persistence, system preference changes, storage restrictions, keyboard operation, local links/resources, image loading, and no-JavaScript fallback.
- Full-page review screenshots are saved to `.artifacts/screenshots/`; test results/traces go to `test-results/`. Both are ignored by Git.

Browser tests load the existing external YouTube/X images; an external asset outage can therefore fail the image-loading check. Automated accessibility checks supplement rather than replace manual review and assistive-technology testing.

The snapshot in `tests/fixtures/original-pages.json` records pre-redesign public content. Complete generated video marker regions are excluded from immutable copy/link comparisons and checked separately against `data/videos.json` using the updater's latest/popular selection rules. Scheduled video updates need no baseline change when the data and generated HTML agree; intentional changes to surrounding content still require a reviewed baseline update. The existing scheduled updater does not run this development test suite.

## Video updates and deployment

`scripts/update_videos.py` and `.github/workflows/update-videos.yml` retain the existing RSS update workflow. Do not remove or rename the `LATEST`, `LATEST3:*`, and `POPULAR3:*` HTML comment markers or their `.video-grid` containers.

`vercel.json` retains `cleanUrls: true` and `trailingSlash: false`. Site files remain directly deployable as static files. Node dependencies are development-only. No analytics, cookies, external scripts, or remote theme services have been added.

Changes are prepared locally. A push, PR, merge, or deployment requires the separate publishing approval process.
