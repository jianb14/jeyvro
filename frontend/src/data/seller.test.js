import { afterEach, describe, expect, it, vi } from "vitest";
import {
  adjustStock,
  createProduct,
  deleteProduct,
  fetchDashboard,
  fetchInventory,
  fetchMyProducts,
  fetchSellerOrders,
  fetchStockHistory,
  mapSellerProduct,
  shipSellerOrder,
  submitProduct,
  uploadProductImage,
} from "./seller";

const DASHBOARD_PAYLOAD = {
  store: { name: "Kalinga Crafts", slug: "kalinga-crafts", status: "active" },
  products: { total: 3, by_status: { published: 2, draft: 1 } },
  sales: {
    orders: 4,
    units_sold: 9,
    gross: 4580,
    average_order_value: 1145,
    last_30_days: { orders: 2, units_sold: 4, gross: 1998 },
  },
  orders: { total: 5, open: 3, by_status: { awaiting_payment: 2, delivered: 1 } },
  inventory: {
    low_stock_count: 1,
    low_stock_items: [
      {
        variant_id: 7,
        product_id: 3,
        product_title: "Woven Basket",
        sku: "woven-basket",
        available: 2,
        low_stock_threshold: 5,
      },
    ],
  },
  recent_orders: [
    {
      id: 11,
      order_number: "JV-20260925-AAAA1111",
      status: "awaiting_payment",
      item_count: 2,
      total: 647,
      customer: "Maria S.",
      placed_at: "2026-09-24T10:00:00Z",
    },
  ],
  recent_reviews: [],
};

