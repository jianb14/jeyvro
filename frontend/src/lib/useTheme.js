import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "jeyvro-theme";
// Kept in step with the `transition-duration` in the .theme-transition block
// in index.css. The timer only has to outlast the animation, not match it
// exactly, so this carries a little slack.
const TRANSITION_MS = 260;
const SETTLE_MS = TRANSITION_MS + 60;

function prefersReducedMotion() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function getInitialTheme() {
  if (typeof window === "undefined") return "light";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  // Runs at module scope, so it can beat any test-time matchMedia stub. Guard
  // it the same way as prefersReducedMotion rather than assuming the API.
  if (typeof window.matchMedia !== "function") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// Module-level, not useState. The Navbar renders ThemeToggle twice (desktop
// rail + mobile sheet) and each call used to get its own useState, so the two
// buttons could disagree — click the mobile one and the desktop icon kept
// showing the old mode until a remount. The class on <html> is global, so the
// state backing it has to be too.
let theme = getInitialTheme();
const listeners = new Set();
let settleTimer = null;

function emit() {
  listeners.forEach((fn) => fn());
}

function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function getSnapshot() {
  return theme;
}

/**
 * Flip the DOM classes. Kept separate because both switch paths call it.
 */
function applyClasses(next) {
  const root = document.documentElement;
  root.classList.toggle("dark", next === "dark");
  root.style.colorScheme = next;
}

/**
 * Write the theme to the DOM, cross-fading when asked.
 *
 * Two mechanisms, because the first one is only ~5 years old:
 *
 * 1. View Transitions API (primary). The browser snapshots the viewport, swaps
 *    the DOM, and cross-fades old -> new on the compositor. This is the right
 *    tool for a theme switch because it is immune to the failure mode that
 *    keeps biting the CSS approach: a property-list transition can only
 *    animate properties somebody remembered to list, and only on elements the
 *    selector can reach. Placeholder text, the scrollbar, replaced elements
 *    and anything new a component adds all silently opt out. A viewport
 *    snapshot has no such holes.
 *
 * 2. A tagged `.theme-transition` class on <html> (fallback), which index.css
 *    turns into a broad transition. Used when the API is missing.
 *
 * The reflow in path 2 is load-bearing: without it the class add and the .dark
 * flip land in the same style recalc, the browser never observes a "before"
 * state that had a transition on it, and the switch snaps.
 */
function applyTheme(next, { animate }) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  // Someone who asked for reduced motion gets an instant switch, full stop.
  const shouldAnimate = animate && !prefersReducedMotion();

  const canViewTransition =
    shouldAnimate && typeof document.startViewTransition === "function";

  if (canViewTransition) {
    // The callback must perform the DOM change synchronously; startViewTransition
    // captures the "after" state as soon as it returns.
    document.startViewTransition(() => applyClasses(next));
    if (import.meta.env?.DEV) console.info("[theme] switch via View Transition");
    return;
  }

  if (shouldAnimate) {
    root.classList.add("theme-transition");
    // Forced reflow, not a no-op: the class and the .dark flip must land in
    // two style recalcs or the browser never sees a "before" state to
    // transition from and the switch snaps.
    void root.offsetWidth;
  }

  applyClasses(next);

  if (shouldAnimate) {
    // Clear any in-flight timer so rapid toggling don't cut a fade short.
    if (settleTimer) clearTimeout(settleTimer);
    settleTimer = setTimeout(() => {
      root.classList.remove("theme-transition");
      settleTimer = null;
    }, SETTLE_MS);
    if (import.meta.env?.DEV) console.info("[theme] switch via .theme-transition fallback");
  } else if (import.meta.env?.DEV) {
    console.info(
      "[theme] instant switch — reduced motion is %s",
      prefersReducedMotion() ? "ON (that is why it is not animating)" : "off"
    );
  }
}

function setTheme(next) {
  if (next === theme) return;
  theme = next;
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Private mode / storage disabled — the theme still applies for this
    // session, it just won't be remembered. Not worth failing a click over.
  }
  applyTheme(next, { animate: true });
  emit();
}

/**
 * Reads the current theme and returns a setter.
 *
 * Also re-syncs the DOM on mount, which covers the case where the module
 * resolved the theme before React hydrated. That first apply is deliberately
 * not animated — index.html has already painted the correct theme, and fading
 * it in on load would be a flash of the wrong colours.
 */
export function useTheme() {
  const current = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  if (typeof document !== "undefined") {
    const root = document.documentElement;
    const rootIsDark = root.classList.contains("dark");
    if (rootIsDark !== (current === "dark") || root.style.colorScheme !== current) {
      applyTheme(current, { animate: false });
    }
  }

  const toggle = useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, []);

  return { theme: current, toggle, setTheme };
}

