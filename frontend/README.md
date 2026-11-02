# Thimi Tech — public portfolio (frontend)

Vue 3 + Vite frontend for the Thimi Tech website and the Thimi Tech OS workspace.
This package is **not** a standalone template: the hero globe, the generated section
imagery and the workspace all rely on the dependencies below, so a fresh clone must
run `npm install` before anything will open.

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Node.js | `^22.18.0` or `>=24.12.0` | Vite 8, Vitest 4 and Vue 3.5 need it; Node 20 crashes the test runner |
| npm | 10 or newer | older npm hits an arborist bug on this lockfile |

Check with `node -v`. The exact ranges are enforced in `package.json` (`engines`), so
an unsupported Node shows up as `EBADENGINE` during install.

## Setup

```sh
npm install     # required once after cloning — nothing works without node_modules
npm run dev     # http://localhost:5173
```

`npm run dev` proxies `/api` and `/media` to the Django backend on `127.0.0.1:8000`.
Start the backend too (see `../CLAUDE.md`, or run `start-dev.bat` in the repo root) or
the portfolio's project / team / hiring sections will show their "unavailable" states.

## The hero globe

`src/components/GlobeScene.vue` (three.js + globe.gl) renders the sphere, the network
arcs and the sparkles. `src/components/globeTexture.ts` draws the map that wraps it —
ocean, country polygons, graticule, ice caps and city markers — with **OpenLayers**, and
returns it as a canvas texture. Requirements for it to work:

- `node_modules` present (`three`, `globe.gl`, `ol` — all declared in `package.json`)
- `public/countries-110m.json` present (committed; used for the country outlines)
- a browser with WebGL

If any of those are missing the component degrades instead of breaking: without WebGL
it shows the flat OpenLayers map, and without the country file it still draws the ocean,
graticule and network markers.

## Scripts

```sh
npm run dev          # dev server with hot reload
npm run build        # type-check (vue-tsc) + production build into dist/
npm run preview      # serve the built output
npm run test:unit    # Vitest unit tests
npm run test:e2e     # Playwright end-to-end tests (needs: npx playwright install)
npm run lint         # oxlint + eslint
npm run format       # oxfmt
```

## Troubleshooting a fresh clone

| Message in VS Code / terminal | Meaning | Fix |
|---|---|---|
| `Cannot find module 'globe.gl'`, `'three'`, `'ol/Map.js'`, or `Failed to resolve import` — usually pointing at `GlobeScene.vue` / `globeTexture.ts` | `node_modules` is missing: those files import the most packages, so they surface first | run `npm install` in this folder, then reload the VS Code window |
| `EBADENGINE … required: {"node":"^22.18.0 || >=24.12.0"}` | Node too old (often 18/20) | install Node 22 LTS or 24 and reinstall |
| Portfolio sections show "temporarily unavailable" | backend not running on `:8000` | start Django (`start-dev.bat`), or run the seed: `myenv\Scripts\python.exe seed_dev.py` |
| Hero shows a flat world map instead of the 3D globe | browser/GPU has no WebGL (or it was blocked) | expected fallback; enable hardware acceleration in the browser |
| Globe is a plain sphere with grid lines but no countries | `public/countries-110m.json` missing | `git checkout -- public/countries-110m.json` |

## Recommended editor setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
with Vetur disabled. TypeScript cannot read `.vue` types on its own, so the project
type-checks with `vue-tsc` instead of `tsc`.
