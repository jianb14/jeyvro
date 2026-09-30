/**
 * PasswordInput — a password field with a reveal toggle in its trailing slot.
 *
 * The toggle is the whole point of this component, so the `visible` state lives
 * here rather than in each route: /login and /register would otherwise each hold
 * their own copy of the same boolean, the same `type` swap, and the same pair of
 * icons, and the two would drift.
 *
 * Accessibility notes, because a reveal button is easy to get wrong:
 *  - it is `type="button"`, so it never submits the form it sits inside;
 *  - `aria-pressed` states the current mode, so the control announces as a
 *    toggle rather than as an unlabelled button that mysteriously retypes the
 *    field;
 *  - the accessible name changes with the state ("Show password" /
 *    "Hide password") *and* `aria-pressed` is kept, because the name alone
 *    describes the action while the pressed state describes the mode — screen
 *    reader users get both, and neither is ambiguous on its own;
 *  - the icon is `aria-hidden` (every icon in Icons.jsx already is), so it is
 *    never read as a second, redundant label.
 *
 * `visible`/`onVisibleChange` are exposed for tests and for the rare caller that
 * needs to know the mode; omit both and the component manages itself.
 */
import { forwardRef, useState } from "react";
import { Input } from "./Input";
import { EyeIcon, EyeOffIcon } from "./Icons";

export const PasswordInput = forwardRef(function PasswordInput(
  { visible: controlledVisible, onVisibleChange, ...props },
  ref
) {
  const [uncontrolledVisible, setUncontrolledVisible] = useState(false);
  // Controlled when a parent passes `visible`, uncontrolled otherwise. Deriving
  // this during render (rather than syncing two states in an effect) means the
  // field can never display one mode while the button announces another.
  const isControlled = controlledVisible !== undefined;
  const visible = isControlled ? controlledVisible : uncontrolledVisible;

  const toggle = () => {
    const next = !visible;
    if (!isControlled) setUncontrolledVisible(next);
    onVisibleChange?.(next);
  };

  return (
    <Input
      ref={ref}
      type={visible ? "text" : "password"}
      trailingAction={
        <button
          type="button"
          onClick={toggle}
          aria-pressed={visible}
          aria-label={visible ? "Hide password" : "Show password"}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-700 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-moss-500 dark:hover:bg-night-800 dark:hover:text-sand-100 dark:focus-visible:outline-moss-400"
        >
          {visible ? <EyeOffIcon size={17} /> : <EyeIcon size={17} />}
        </button>
      }
      {...props}
    />
  );
});
