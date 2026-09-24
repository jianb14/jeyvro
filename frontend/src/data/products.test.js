import { afterEach, describe, expect, it, vi } from "vitest";
import { getCategories, getProductById, getProducts } from "./products";

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
  images: [{ image: "http://api/media/products/a.png" }],
  variants: [
    {
      id: 1,
      sku: "woven-basket",
      name: "Default",
      price: "349.00",
      is_default: true,
      is_active: true,
      inventory: { available: 24, low_stock_threshold: 5 },
    },
  ],
};

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async () => ({
    ok,
    status,
    json: async () => payload,
  }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("catalog accessors", () => {
  it("maps list responses to the {count, items} contract", async () => {
    const fetchMock = mockFetch({ count: 1, items: [API_ITEM] });
    const data = await getProducts({
      q: "basket",
      sort: "discount",
      minPrice: "100",
      page: 2,
      pageSize: 12,
    });

    expect(data.count).toBe(1);
    const [item] = data.items;
    expect(item.id).toBe("woven-basket");
    expect(item.image).toBe("http://api/media/products/a.png");
    expect(item.categorySlug).toBe("home-living");
    expect(item.rating).toBe(0); // null placeholder → 0 for rendering
    expect(item.variants[0].price).toBe(349); // Decimal string → number
    expect(item.variants[0].stock).toBe(24);
    expect(item.variants[0].lowStockThreshold).toBe(5);

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/catalog/products/?");
    expect(url).toContain("q=basket");
    expect(url).toContain("sort=discount");
    expect(url).toContain("min_price=100");
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=12");
  });

  it("returns null for a missing detail and maps prices to numbers", async () => {
    mockFetch({ detail: "Not found." }, { ok: false, status: 404 });
    expect(await getProductById("missing")).toBeNull();

    mockFetch(API_ITEM);
    const item = await getProductById("woven-basket");
    expect(item.price).toBe(349);
    expect(item.originalPrice).toBe(499);
    expect(item.variants[0].isDefault).toBe(true);
  });

  it("unwraps the category envelope into a plain list", async () => {
    mockFetch({ count: 1, items: [{ id: 1, parent: null, name: "Food", slug: "food" }] });
    expect(await getCategories()).toEqual([
      { id: 1, parent: null, name: "Food", slug: "food" },
    ]);
  });
});