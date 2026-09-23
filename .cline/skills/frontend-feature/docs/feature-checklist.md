# Feature Checklist (end-to-end)

Work top to bottom; do not skip the gates.

## Scope
- [ ] User goal and data source (real/demo) confirmed or reasonably inferred
- [ ] Checked existing sections — extending beats duplicating

## Inventory
- [ ] Listed existing components that cover each part of the feature
- [ ] No re-implemented primitives (button/input/modal/toast/etc.)
- [ ] Any genuinely new primitive built per `frontend-ui` skill and added to `components/ui/`

## Implementation
- [ ] All four async/UX states wired: loading, empty, error, success (`ux-patterns`)
- [ ] Destructive actions confirmed via `Modal`; feedback via `Toast`/`Alert` per decision trees
- [ ] Design tokens only — no hardcoded colors/shadows/animations (`design-tokens`)
- [ ] Every component has `dark:` variants; `cx()` merging; icons from `Icons.jsx` only

## Registration
- [ ] `src/sections/<Name>Section.jsx` created with `Section`/`Demo`
- [ ] Added to `NAV_SECTIONS` **and** page body in `DesignSystemPage.jsx`
- [ ] New primitives demoed in their own section

## Gates (from `frontend-review` skill)
- [ ] Keyboard operable; focus visible; ARIA wired; labels associated
- [ ] Responsive at ~360px / ~768px / ~1280px; no horizontal overflow
- [ ] Light + dark both look correct
- [ ] `npm.cmd run lint` → 0 errors (run it, log it, read it)
- [ ] `npm.cmd run build` → success (run it, log it, read it)
- [ ] Review report output in the `frontend-review` format
