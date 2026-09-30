/**
 * The theme cross-fade in index.css is a hand-written list of CSS properties.
 * Nothing makes it stay in step with what the components actually use, so a
 * new `dark:` utility on a property that isn't listed will snap while the rest
 * of the page fades — a one-frame flash that is genuinely hard to spot by
 * eye and impossible to spot in review.
 *
 * These tests close that loop: they read the real stylesheet, extract the
 * properties it animates, and assert that every `dark:` utility in the source
 * maps to one of them. A component that needs a new property now fails here
 * instead of shipping a subtle visual bug.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = resolve(HERE, "..");
const INDEX_CSS = resolve(SRC, "index.css");

const SOURCE_EXTS = new Set([".js", ".jsx", ".ts", ".tsx", ".css", ".html"]);

// Tailwind utility prefix -> CSS property it ultimately changes.
// Longest/most specific first: `dark:bg-linear-` must not be read as `dark:bg-`.
const PROPERTY_BY_UTILITY = [
  [/^bg-(linear|radial|conic)-/, "background-image"],
  [/^bg-/, "background-color"],
  [/^text-/, "color"],
  [/^border-/, "border-color"],
  [/^border-[xytblrse]?-/, "border-color"],
  [/^outline-/, "outline-color"],
  [/^divide-/, "border-color"],
  [/^ring-/, "box-shadow"],
  [/^shadow-/, "box-shadow"],
  [/^fill-/, "fill"],
  [/^stroke-/, "stroke"],
  [/^placeholder:/, "color"],
  [/^caret-/, "caret-color"],
  [/^accent-/, "accent-color"],
  [/^opacity-/, "opacity"],
  [/^(brightness|saturate|contrast|invert|sepia|grayscale|hue-rotate)-/, "filter"],
  [/^blur-/, "filter"],
  [/^backdrop-/, "backdrop-filter"],
  [/^mix-blend-/, "mix-blend-mode"],
  [/^decoration-/, "text-decoration-color"],
];

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (SOURCE_EXTS.has(extname(p))) out.push(p);
  }
  return out;
}

/** Properties the cross-fade rule animates, parsed from the real stylesheet. */
function readAnimatedProperties() {
  const css = readFileSync(INDEX_CSS, "utf8");
  const block = css.match(/@media \(prefers-reduced-motion: no-preference\)\s*{[^}]*{([^}]*)/);
  expect(block, "index.css is missing the prefers-reduced-motion theme block").not.toBeNull();
  const decl = block[1].match(/transition-property:\s*([^;]+);/);
  expect(decl, "the theme block has no transition-property declaration").not.toBeNull();
  return new Set(
    decl[1]
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
  );
}

/** Every `dark:<utility>` in the source, mapped to the property it changes. */
function readDarkUtilities() {
  const used = new Map(); // property -> example utility
  for (const file of walk(SRC)) {
    // Strip comments first. Otherwise a utility named in prose — including one
    // in this file's own docstrings — is counted as a real usage and demands a
    // property that nothing actually needs. A self-referential test that reads
    // itself is worse than no test.
    const text = readFileSync(file, "utf8")
      .replace(/\/\*[\s\S]*?\*\//g, " ")
      .replace(/(^|[^:])\/\/[^\n]*/g, "$1 ");

    for (const m of text.matchAll(/(?:^|[\s"'`:])dark:([a-z-]+(?:\[[^\]]*\])?)/g)) {
      const util = m[1];
      for (const [re, prop] of PROPERTY_BY_UTILITY) {
        if (re.test(util)) {
          if (!used.has(prop)) used.set(prop, util);
          break;
        }
      }
    }
  }
  return used;
}

describe("theme cross-fade coverage", () => {
  it("animates every CSS property the dark: utilities actually change", () => {
    const animated = readAnimatedProperties();
    const used = readDarkUtilities();

    // Sanity: the audit is looking at a real codebase, not an empty string.
    expect(used.size).toBeGreaterThan(0);
    expect([...used.keys()]).toContain("background-color");

    const uncovered = [...used.entries()].filter(([prop]) => !animated.has(prop));
    expect(
      uncovered,
      `these properties change in dark mode but are not in the transition-property ` +
        `list, so they will snap while everything else fades: ` +
        uncovered.map(([p, u]) => `${p} (e.g. dark:${u})`).join(", ")
    ).toEqual([]);
  });

  it("keeps the ::placeholder pseudo-element reachable", () => {
    // A `*` descendant rule does not style ::placeholder; it needs its own
    // selector, or every input's placeholder snaps while the field fades.
    const css = readFileSync(INDEX_CSS, "utf8");
    expect(css).toMatch(/html\.theme-transition \*::placeholder/);
  });

  it("stays opt-in so hovers are not permanently transitioned", () => {
    const css = readFileSync(INDEX_CSS, "utf8");
    const block = css.match(/@media \(prefers-reduced-motion: no-preference\)\s*{[\s\S]*?\n}/);
    expect(block).not.toBeNull();
    // Every selector in the block must be gated on .theme-transition.
    const selectors = block[0].match(/html\.theme-transition[^{]*{/g) || [];
    expect(selectors.length).toBeGreaterThan(0);
    expect(block[0]).not.toMatch(/^\s*\*(?!\.)/m);
  });

  it("ships the View Transition cross-fade, which is the primary path", () => {
    const css = readFileSync(INDEX_CSS, "utf8");
    // The snapshot path is what actually reads as smooth; if these go missing
    // the switch silently degrades to the property-list fallback and the
    // scrollbar and placeholders start snapping again.
    expect(css).toMatch(/::view-transition-new\(root\)/);
    expect(css).toMatch(/::view-transition-old\(root\)/);
    // Pinning the old snapshot avoids the both-at-50% grey dip.
    expect(css).toMatch(/::view-transition-old\(root\)\s*{[^}]*animation:\s*none/);
  });
});
