import { afterEach, describe, expect, it, vi } from "vitest";
import { addCartItem, clearCart, fetchCart, removeCartItem, updateCartItem } from "./cart";

const CART_PAYLOAD = {
  id: 7,
  owner: "guest",
  items: [
    {
      id: 11,
      variant_id: 42,
      product_slug: "woven-basket",
      title: "Woven Basket",
      variant_name: "Default",
      sku: "woven-basket",
      price: 349,
      compare_at_price: 499,
      discount: 30,
      quantity: 2,
      line_total: 698,
      available: 10,
      purchasable: true,
      unavailable_reason: "",
      stock_limited: false,
      primary_image: "http://api/media/products/a.png",
      store_slug: "kalinga-crafts",
      store_name: "Kalinga Crafts",
      promotion_savings: 30,
      promotion_label: "Flash sale",
    },
  ],
  groups: [
    {
      store_slug: "kalinga-crafts",
      store_name: "Kalinga Crafts",
      item_count: 2,
      subtotal: 698,
      promotion_discount: 30,
      items: [],
    },
  ],
  totals: {
    line_count: 1,
    item_count: 2,
    subtotal: 698,
    savings: 300,
    promotion_discount: 30,
    items_total: 668,
    max_order_units: 200,
    over_unit_ceiling: false,
  },
};

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async (url) => {
    // CSRF preflight always succeeds; assertions target the cart calls.
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

describe("cart accessors", () => {
  it("maps the server payload to the component contract", async () => {
    const { fetchMock } = mockFetch(CART_PAYLOAD);
    const cart = await fetchCart();

    expect(cart.owner).toBe("guest");
    expect(cart.totals.itemCount).toBe(2);
    expect(cart.totals.subtotal).toBe(698);
    expect(cart.items[0].qty).toBe(2);
    expect(cart.items[0].lineTotal).toBe(698);
    expect(cart.items[0].originalPrice).toBe(499);
    expect(cart.items[0].stock).toBe(10);
    expect(cart.items[0].productSlug).toBe("woven-basket");
    expect(cart.items[0].storeSlug).toBe("kalinga-crafts");
    expect(cart.groups[0].storeName).toBe("Kalinga Crafts");
    expect(typeof cart.items[0].seed).toBe("number");
    // §16.2 — the engine's numbers are mapped, never recomputed.
    expect(cart.totals.promotionDiscount).toBe(30);
    expect(cart.totals.itemsTotal).toBe(668);
    expect(cart.groups[0].promotionDiscount).toBe(30);
    expect(cart.items[0].promotionSavings).toBe(30);
    expect(cart.items[0].promotionLabel).toBe("Flash sale");
    // §20.2 v3 — the ceiling is the server's number, mapped not recomputed, so
    // a 2-item cart reads as comfortably under the limit.
    expect(cart.totals.maxOrderUnits).toBe(200);
    expect(cart.totals.overUnitCeiling).toBe(false);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/cart/");
  });

  it("flags a cart the server says is over the unit ceiling", async () => {
    mockFetch({
      ...CART_PAYLOAD,
      totals: {
        ...CART_PAYLOAD.totals,
        item_count: 270,
        max_order_units: 200,
        over_unit_ceiling: true,
      },
    });

    const cart = await fetchCart();

    // The verdict is the server's; the client never decides it for itself.
    expect(cart.totals.itemCount).toBe(270);
    expect(cart.totals.maxOrderUnits).toBe(200);
    expect(cart.totals.overUnitCeiling).toBe(true);
  });

  it("defaults the ceiling hint safely when the server omits it", async () => {
    const legacyTotals = { ...CART_PAYLOAD.totals };
    delete legacyTotals.max_order_units;
    delete legacyTotals.over_unit_ceiling;
    mockFetch({ ...CART_PAYLOAD, totals: legacyTotals });

    const cart = await fetchCart();

    // An older backend must not make the cart claim it is over a limit it
    // never heard of.
    expect(cart.totals.maxOrderUnits).toBeNull();
    expect(cart.totals.overUnitCeiling).toBe(false);
  });

  it("sends add/update/remove to the right URLs with the right verbs", async () => {
    const { callWith } = mockFetch(CART_PAYLOAD);

    await addCartItem(42, 2);
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/cart/items");
    expect(JSON.parse(post[1].body)).toEqual({ variant_id: 42, quantity: 2 });

    await updateCartItem(11, 3);
    const patch = callWith("PATCH");
    expect(patch[0]).toBe("/api/v1/cart/items/11");
    expect(JSON.parse(patch[1].body)).toEqual({ quantity: 3 });

    await removeCartItem(11);
    const remove = callWith("DELETE");
    expect(remove[0]).toBe("/api/v1/cart/items/11");
  });

  it("throws the §8 error envelope, message and status intact", async () => {
    mockFetch(
      { error: "cart_item_rejected", detail: "Only 3 left in stock." },
      { ok: false, status: 400 }
    );
    await expect(addCartItem(42, 4)).rejects.toMatchObject({
      status: 400,
      message: "Only 3 left in stock.",
    });
  });

  it("clears the cart through a DELETE on the cart root", async () => {
    const { callWith } = mockFetch({
      ...CART_PAYLOAD,
      items: [],
      groups: [],
      totals: { line_count: 0, item_count: 0, subtotal: 0, savings: 0 },
    });
    const cart = await clearCart();
    const remove = callWith("DELETE");
    expect(remove[0]).toBe("/api/v1/cart/");
    expect(cart.totals.itemCount).toBe(0);
  });
});

