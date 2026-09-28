import { afterEach, describe, expect, it, vi } from "vitest";
import { getSuggestions, searchResults } from "./search";

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
