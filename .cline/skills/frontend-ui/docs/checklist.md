# Component Definition of Done

Before saying a component is finished, verify every item below.

## API & code

- [ ] Named export matching the file name; no `export default`
- [ ] Variants/sizes as const maps above the component; `className` merged **last** via `cx()`
- [ ] Props destructured with inline defaults; remaining props spread onto root
- [ ] Form controls use `forwardRef` + `useId`
- [ ] Icons imported only from `components/ui/Icons.jsx`
- [ ] No hardcoded colors/shadows/animations — design tokens only

## Styling

- [ ] Complete `dark:` variants for bg / text / border / hover / active
- [ ] `focus-visible` state present
- [ ] `duration-150` transitions on interactive elements; touch target ≥ 44px

## Accessibility

- [ ] Keyboard operable (logical Tab order; Enter/Space activate; Escape closes overlays)
- [ ] Labels associated (`htmlFor`/`id`); errors use `aria-invalid` + `aria-describedby`
- [ ] Icon-only controls have `aria-label`
- [ ] Status conveyed by icon + text, never color alone
- [ ] Overlays: `role="dialog"`, `aria-modal="true"`, `createPortal`, Escape handler, body scroll lock

## Integration

- [ ] Showcased in `frontend/src/sections/` (using `Section`/`Demo`) and registered in `DesignSystemPage.jsx`
- [ ] `npm run lint` passes in `frontend/`
- [ ] `npm run build` passes in `frontend/`
