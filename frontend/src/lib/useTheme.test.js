import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const root = () => document.documentElement;

// jsdom ships no matchMedia, and useTheme asks it about
// prefers-reduced-motion on every switch. Default to "no preference" so the
// animation path is the one under test; individual cases override it.
function stubMatchMedia({ reduced = false, dark = false } = {}) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query) => ({
      matches: query.includes("reduced-motion") ? reduced : dark,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }))
  );
}

// The hook keeps `theme` at module scope on purpose (that is what makes the
// two ThemeToggle instances agree), so a test that leaves it on "dark" would
// silently decide the starting state of the next one. Reload the module per
// test and read it back so every case starts from a known baseline.
let useTheme;
async function loadHook() {
  vi.resetModules();
  ({ useTheme } = await import("./useTheme"));
  return useTheme;
}

beforeEach(async () => {
  localStorage.clear();
  root().className = "";
  root().removeAttribute("style");
  stubMatchMedia();
  vi.useFakeTimers();
  await loadHook();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  // Delete here rather than at the end of each test body: a failing assertion
  // aborts the body, and a leaked stub would silently reroute every later test
  // down the View Transition path.
  delete document.startViewTransition;
});

describe("useTheme", () => {
  it("flips the dark class on <html> and persists the choice", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
    expect(root().classList.contains("dark")).toBe(false);

    act(() => result.current.toggle());

    expect(result.current.theme).toBe("dark");
    expect(root().classList.contains("dark")).toBe(true);
    expect(root().style.colorScheme).toBe("dark");
    expect(localStorage.getItem("jeyvro-theme")).toBe("dark");
  });

  it("tags the switch with theme-transition, then cleans the tag up", () => {
    const { result } = renderHook(() => useTheme());

    act(() => result.current.toggle());
    // Mid-fade: the class has to be on the element while the colors move.
    expect(root().classList.contains("theme-transition")).toBe(true);

    act(() => {
      vi.advanceTimersByTime(400);
    });
    // Afterwards: leaving it on would make every hover repaint the page.
    expect(root().classList.contains("theme-transition")).toBe(false);
  });

  it("keeps the transition tag through rapid successive toggles", () => {
    const { result } = renderHook(() => useTheme());

    act(() => result.current.toggle());
    act(() => {
      vi.advanceTimersByTime(100);
    });
    act(() => result.current.toggle());
    // The first timer must not strip the tag out from under the second fade.
    expect(root().classList.contains("theme-transition")).toBe(true);

    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(root().classList.contains("theme-transition")).toBe(false);
  });

  it("skips the transition when the user prefers reduced motion", async () => {
    vi.unstubAllGlobals();
    stubMatchMedia({ reduced: true });
    const useReduced = await loadHook();
    const { result } = renderHook(() => useReduced());

    act(() => result.current.toggle());

    // The theme still applies; only the animation is suppressed.
    expect(result.current.theme).toBe("dark");
    expect(root().classList.contains("dark")).toBe(true);
    expect(root().classList.contains("theme-transition")).toBe(false);
  });

  it("prefers the View Transitions API when the browser has it", () => {
    const startViewTransition = vi.fn((cb) => {
      cb();
      return { finished: Promise.resolve() };
    });
    document.startViewTransition = startViewTransition;

    const { result } = renderHook(() => useTheme());
    act(() => result.current.toggle());

    expect(startViewTransition).toHaveBeenCalledTimes(1);
    // The DOM change has to happen inside the callback, or the API captures an
    // "after" state identical to the "before" one and nothing cross-fades.
    expect(root().classList.contains("dark")).toBe(true);
    // The CSS fallback tag must stay off, or both mechanisms would animate.
    expect(root().classList.contains("theme-transition")).toBe(false);

    delete document.startViewTransition;
  });

  it("falls back to .theme-transition when the API is missing", () => {
    expect(typeof document.startViewTransition).toBe("undefined");

    const { result } = renderHook(() => useTheme());
    act(() => result.current.toggle());

    expect(root().classList.contains("theme-transition")).toBe(true);
  });

  it("skips the View Transition when reduced motion is requested", async () => {
    const startViewTransition = vi.fn(() => ({ finished: Promise.resolve() }));
    document.startViewTransition = startViewTransition;

    vi.unstubAllGlobals();
    stubMatchMedia({ reduced: true });
    const useReduced = await loadHook();
    const { result } = renderHook(() => useReduced());

    act(() => result.current.toggle());

    // The theme still applies, but nothing is allowed to animate — including
    // the viewport snapshot, which the UA does not gate on its own.
    expect(result.current.theme).toBe("dark");
    expect(startViewTransition).not.toHaveBeenCalled();
    expect(root().classList.contains("theme-transition")).toBe(false);

    delete document.startViewTransition;
  });

  // Regression: the Navbar mounts ThemeToggle twice (desktop + mobile) and
  // each call used to own a private useState, so the two buttons disagreed.
  it("shares one theme across simultaneous consumers", () => {
    const a = renderHook(() => useTheme());
    const b = renderHook(() => useTheme());

    act(() => a.result.current.toggle());

    expect(a.result.current.theme).toBe("dark");
    expect(b.result.current.theme).toBe("dark");
  });

  it("honours a stored preference on load", async () => {
    localStorage.setItem("jeyvro-theme", "dark");
    const useStored = await loadHook();

    const { result } = renderHook(() => useStored());
    expect(result.current.theme).toBe("dark");
    // The module resolved the theme before React mounted, so the hook
    // re-syncs the DOM on first render — without animating it.
    expect(root().classList.contains("dark")).toBe(true);
    expect(root().classList.contains("theme-transition")).toBe(false);
  });

  it("survives a blocked localStorage", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });
    const { result } = renderHook(() => useTheme());

    expect(() => act(() => result.current.toggle())).not.toThrow();
    expect(result.current.theme).toBe("dark");
    setItem.mockRestore();
  });
});
