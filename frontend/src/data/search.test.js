import { afterEach, describe, expect, it, vi } from "vitest";
import { getSuggestions, recommendations, searchResults } from "./search";

const API_ITEM = {
  id: 7,
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

const API_FACETS = {
  categories: [{ slug: "home-living", name: "Home & Living", count: 3 }],
  brands: [{ slug: "rattan-co", name: "Rattan Co", count: 2 }],
  prices: [{ label: "₱100 – ₱500", min: 100, max: 500, count: 4 }],
  ratings: [{ label: "4★ & up", min: 4, count: 1 }],
  in_stock: { total: 5, in_stock: 4, out_of_stock: 1 },
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

describe("search accessors", () => {
  it("maps a ranked result set into the page contract", async () => {
    const fetchMock = mockFetch({
      query: "basket",
      count: 1,
      fuzzy: false,
      items: [API_ITEM],
      stores: [
        {
          slug: "kalinga-crafts",
          name: "Kalinga Crafts",
          logo_url: "http://api/logo.png",
          rating: 4.5,
          product_count: 12,
        },
      ],
      categories: [{ slug: "home-living", name: "Home & Living", product_count: 3 }],
      facets: API_FACETS,
    });

    const data = await searchResults({
      q: "basket",
      category: "home-living",
      brand: "rattan-co",
      minPrice: "100",
      maxPrice: "500",
      minRating: "4",
      inStock: "1",
      sort: "price_asc",
      page: 2,
      pageSize: 12,
    });

    // Products ride the catalog mapper, so a card renders identically here.
    expect(data.count).toBe(1);
    expect(data.fuzzy).toBe(false);
    expect(data.items[0].id).toBe("woven-basket");
    expect(data.items[0].variants[0].price).toBe(349);

    expect(data.stores[0]).toEqual({
      slug: "kalinga-crafts",
      name: "Kalinga Crafts",
      logo: "http://api/logo.png",
      rating: 4.5,
      productCount: 12,
    });
    expect(data.categories[0].productCount).toBe(3);

    expect(data.facets.categories[0]).toEqual({
      slug: "home-living",
      name: "Home & Living",
      count: 3,
    });
    expect(data.facets.prices[0]).toEqual({
      label: "₱100 – ₱500",
      min: 100,
      max: 500,
      count: 4,
    });
    expect(data.facets.ratings[0]).toEqual({ label: "4★ & up", min: 4, count: 1 });
    expect(data.facets.stock).toEqual({ total: 5, inStock: 4, outOfStock: 1 });

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/search/?");
    expect(url).toContain("q=basket");
    expect(url).toContain("category=home-living");
    expect(url).toContain("brand=rattan-co");
    expect(url).toContain("min_price=100");
    expect(url).toContain("max_price=500");
    expect(url).toContain("min_rating=4");
    expect(url).toContain("in_stock=1");
    expect(url).toContain("sort=price_asc");
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=12");
  });

  it("flags a fuzzy rescue so the UI can explain the ordering", async () => {
    mockFetch({ query: "banan", count: 1, fuzzy: true, items: [API_ITEM] });
    expect((await searchResults({ q: "banan" })).fuzzy).toBe(true);
  });

  it("treats an empty query as a real request, not an error", async () => {
    const fetchMock = mockFetch({ query: "", count: 0, fuzzy: false, items: [] });
    const data = await searchResults({ category: "home-living" });
    expect(data.count).toBe(0);
    expect(data.facets.stock).toEqual({ total: 0, inStock: 0, outOfStock: 0 });
    // No ?q= key at all — the browse-with-filters case.
    expect(fetchMock.mock.calls[0][0]).not.toContain("q=");
  });

  it("never calls the API for a single character", async () => {
    const fetchMock = mockFetch({ query: "b", products: [], stores: [], categories: [] });
    expect(await getSuggestions("b")).toEqual({
      query: "b",
      products: [],
      stores: [],
      categories: [],
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("maps suggestion groups by entity", async () => {
    const fetchMock = mockFetch({
      query: "bamboo",
      products: [{ slug: "bamboo-basket", title: "Bamboo Basket", store_name: "Bamboo Hut" }],
      stores: [{ slug: "bamboo-hut", name: "Bamboo Hut", product_count: 4 }],
      categories: [{ slug: "bamboo-goods", name: "Bamboo Goods", product_count: 2 }],
    });

    const data = await getSuggestions("  bamboo  ");
    expect(data.products).toEqual([
      { slug: "bamboo-basket", title: "Bamboo Basket", storeName: "Bamboo Hut" },
    ]);
    expect(data.stores[0].productCount).toBe(4);
    expect(data.categories[0]).toEqual({
      slug: "bamboo-goods",
      name: "Bamboo Goods",
      productCount: 2,
    });
    expect(fetchMock.mock.calls[0][0]).toContain("/api/v1/search/suggest/?q=bamboo");
  });

  it("rejects an oversized query before it leaves the browser", async () => {
    const fetchMock = mockFetch({});
    const oversized = "x".repeat(121);
    expect(await getSuggestions(oversized)).toEqual({
      query: oversized,
      products: [],
      stores: [],
      categories: [],
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces the server's 400 rather than inventing results", async () => {
    mockFetch({ error: "query_too_long", detail: "Too long." }, { ok: false, status: 400 });
    await expect(searchResults({ q: "x".repeat(121) })).rejects.toMatchObject({
      status: 400,
    });
  });
});

describe("§18.3 recommendation shelves", () => {
  it("maps a shelf through the same catalog mapper as search", async () => {
    const fetchMock = mockFetch({ kind: "trending", count: 1, items: [API_ITEM] });

    const data = await recommendations({ kind: "trending", limit: 8 });

    // The same guarantees as a search card: identical shape, server-resolved price.
    expect(data.kind).toBe("trending");
    expect(data.items[0].id).toBe("woven-basket");
    expect(data.items[0].variants[0].price).toBe(349);

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/search/recommendations/?");
    expect(url).toContain("kind=trending");
    expect(url).toContain("limit=8");
    // Nothing to anchor and no history: neither key is invented.
    expect(url).not.toContain("seed=");
    expect(url).not.toContain("seen=");
  });

  it("trusts the kind the server says it ranked for", async () => {
    mockFetch({ kind: "popular", count: 0, items: [] });
    expect((await recommendations({ kind: "trending" })).kind).toBe("popular");
  });

  it("sends the seed for an item-to-item shelf", async () => {
    const fetchMock = mockFetch({ kind: "related", count: 1, items: [API_ITEM] });
    await recommendations({ kind: "related", seed: "woven-basket" });
    expect(fetchMock.mock.calls[0][0]).toContain("seed=woven-basket");
  });

  it("sends the browser's own history as the personalization seed", async () => {
    const fetchMock = mockFetch({ kind: "personalized", count: 1, items: [API_ITEM] });
    await recommendations({ kind: "personalized", seen: [" woven-basket ", "", null] });
    // Blank and missing entries are dropped rather than sent as `,,`.
    expect(fetchMock.mock.calls[0][0]).toContain("seen=woven-basket");
  });

  it("caps the history at the server's limit, keeping the newest", async () => {
    const fetchMock = mockFetch({ kind: "personalized", count: 0, items: [] });
    const many = Array.from({ length: 30 }, (_, i) => `p-${i}`);
    await recommendations({ kind: "personalized", seen: many });

    const sent = new URL(fetchMock.mock.calls[0][0], "http://x").searchParams.get("seen");
    expect(sent.split(",")).toHaveLength(20);
    // Most-recent-first, so the tail is dropped rather than the head.
    expect(sent.split(",")[0]).toBe("p-0");
    expect(sent).not.toContain("p-25");
  });

  it("returns an empty shelf instead of calling an endpoint it knows will 400", async () => {
    const fetchMock = mockFetch({});

    // No seed: "related" has no subject. An empty shelf, not an error banner.
    expect(await recommendations({ kind: "related" })).toEqual({
      kind: "related",
      items: [],
    });
    expect(await recommendations({ kind: "similar" })).toEqual({
      kind: "similar",
      items: [],
    });
    // No history: a first visit is not a failure.
    expect(await recommendations({ kind: "personalized", seen: [] })).toEqual({
      kind: "personalized",
      items: [],
    });

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces a real failure rather than rendering an empty shelf", async () => {
    mockFetch({ error: "not_found", detail: "No sellable product." }, { ok: false, status: 404 });
    // A seed that no longer resolves must be visible, not silently dropped —
    // otherwise a deleted product looks identical to one with no neighbours.
    await expect(recommendations({ kind: "similar", seed: "gone" })).rejects.toMatchObject({
      status: 404,
    });
  });
});
