/**
 * Light/dark switch — a shared control, so it lives in `ui/` rather than
 * inside Navbar. Two shells render it (the storefront header and the admin
 * console), and a second copy would be a second thing to keep in sync.
 *
 * The state behind it is module scope in `lib/useTheme.js` precisely because of
 * that duplication: each call site must agree about the current mode.
 */
import { cx } from "../../lib/cx";
import { useTheme } from "../../lib/useTheme";
import { SunIcon, MoonIcon } from "./Icons";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="relative inline-flex size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-sand-300 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
    >
      {/* Both icons are mounted and cross-faded, rather than swapping one for
          the other. Conditionally rendering made the change instant and also
          dropped the button's contents, which reads as a flicker at this size.
          The wrapper is the positioning context so the absolute children stack
          instead of sitting side by side. */}
      <span className="relative block size-5">
        <SunIcon
          size={20}
          className={cx(
            "absolute inset-0 transition-all duration-300 ease-out motion-reduce:transition-none",
            theme === "dark" ? "scale-100 rotate-0 opacity-100" : "scale-50 -rotate-90 opacity-0"
          )}
        />
        <MoonIcon
          size={20}
          className={cx(
            "absolute inset-0 transition-all duration-300 ease-out motion-reduce:transition-none",
            theme === "dark" ? "scale-50 rotate-90 opacity-0" : "scale-100 rotate-0 opacity-100"
          )}
        />
      </span>
    </button>
  );
}