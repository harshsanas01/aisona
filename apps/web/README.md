# CareCall Insight - frontend

A Vite + React + TypeScript single-page app for the CareCall Insight care-coordination
tool. This note covers the design system and structure introduced in the production
UI redesign; it does not document the backend (see the root `README.md` and `docs/`).

## Stack

- React 18 + TypeScript, Vite build/dev server
- `react-router-dom` for the five top-level routes (`/ask`, `/calls`, `/safety-events`,
  `/ingestion`, `/evaluations`)
- `lucide-react` for icons (no emoji as UI iconography)
- Plain, token-based CSS - no CSS-in-JS or utility framework. Each feature/component
  owns a small scoped `.css` file; there is no global stylesheet of page styles.
- `vitest` + `@testing-library/react` for component/interaction tests (there was no
  frontend test runner before this redesign - see `vitest.config.ts`)

## Design tokens and UI primitives

All color, spacing, radius, shadow, typography, and motion values live in
`src/styles/tokens.css` as CSS custom properties. Components should reference a
`var(--...)` token rather than hard-coding a color or pixel value; if a new color is
needed, add it to `tokens.css` first.

Reusable primitives live in `src/components/ui/` (Button, IconButton, Badge, Card,
Input, Textarea, Select, DateInput, EmptyState, ErrorState, Skeleton, Toast, Modal,
Drawer, Tabs, Tooltip, StatCard, FilterChip, SourceCard, SafetyBadge) and are styled
by the single `ui.css` file next to them. `Modal` and `Drawer` share a focus-trap /
Escape-to-close / focus-return hook (`useDismissable`) - reuse it for any new
dismissable panel rather than re-implementing keyboard handling.

## Structure

```
src/
  app/                    App.tsx (routes) and main.tsx (providers)
  components/
    layout/               AppShell, Sidebar, Header, navItems (nav/route metadata)
    ui/                    Design-system primitives (see above)
  features/
    ask-question/          Ask page: composer, streaming, answer/source cards
    calls/                  Calls explorer
    safety/                 Safety Events dashboard + shared safety category metadata
    ingestion/              Ingestion workflow + client-side payload validation
    evaluations/            Static CLI-evaluation documentation panel
    patient-filters/        Patient/date filter bar (used by Ask)
    transcript-viewer/      TranscriptDrawerContext + TranscriptDrawer (shared)
  hooks/                    Cross-feature hooks (useAskQuestion, useHealth)
  services/api.ts           All fetch() calls - the only place that talks to the API
  types/                    Shared TypeScript types mirroring the API's response shapes
```

Each page under `features/` owns its data fetching via a small hook (e.g. `useCalls`,
`useSafetyDashboard`) that calls into `services/api.ts`. Nothing outside
`services/api.ts` calls `fetch` directly.

### The transcript drawer is shared, not per-page

`TranscriptDrawerProvider` (wrapping the whole app in `main.tsx`) and the single
`<TranscriptDrawer />` rendered once in `AppShell` are what let Ask, Calls, and Safety
Events all open "the transcript, scrolled to turn N" without each page owning its own
copy of the panel. Call `useTranscriptDrawer().open({ callId, turnStart, turnEnd,
focusTurn, category })` from any page; `turnStart`/`turnEnd` highlight a cited range,
`focusTurn` is what the drawer scrolls to and defaults to `turnStart`, and `category`
pre-filters the drawer's safety-category legend.

## Known gaps / unfinished polish

- **Theme toggle**: the design brief called this out as optional "if implemented
  cleanly"; it was not implemented. The palette is light-mode only.
- **Calls list duration**: `GET /api/calls` doesn't return `duration_seconds`, only
  `GET /api/calls/{id}` does, so the Calls explorer shows a safety-flag count (derived
  from `/api/safety-events`) but not duration, to avoid either fabricating data or an
  N+1 fetch per row.
- **Transcript full-text search** on the Calls page searches patient name, call ID,
  and date (all present in the list endpoint) - not turn text, since that would
  require fetching every transcript client-side.
- **Evaluations page** is intentionally a static "run this from the CLI" panel, since
  the API has no evaluation endpoints; wire it to real data if/when one exists.

## Running

```
npm install
npm run dev         # Vite dev server on :5173, proxies /api to :8000
npm run typecheck    # tsc -b
npm run test         # vitest run
npm run build        # tsc -b && vite build
```

Requires Node 20 (matches the CI workflow and Docker image) - some dependencies
(`react-router-dom` 7.x, `vitest` 4.x) do not run on Node 18.
