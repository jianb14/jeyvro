import { afterEach, describe, expect, it, vi } from "vitest";
import { addToWishlist, fetchWishlist, removeFromWishlist } from "./wishlist";

const API_ITEM = {
  slug: "woven-basket",
  title: "Woven Basket",
  description: "Handwoven.",
  price: 349,
  originalPrice: 499,
  discount: 30,
  rating: null,
  sold: 0,
  stock: 24,
  isNew: true,
  category: "Home & Living",
  category_slug: "home-living",
  store_name: "Kalinga Crafts",
  store_slug: "kalinga-crafts",
  store_verified: true,
  primary_image: "http://api/media/products/a.png",
  images: [],
  variants: [],
};

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async (url) => {
    // CSRF preflight always succeeds; assertions target the API calls.
    if (String(url).includes("/csrf")) {
      return { ok: true, status: 200, json: async () => ({ detail: "csrf cookie set" }) };
    }
    return { ok, status, json: async () => payload };
  });
  vi.stubGlobal("fetch", fetchMock);
  const callWith = (method) =>
    fetchMock.mock.calls.find(([, options]) => options?.method === method);
  return { fetchMock, callWith };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("wishlist accessors", () => {
  it("maps entries through the shared product contract", async () => {
    mockFetch({
      count: 1,
      items: [{ id: 5, created_at: "2026-01-01T00:00:00Z", available: true, product: API_ITEM }],
    });
    const wishlist = await fetchWishlist();
    expect(wishlist.count).toBe(1);
    expect(wishlist.items[0].productId).toBe("woven-basket");
    expect(wishlist.items[0].available).toBe(true);
    expect(wishlist.items[0].product.storeSlug).toBe("kalinga-crafts");
    expect(wishlist.items[0].product.variants).toEqual([]);
  });

  it("posts and deletes against the product slug", async () => {
    const { callWith } = mockFetch({
      id: 5,
      created_at: "2026-01-01T00:00:00Z",
      available: true,
      product: API_ITEM,
    });
    const entry = await addToWishlist("woven-basket");
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/wishlist/");
    expect(JSON.parse(post[1].body)).toEqual({ product_id: "woven-basket" });
    expect(entry.productId).toBe("woven-basket");

    const removeMock = mockFetch({ detail: "removed", count: 0 });
    await removeFromWishlist("woven-basket");
    const remove = removeMock.callWith("DELETE");
    expect(remove[0]).toBe("/api/v1/wishlist/items/woven-basket");
  });
});
