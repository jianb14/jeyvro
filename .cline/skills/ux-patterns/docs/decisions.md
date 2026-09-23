# UX Decision Trees

For ambiguous situations. Each tree assumes the Jeyvro component set.

## 1. Where does this message go?

```
Did the user just trigger an action?
├─ YES → Did it succeed or fail?
│        ├─ Succeed + user stays on page → Toast (success) + update the UI itself
│        ├─ Succeed + navigate away anyway → skip the toast, the new page IS the feedback
│        └─ Fail → can the user fix it here?
│                 ├─ YES → inline Alert (danger) near the form/section
│                 └─ NO (fatal) → full-page error state with retry action
└─ NO (system-initiated, e.g. new version) → Toast (info) or Badge, never a modal
```

## 2. Do I need a confirmation?

```
Is the action destructive or hard to reverse (delete, remove, pay, logout)?
├─ NO  → no confirm; make it easy to undo instead where possible
└─ YES → Modal with:
         • title naming object + verb ("Delete address?")
         • description stating consequence ("This can't be undone.")
         • footer: ghost "Cancel" + destructive Button
         • focus lands inside; Escape = Cancel (Modal handles Escape)
```

## 3. Loading pattern?

```
Is the final layout known?
├─ YES → Skeletons shaped like the content (cards → card skeletons, rows → row skeletons)
└─ NO  → is it inside a button/action?
         ├─ YES → Button loading prop
         └─ NO  → Spinner centered in the affected region
Progress bar instead of either when % progress exists.
```

## 4. Optimistic update or wait-for-server?

```
Is the action easily reversible and failure rare (like, follow, qty change)?
├─ YES → optimistic update; on failure, roll back + Toast (danger)
└─ NO  (payment, delete, submit) → wait for result; Button loading during flight
```

## 5. Nested overlays (drawer inside modal, etc.)?

Avoid. If unavoidable: one Escape closes only the topmost layer; only the
topmost scrolls; backdrop of the lower layer stays inert. Prefer restructuring
into steps (Stepper) over stacking overlays.

## 6. Multiple toasts at once?

Cap visible stack (~3) in `ToastViewport` usage; coalesce repeats ("3 items
added") instead of firing 3 toasts. Toasts are bottom-right, non-blocking —
they must never cover a primary action the user is about to click.

## 7. Motion budget

One entrance animation per element (tokens already include it). Additional
allowed cases: drawer/modal transitions, toast slide-in, hover elevation
(`shadow-lift`), chevron rotate on expand. Everything else: no motion. If you
are reaching for a keyframe not in `index.css`, the answer is almost always no
(see `design-tokens` skill).
