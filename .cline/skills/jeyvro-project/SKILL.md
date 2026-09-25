---
name: jeyvro-project
description: Orientation for the Jeyvro workspace — use when asked where things live, how to run or build the project, what the stack is, what components exist, or when starting a fresh session in this repo. Covers the frontend folder map, all npm commands (including the Windows npm.cmd quirk), the 50-primitive inventory in components/ui, the lib utilities, and how routes, features, and data accessors are organized.
---

> **Source of truth:** [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) — when anything conflicts, the project context wins.

# Jeyvro Project Orientation

Everything needed to navigate this workspace without re-asking the user.

## Stack

- **Frontend:** React 19 + Vite + Tailwind CSS v4 (CSS-first config, no `tailwind.config.js`), plain JavaScript/JSX — no TypeScript. Routing via `react-router-dom` (`BrowserRouter` in `main.jsx`).
- **Backend (live):** Django + Django REST Framework + PostgreSQL — `manage.py runserver` on port 8000; `/api` is proxied in dev. The frontend reaches it **only** through the async accessors in `frontend/src/data/` (see the `data-layer` skill).
- Design tokens in `frontend/src/index.css` (`@theme`): moss/sand/night palettes + semantic colors. See the `design-tokens` skill.
- Dark mode: class-based (`.dark` on `<html>`), persisted in `localStorage` as `jeyvro-theme`, initialized by an inline script in `frontend/index.html`.
- Fonts: Outfit (`font-sans`), Plus Jakarta Sans (`font-display`, via Google Fonts).
- Data access goes **only** through async accessors in `frontend/src/data/` — see the `data-layer` skill.
- State: no external state library — feature-scoped React contexts (`features/auth`, `features/cart`, `features/wishlist`) hold server truth; see the `frontend-state` skill.
- Tests: Vitest + jsdom + Testing Library on the frontend (`src/**/*.test.js[x]`), pytest + pytest-django on the backend. See the `testing` skill.
- Repo: GitHub `jianb14/jeyvro` (branch `main`); see the `git-workflow` skill.

## Commands

Frontend (run from `frontend/`):

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server (proxies `/api` → localhost:8000, Django) |
| `npm run lint` | ESLint over the project |
| `npm run test` | Vitest suite (jsdom + Testing Library) |
| `npm run test:watch` | Vitest in watch mode |
| `npm run build` | Production build (vite build) |
| `npm run preview` | Preview the production build |

Backend (run from `backend/`, using the venv at `%LOCALAPPDATA%\jeyvro-venv`):

| Command | What it does |
|---|---|
| `python manage.py runserver` | API on port 8000 (proxied by Vite) |
| `python -m pytest -q` | Full backend test suite |
| `python manage.py makemigrations` / `migrate` | Model migrations |

> **Windows (this machine):** PowerShell blocks `npm.ps1` — use `npm.cmd run ...` instead. If shell output is not visible, redirect to a temp log file and read it.
> **Vitest path quirk:** run the frontend **test** gate through a space-free path — `subst X: "<repo>"` then `cd X:\frontend`. The space in the repo path breaks Vitest's module identity and every suite fails with a misleading "failed to find the current suite" error (lint and build are unaffected). See the `testing` skill.

## Folder map

```
frontend/
  index.html                  fonts, theme-init script, #root
  vite.config.js              React + Tailwind plugins; test config (jsdom); dev proxy: /api → localhost:8000
  src/
    main.jsx                  entry: StrictMode + BrowserRouter
    App.jsx                   all routes (Home, Browse, ProductDetail, Storefront, Cart, Wishlist, auth)
    index.css                 ALL design tokens (@theme) + base styles
    routes/
      Home.jsx                marketplace landing (search, grid, full async states)
      Browse.jsx              /products + /category/:slug (URL-driven filters/sort/pagination)
      ProductDetail.jsx       /product/:slug (gallery, variant picker over server truth, quantity)
      Storefront.jsx          /store/:slug (store shelf)
      Cart.jsx                /cart (store-grouped lines, live revalidation)
      Wishlist.jsx            /wishlist (availability-aware saved products)
    features/                 feature modules: auth/, cart/ (CartContext + useQuickAdd), wishlist/
    data/                     async accessors — the ONLY frontend data access point (products, cart, wishlist, stores, auth)
    test/setup.js             Vitest setup (jest-dom matchers + RTL cleanup)
    lib/
      cx.js                   class merge utility (cx(...classes))
      useTheme.js             light/dark toggle hook
      useToasts.js            toast queue hook (useToasts)
      productCart.js          which variant a product-card "Add to cart" adds (shared by Home/Browse/Storefront)
    components/
      layout/Navbar.jsx       marketplace header (search, categories, cart/wishlist/user)
      ui/                     49 primitives, one file each (see below; Button.test.jsx is the component-test reference)
```

## Component inventory (`components/ui/`, all named exports)

Layout/primitives: Button, Card (+CardHeader/Title/Description/Content/Footer), Divider, Kbd, Label, Icons (the only icon source).
Forms: Input, Textarea, Select, Checkbox, Radio, Switch, FileUpload (+FileList), VariantPicker.
Navigation: Tabs (+TabPanel), Breadcrumb, Pagination, DropdownMenu (+MenuButton), CommandPalette.
Data display: Table (+THead/TH/TBody/TR/TD), Badge, Avatar (+AvatarGroup), Chip, Rating, Price, ProductCard (+ProductGrid), ProductShelf, ProductArt, StockIndicator, StoreCard, ReviewCard, OrderStatusBadge, PaymentMethodCard, PaymentStatusBadge, AddressCard (+AddressList), CartItem, CartSummary, QuantityStepper, Accordion, Tooltip, Timeline.
Feedback/overlays: Alert, Toast (+ToastViewport), ToastProvider, Progress, Spinner, Skeleton, Modal, Drawer, EmptyState, Stepper.

## Routes and primitives

- **Marketplace pages** are routes: create `src/routes/<Name>.jsx` (reference implementation: `routes/Home.jsx`), add a `<Route>` in `App.jsx`, link it from the app header.
- **New UI primitives** go in `components/ui/` and must be used by a real route/feature — the design-system playground was retired in Phase 7 (no `src/sections/`, no `pages/DesignSystemPage.jsx`); primitives are validated by tests + the `frontend-review` gates.

For deeper guidance: building components → `frontend-ui` skill · tokens → `design-tokens` · UX behavior → `ux-patterns` · whole features → `frontend-feature` · data/API rules → `data-layer` · state placement → `frontend-state` · responsive/mobile-first → `frontend-responsive` · speed → `frontend-performance` · QA → `frontend-review` · git → `git-workflow` · testing/debugging → `testing` · Django/data/ORM → `backend-core` · REST API → `backend-api` · auth/permissions → `security` · backend domains → `backend-feature` · catalog → `marketplace-catalog` · cart/checkout/orders → `marketplace-orders` · sellers/stores → `marketplace-sellers` · reviews/wishlist/messaging → `marketplace-community` · staff/admin → `marketplace-admin` · payments/payouts → `payments-skill` · API/database tuning → `performance-skill` · shipping/ops → `deployment` · MCP/agent config → `ai-tooling`.
