import { afterEach, describe, expect, it } from "vitest";
import { getRecentlyViewed, recordRecentlyViewed } from "./recentlyViewed";

const product = (id) => ({ id, title: `Product ${id}`, price: 100 });

afterEach(() => {
  localStorage.clear();
});

describe("recently viewed foundation", () => {
  it("records products newest-first and dedupes", () => {
    recordRecentlyViewed(product("a"));
    recordRecentlyViewed(product("b"));
    recordRecentlyViewed(product("a"));

    const items = getRecentlyViewed();
    expect(items.map((item) => item.id)).toEqual(["a", "b"]);
  });

  it("keeps a light snapshot (no description/images/variants)", () => {
    recordRecentlyViewed({
      ...product("a"),
      description: "heavy",
      images: ["http://x/a.png"],
      variants: [{ id: 1 }],
    });
    const [item] = getRecentlyViewed();
    expect(item.description).toBeUndefined();
    expect(item.images).toBeUndefined();
    expect(item.variants).toBeUndefined();
    expect(item.title).toBe("Product a");
  });

  it("caps the list at 8 entries", () => {
    for (let i = 0; i < 12; i += 1) recordRecentlyViewed(product(String(i)));
    expect(getRecentlyViewed()).toHaveLength(8);
  });

  it("survives corrupted storage", () => {
    localStorage.setItem("jeyvro.recentlyViewed", "{not-json");
    expect(getRecentlyViewed()).toEqual([]);
  });
});