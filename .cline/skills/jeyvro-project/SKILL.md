---
name: jeyvro-project
description: Orientation for the Jeyvro workspace — use when asked where things live, how to run or build the project, what the stack is, what components exist, or when starting a fresh session in this repo. Covers the frontend folder map, all npm commands (including the Windows npm.cmd quirk), the 45+ component inventory in components/ui, the lib utilities, and how the DesignSystemPage and its sections are organized.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Jeyvro Project Orientation

Everything needed to navigate this workspace without re-asking the user.

## Stack

- **Frontend:** React 19 + Vite + Tailwind CSS v4 (CSS-first config, no `tailwind.config.js`), plain JavaScript/JSX — no TypeScript. Routing via `react-router-dom` (`BrowserRouter` in `main.jsx`).
- **Backend:** Django + Django REST Framework + PostgreSQL (to be built — the sole approved backend target). Until then, the frontend runs on mock data accessors (see the `data-layer` skill).
- Design tokens in `frontend/src/index.css` (`@theme`): moss/sand/night palettes + semantic colors. See the `design-tokens` skill.
- Dark mode: class-based (`.dark` on `<html>`), persisted in `localStorage` as `jeyvro-theme`, initialized by an inline script in `frontend/index.html`.
- Fonts: Outfit (`font-sans`), Plus Jakarta Sans (`font-display`, via Google Fonts).
- Data access goes **only** through async accessors in `frontend/src/data/` — see the `data-layer` skill.
- No state library, no test runner, no git repo yet.

## Commands

Frontend (run from `frontend/`):

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server (proxies `/api` → localhost:8000, Django) |
| `npm run lint` | ESLint over the project |
| `npm run build` | Production build (vite build) |
| `npm run preview` | Preview the production build |

Backend: none yet — Django (to be scaffolded) will run via `manage.py runserver` on port 8000.

> **Windows (this machine):** PowerShell blocks `npm.ps1` — use `npm.cmd run ...` instead. If shell output is not visible, redirect to a temp log file and read it.

## Folder map

```
frontend/
  index.html                  fonts, theme-init script, #root
  vite.config.js              React + Tailwind plugins; dev proxy: /api → localhost:8000 (Django)
  src/
    main.jsx                  entry: StrictMode + BrowserRouter
    App.jsx                   routes: / → Home, /design-system → DesignSystem
    index.css                 ALL design tokens (@theme) + base styles
    routes/
      Home.jsx                marketplace landing (search, grid, full async states)
      DesignSystem.jsx        wraps pages/DesignSystemPage
    data/
      products.js             async accessors — the ONLY frontend data access point
    lib/
      cx.js                   class merge utility (cx(...classes))
      useTheme.js             light/dark toggle hook
      useToasts.js            toast queue hook (useToasts)
    components/
      layout/Navbar.jsx       design-system header
      ui/                     ~45 primitives, one file each (see below)
    pages/
      DesignSystemPage.jsx    assembles the design-system demo (NAV_SECTIONS + sections)
    sections/                 design-system showcases, one per category + shared.jsx
```

## Component inventory (`components/ui/`, all named exports)

Layout/primitives: Button, Card (+CardHeader/Title/Description/Content/Footer), Divider, Kbd, Label, Icons (the only icon source).
Forms: Input, Textarea, Select, Checkbox, Radio, Switch, FileUpload (+FileList), VariantPicker.
Navigation: Tabs (+TabPanel), Breadcrumb, Pagination, DropdownMenu (+MenuButton), CommandPalette.
Data display: Table (+THead/TH/TBody/TR/TD), Badge, Avatar (+AvatarGroup), Chip, Rating, Price, ProductCard (+ProductGrid), StockIndicator, StoreCard, ReviewCard, OrderStatusBadge, PaymentMethodCard, AddressCard (+AddressList), CartItem, CartSummary, Accordion, Tooltip, Timeline.
Feedback/overlays: Alert, Toast (+ToastViewport), Progress, Spinner, Skeleton, Modal, Drawer, EmptyState, Stepper.

## Routes vs design-system registration

- **Marketplace pages** are routes: create `src/routes/<Name>.jsx` (reference implementation: `routes/Home.jsx`), add a `<Route>` in `App.jsx`, link it from the app header.
- **Design-system showcases** live in `src/sections/<Name>Section.jsx` using `Section`/`Demo` from `sections/shared.jsx`, registered in `pages/DesignSystemPage.jsx` (both `NAV_SECTIONS` and the page body). Only new UI primitives go here.

For deeper guidance: building components → `frontend-ui` skill · tokens → `design-tokens` · UX behavior → `ux-patterns` · whole features → `frontend-feature` · data/API rules → `data-layer` · state placement → `frontend-state` · responsive/mobile-first → `frontend-responsive` · speed → `frontend-performance` · QA → `frontend-review` · git → `git-workflow` · testing/debugging → `testing` · Django/data/ORM → `backend-core` · REST API → `backend-api` · auth/permissions → `security` · backend domains → `backend-feature` · catalog → `marketplace-catalog` · cart/checkout/orders → `marketplace-orders` · sellers/stores → `marketplace-sellers` · reviews/wishlist/messaging → `marketplace-community` · staff/admin → `marketplace-admin` · payments/payouts → `payments-skill` · API/database tuning → `performance-skill` · shipping/ops → `deployment` · MCP/agent config → `ai-tooling`.
