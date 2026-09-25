import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cancelOrder,
  createOrderRequest,
  fetchCheckout,
  fetchOrder,
  fetchOrders,
  placeOrder,
  reorderOrder,
  withdrawOrderRequest,
} from "./orders";

const CHECKOUT_PAYLOAD = {
  items: [
    {
      id: 11,
      variant_id: 42,
      product_slug: "woven-basket",
      title: "Woven Basket",
      variant_name: "Default",
      sku: "woven-basket",
      price: 299,
      compare_at_price: 399,
      discount: 25,
      quantity: 2,
      line_total: 598,
      available: 10,
      purchasable: true,
      unavailable_reason: "",
      stock_limited: false,
      primary_image: null,
      store_slug: "kalinga-crafts",
      store_name: "Kalinga Crafts",
    },
  ],
  groups: [
    {
      store_slug: "kalinga-crafts",
      store_name: "Kalinga Crafts",
      item_count: 2,
      subtotal: 598,
      shipping_fee: 49,
      free_shipping: false,
      items: [],
    },
  ],
  totals: {
    line_count: 1,
    item_count: 2,
    subtotal: 598,
    savings: 200,
    shipping_total: 49,
    tax_total: 0,
    grand_total: 647,
  },
  issues: [],
  payment_methods: [
    {
      id: "cod",
      label: "Cash on Delivery",
      description: "Pay in cash when your order arrives — no online payment needed.",
      available: true,
    },
    {
      id: "gcash",
      label: "GCash",
      description: "Coming soon — online payments need the gateway integration.",
      available: false,
    },
  ],
  checkout_ready: true,
};