const PRODUCT_PAYLOAD = {
  id: 3,
  title: "Woven Basket",
  slug: "woven-basket",
  description: "Handwoven.",
  status: "draft",
  rejection_reason: "",
  base_price: "349.00",
  compare_at_price: "499.00",
  display_price: "349.00",
  discount_percent: 30,
  category: 2,
  brand: null,
  variants: [
    {
      id: 7,
      sku: "woven-basket",
      name: "Default",
      price: "349.00",
      is_default: true,
      is_active: true,
      inventory: {
        on_hand: 12,
        reserved: 2,
        available: 10,
        low_stock_threshold: 5,
        low_stock: false,
      },
    },
  ],
  images: [{ id: 9, image: "/media/products/a.png", alt_text: "", position: 0 }],
  created_at: "2026-09-20T08:00:00Z",
  updated_at: "2026-09-21T08:00:00Z",
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

describe("seller accessors", () => {
  it("maps the dashboard envelope to the component contract", async () => {
    const fetchMock = mockFetch(DASHBOARD_PAYLOAD);
    const data = await fetchDashboard();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/stores/my/dashboard");
    expect(data.sales.averageOrderValue).toBe(1145);
    expect(data.sales.last30Days.gross).toBe(1998);
    expect(data.orders.open).toBe(3);
    expect(data.inventory.lowStockItems[0].variantId).toBe(7);
    expect(data.recentOrders[0].orderNumber).toBe("JV-20260925-AAAA1111");
    expect(data.recentReviews).toEqual([]);
  });

  it("maps seller products with numeric variant prices and stock totals", async () => {
    const fetchMock = mockFetch({ count: 1, items: [PRODUCT_PAYLOAD] });
    const data = await fetchMyProducts({ q: "basket", status: "draft", page: 2 });

    const [item] = data.items;
    expect(item.variants[0].price).toBe(349);
    expect(item.variants[0].inventory.available).toBe(10);
    expect(item.stockTotal).toBe(10);
    expect(item.discountPercent).toBe(30);
    expect(item.images[0].url).toBe("/media/products/a.png");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/catalog/my/products/?");
    expect(url).toContain("q=basket");
    expect(url).toContain("status=draft");
    expect(url).toContain("page=2");
  });

  it("posts product creation as JSON and lifecycle transitions as actions", async () => {
    const fetchMock = mockFetch(PRODUCT_PAYLOAD);
    await createProduct({ title: "Woven Basket", base_price: "349.00" });
    const [url, options] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/v1/catalog/my/products/");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      title: "Woven Basket",
      base_price: "349.00",
    });

    await submitProduct(3);
    // The CSRF preflight is a fetch of its own, so find the call by URL
    // instead of counting positions (same convention as cart.test.js).
    const submitCall = fetchMock.mock.calls.find(
      ([callUrl]) => callUrl === "/api/v1/catalog/my/products/3/submit/"
    );
    expect(submitCall).toBeTruthy();
    expect(submitCall[1].method).toBe("POST");
  });

  it("reports the server's delete decision (deleted vs archived)", async () => {
    mockFetch({
      action: "archived",
      detail: "Product archived — past orders keep their history.",
      product: { ...PRODUCT_PAYLOAD, status: "archived" },
    });
    const result = await deleteProduct(3);
    expect(result.action).toBe("archived");
    expect(result.product.status).toBe("archived");
    expect(mapSellerProduct(PRODUCT_PAYLOAD).status).toBe("draft");
  });

  it("maps inventory rows and filters low stock server-side", async () => {
    const fetchMock = mockFetch({
      count: 1,
      items: [
        {
          variant_id: 7,
          product_id: 3,
          product_title: "Woven Basket",
          product_slug: "woven-basket",
          product_status: "published",
          sku: "woven-basket",
          name: "Default",
          price: "349.00",
          is_active: true,
          inventory: {
            on_hand: 2,
            reserved: 0,
            available: 2,
            low_stock_threshold: 5,
            low_stock: true,
          },
        },
      ],
    });
    const data = await fetchInventory({ lowStock: true });

    expect(data.items[0].inventory.lowStock).toBe(true);
    expect(data.items[0].price).toBe(349);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/catalog/my/stock?low_stock=1"
    );
  });

  it("sends stock adjustments and maps the movement history", async () => {
    const fetchMock = mockFetch({
      id: 7,
      sku: "woven-basket",
      name: "Default",
      price: "349.00",
      is_default: true,
      is_active: true,
      inventory: {
        on_hand: 8,
        reserved: 0,
        available: 8,
        low_stock_threshold: 5,
        low_stock: false,
      },
    });
    const variant = await adjustStock({
      variantId: 7,
      delta: -4,
      note: "damaged",
    });
    const [url, options] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/v1/catalog/my/stock");
    expect(JSON.parse(options.body)).toEqual({
      variant_id: 7,
      delta: -4,
      note: "damaged",
    });
    expect(variant.inventory.onHand).toBe(8);

    mockFetch({
      count: 1,
      items: [
        {
          id: 4,
          reason: "adjustment",
          quantity_delta: -4,
          resulting_on_hand: 8,
          note: "damaged",
          created_at: "2026-09-25T09:00:00Z",
        },
      ],
    });
    const history = await fetchStockHistory(7);
    expect(history.items[0].delta).toBe(-4);
    expect(history.items[0].resultingOnHand).toBe(8);
  });

  it("maps seller orders with privacy context and action flags", async () => {
    const fetchMock = mockFetch({
      count: 1,
      items: [
        {
          id: 11,
          order_number: "JV-20260925-AAAA1111",
          placed_at: "2026-09-24T10:00:00Z",
          store_slug: "kalinga-crafts",
          store_name: "Kalinga Crafts",
          status: "awaiting_payment",
          item_count: 2,
          subtotal: 598,
          shipping_fee: 49,
          total: 647,
          items: [
            {
              id: 1,
              product_slug: "woven-basket",
              title: "Woven Basket",
              variant_name: "Default",
              sku: "woven-basket",
              unit_price: 299,
              quantity: 2,
              line_total: 598,
            },
          ],
          shipments: [],
          payment: {
            method: "cod",
            method_label: "Cash on Delivery",
            status: "pending",
            paid: false,
          },
          customer: {
            name: "Maria S.",
            phone: "•••••••4567",
            city: "Manila",
            province: "Metro Manila",
            postal_code: "1000",
            address: null,
            revealed: false,
          },
          can_process: true,
          can_pack: true,
          can_ship: true,
        },
      ],
    });
    const data = await fetchSellerOrders({
      status: "awaiting_payment",
      q: "JV-",
    });

    const [order] = data.items;
    expect(order.orderNumber).toBe("JV-20260925-AAAA1111");
    expect(order.customer.revealed).toBe(false);
    expect(order.customer.address).toBeNull();
    expect(order.canProcess).toBe(true);
    expect(order.payment.methodLabel).toBe("Cash on Delivery");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/seller/orders/?");
    expect(url).toContain("status=awaiting_payment");
    expect(url).toContain("q=JV-");
  });

  it("posts parcel details when shipping and FormData when uploading images", async () => {
    const fetchMock = mockFetch({
      id: 11,
      order_number: "JV-1",
      store_slug: "kalinga-crafts",
      store_name: "Kalinga Crafts",
      status: "shipped",
      items: [],
      shipments: [],
    });
    await shipSellerOrder(11, { carrier: "jtexpress", notes: "Fragile" });
    const shipBody = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(shipBody).toEqual({
      carrier: "jtexpress",
      package_notes: "Fragile",
    });

    const uploadMock = mockFetch({
      id: 9,
      image: "/media/products/b.png",
      alt_text: "B",
      position: 1,
    });
    const file = new File(["x"], "b.png", { type: "image/png" });
    await uploadProductImage(3, file, { altText: "B", position: 1 });
    // call 0 is the CSRF preflight, call 1 is the multipart upload.
    const [url, options] = uploadMock.mock.calls[1];
    expect(url).toBe("/api/v1/catalog/my/products/3/images/");
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.headers["Content-Type"]).toBeUndefined();
  });
});