const ORDER_PAYLOAD = {
  number: "JV-20260925-ABCD2345",
  status: "awaiting_payment",
  created_at: "2026-09-25T08:00:00Z",
  item_count: 2,
  payment: {
    reference: "JVPAY-20260925-ABCD2345",
    method: "cod",
    status: "pending",
    amount: 647,
    currency: "PHP",
    provider: "cod",
    checkout_url: null,
    paid_at: null,
    expires_at: null,
    refunded_total: 0,
  },
  shipping_address: {
    full_name: "Bianca Buyer",
    phone: "09171234567",
    line1: "12 Mabini Street",
    line2: "Unit 4B",
    city: "Quezon City",
    province: "Metro Manila",
    postal_code: "1100",
  },
  totals: {
    subtotal: 598,
    shipping_total: 49,
    savings_total: 200,
    tax_total: 0,
    grand_total: 647,
  },
  seller_orders: [
    {
      id: 3,
      store_slug: "kalinga-crafts",
      store_name: "Kalinga Crafts",
      status: "placed",
      subtotal: 598,
      shipping_fee: 49,
      total: 647,
      items: [
        {
          id: 11,
          product_slug: "woven-basket",
          title: "Woven Basket",
          variant_name: "Default",
          sku: "woven-basket",
          unit_price: 299,
          compare_at_price: 399,
          quantity: 2,
          line_total: 598,
        },
      ],
      shipments: [
        {
          id: 7,
          tracking_number: "JVTRK-20260925-ABCD2345",
          carrier: "manual",
          carrier_name: "Standard Delivery",
          shipping_method: "standard",
          shipping_fee: 49,
          status: "in_transit",
          shipped_at: "2026-09-25T10:00:00Z",
          estimated_delivery: null,
          delivered_at: null,
          recipient_name: "Bianca Buyer",
          recipient_phone: "09171234567",
          items: [
            {
              id: 5,
              order_item_id: 11,
              product_title: "Woven Basket",
              variant_name: "Default",
              sku: "woven-basket",
              quantity: 2,
            },
          ],
          tracking_events: [
            {
              id: 1,
              status: "picked_up",
              location: "Kalinga Crafts",
              description: "Parcel picked up by the courier.",
              occurred_at: "2026-09-25T10:00:00Z",
            },
            {
              id: 2,
              status: "in_transit",
              location: "Manila hub",
              description: "In transit to destination sorting hub.",
              occurred_at: "2026-09-25T12:00:00Z",
            },
          ],
        },
      ],
    },
  ],
  can_cancel: false,
  timeline: [
    {
      title: "Order placed",
      description: "",
      tone: "success",
      occurred_at: "2026-09-25T08:00:00Z",
    },
    {
      title: "In transit",
      description: "Tracking JVTRK-20260925-ABCD2345 · Manila hub",
      tone: "info",
      occurred_at: "2026-09-25T12:00:00Z",
    },
  ],
  requests: [
    {
      id: 4,
      kind: "issue",
      kind_label: "Report an issue",
      status: "pending",
      reason: "Delivery is late",
      description: "",
      seller_order_id: 3,
      store_name: "Kalinga Crafts",
      created_at: "2026-09-26T09:00:00Z",
    },
  ],
};

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async (url) => {
    // CSRF preflight always succeeds; assertions target the order calls.
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

describe("order accessors", () => {
  it("maps the checkout preview with per-store shipping to the component contract", async () => {
    const { fetchMock } = mockFetch(CHECKOUT_PAYLOAD);
    const checkout = await fetchCheckout();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/checkout/");
    expect(checkout.ready).toBe(true);
    expect(checkout.issues).toEqual([]);
    expect(checkout.paymentMethods).toEqual([
      {
        id: "cod",
        label: "Cash on Delivery",
        description: "Pay in cash when your order arrives — no online payment needed.",
        available: true,
      },
      {
        id: "gcash",
        label: "GCash",
        description: "Coming soon — online payments need the gateway integration.",
        available: false,
      },
    ]);
    expect(checkout.groups[0].shippingFee).toBe(49);
    expect(checkout.groups[0].freeShipping).toBe(false);
    expect(checkout.totals.shipping).toBe(49);
    expect(checkout.totals.grandTotal).toBe(647);
    expect(checkout.items[0].price).toBe(299);
    expect(checkout.items[0].originalPrice).toBe(399);
  });

  it("surfaces blocked lines as issues", async () => {
    mockFetch({
      ...CHECKOUT_PAYLOAD,
      issues: [
        { item_id: 11, title: "Woven Basket", reason: "Only 1 left in stock." },
      ],
      checkout_ready: false,
    });
    const checkout = await fetchCheckout();
    expect(checkout.ready).toBe(false);
    expect(checkout.issues[0]).toEqual({
      itemId: 11,
      title: "Woven Basket",
      reason: "Only 1 left in stock.",
    });
  });

  it("places an order with only the address id and payment method in the body", async () => {
    const { callWith } = mockFetch(ORDER_PAYLOAD, { status: 201 });
    const order = await placeOrder(7, "cod");

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/checkout/orders");
    expect(JSON.parse(post[1].body)).toEqual({
      address_id: 7,
      payment_method: "cod",
    });
    expect(order.number).toBe("JV-20260925-ABCD2345");
    expect(order.status).toBe("awaiting_payment");
    expect(order.payment.method).toBe("cod");
    expect(order.payment.methodLabel).toBe("Cash on Delivery");
    expect(order.payment.status).toBe("pending");
    expect(order.payment.amount).toBe(647);
    expect(order.payment.expiresAt).toBeNull();
    expect(order.payment.refundedTotal).toBe(0);
    expect(order.totals.grandTotal).toBe(647);
    expect(order.address.line1).toBe("12 Mabini Street");
    expect(order.sellerOrders[0].storeName).toBe("Kalinga Crafts");
    expect(order.sellerOrders[0].shippingFee).toBe(49);
    expect(order.sellerOrders[0].items[0].qty).toBe(2);
  });

  it("fetches and cancels one order by number", async () => {
    const { callWith } = mockFetch(ORDER_PAYLOAD);
    const order = await fetchOrder("JV-20260925-ABCD2345");
    expect(order.status).toBe("awaiting_payment");

    await cancelOrder("JV-20260925-ABCD2345");
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/orders/JV-20260925-ABCD2345/cancel");
  });

  it("throws the §8 error envelope, message and status intact", async () => {
    mockFetch(
      { error: "insufficient_stock", detail: "Basket: only 1 left in stock." },
      { ok: false, status: 400 }
    );
    await expect(placeOrder(7)).rejects.toMatchObject({
      status: 400,
      message: "Basket: only 1 left in stock.",
    });
  });

  it("maps order history rows from the {count, items} envelope", async () => {
    const { fetchMock } = mockFetch({
      count: 1,
      items: [
        {
          number: "JV-20260925-ABCD2345",
          status: "delivered",
          created_at: "2026-09-25T08:00:00Z",
          item_count: 2,
          grand_total: 647,
          store_names: ["Kalinga Crafts"],
          can_cancel: false,
        },
      ],
    });
    const page = await fetchOrders({ page: 2, pageSize: 10 });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/orders/?page=2&page_size=10"
    );
    expect(page.count).toBe(1);
    expect(page.items[0]).toEqual({
      number: "JV-20260925-ABCD2345",
      status: "delivered",
      placedAt: "2026-09-25T08:00:00Z",
      itemCount: 2,
      grandTotal: 647,
      storeNames: ["Kalinga Crafts"],
      canCancel: false,
    });
  });

  it("maps shipments, tracking events, timeline and requests on the order", async () => {
    mockFetch(ORDER_PAYLOAD);
    const order = await fetchOrder("JV-20260925-ABCD2345");

    const shipment = order.sellerOrders[0].shipments[0];
    expect(shipment.trackingNumber).toBe("JVTRK-20260925-ABCD2345");
    expect(shipment.carrierName).toBe("Standard Delivery");
    expect(shipment.status).toBe("in_transit");
    expect(shipment.events.map((event) => event.status)).toEqual([
      "picked_up",
      "in_transit",
    ]);
    expect(shipment.events[1].occurredAt).toBe("2026-09-25T12:00:00Z");

    expect(order.canCancel).toBe(false);
    expect(order.timeline.map((step) => step.title)).toEqual([
      "Order placed",
      "In transit",
    ]);
    expect(order.timeline[1].time).toBe("2026-09-25T12:00:00Z");

    expect(order.requests[0]).toMatchObject({
      id: 4,
      kind: "issue",
      kindLabel: "Report an issue",
      status: "pending",
      reason: "Delivery is late",
      sellerOrderId: 3,
      storeName: "Kalinga Crafts",
    });
  });

  it("reorder posts to the reorder endpoint and returns added/skipped lines", async () => {
    const { callWith } = mockFetch({
      added: [{ title: "Woven Basket", variant_name: "Default", quantity: 2 }],
      skipped: [{ title: "Dead Item", reason: "This item is out of stock." }],
      cart_item_count: 2,
    });
    const result = await reorderOrder("JV-20260925-ABCD2345");

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/orders/JV-20260925-ABCD2345/reorder");
    expect(result.added).toHaveLength(1);
    expect(result.skipped[0].reason).toBe("This item is out of stock.");
    expect(result.cartItemCount).toBe(2);
  });

  it("creates and withdraws order requests with the server's shape", async () => {
    const { fetchMock, callWith } = mockFetch({
      id: 9,
      kind: "return",
      kind_label: "Return",
      status: "pending",
      reason: "Changed my mind",
      description: "Unopened",
      seller_order_id: null,
      store_name: "",
      created_at: "2026-09-26T09:00:00Z",
    });
    const created = await createOrderRequest("JV-20260925-ABCD2345", {
      kind: "return",
      reason: "Changed my mind",
      description: "Unopened",
    });

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/orders/JV-20260925-ABCD2345/requests");
    expect(JSON.parse(post[1].body)).toEqual({
      kind: "return",
      reason: "Changed my mind",
      description: "Unopened",
    });
    expect(created.kindLabel).toBe("Return");
    expect(created.status).toBe("pending");

    await withdrawOrderRequest("JV-20260925-ABCD2345", 9);
    const posts = fetchMock.mock.calls.filter(
      ([, options]) => options?.method === "POST"
    );
    expect(posts[1][0]).toBe(
      "/api/v1/orders/JV-20260925-ABCD2345/requests/9/withdraw"
    );
  });
});
