import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createSellerPromotion,
  deactivateSellerPromotion,
  fetchSellerPromotions,
  setSellerPromotionActive,
  validateVoucher,
} from "./promotions";

const PROMOTION_PAYLOAD = {
  id: 3,
  store_id: 9,
  store_name: "Kalinga Crafts",
  store_slug: "kalinga-crafts",
  name: "Flash sale",
  kind: "flash_sale",
  label: "Flash sale",
  discount_type: "percentage",
  value: 15,
  min_spend: 0,
  min_qty: 1,
  is_active: true,
  campaign_id: 7,
  campaign_name: "Harvest sale",
  starts_at: "2026-09-20T00:00:00Z",
  ends_at: "2026-09-30T23:59:59Z",
};

/**
 * The CSRF preflight always succeeds; assertions target the promotion calls.
 * Same stub as orders.test.js — the accessors share `lib/api`.
 */
function mockFetch(payload, { ok = true, status = 200 } = {}) {
  const fetchMock = vi.fn(async (url) => {
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

describe("voucher accessors", () => {
  it("posts only the code and maps the server's verdict", async () => {
    const { callWith } = mockFetch({
      valid: true,
      code: "WELCOME10",
      voucher: { id: 1, code: "WELCOME10", title: "Welcome 10% off" },
      eligible_subtotal: 400,
      discount_total: 40,
    });

    const verdict = await validateVoucher("WELCOME10");

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/vouchers/validate/");
    // The client sends a code, never an amount (§16).
    expect(JSON.parse(post[1].body)).toEqual({ code: "WELCOME10" });
    expect(verdict).toEqual({
      valid: true,
      code: "WELCOME10",
      title: "Welcome 10% off",
      discountTotal: 40,
      eligibleSubtotal: 400,
    });
  });

  it("throws the refusal envelope so checkout can show the reason inline", async () => {
    mockFetch(
      {
        error: "voucher_min_spend",
        detail: "Spend at least PHP 500.00 to use this voucher.",
      },
      { ok: false, status: 400 }
    );

    await expect(validateVoucher("nope")).rejects.toMatchObject({
      status: 400,
      message: "Spend at least PHP 500.00 to use this voucher.",
      data: { error: "voucher_min_spend" },
    });
  });
});

describe("seller promotion accessors", () => {
  it("maps this store's promotions from the plain list", async () => {
    const { fetchMock } = mockFetch([PROMOTION_PAYLOAD]);

    const promos = await fetchSellerPromotions();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/seller/promotions/");
    expect(promos[0]).toMatchObject({
      id: 3,
      name: "Flash sale",
      kind: "flash_sale",
      discountType: "percentage",
      value: 15,
      minSpend: 0,
      minQty: 1,
      isActive: true,
      campaignName: "Harvest sale",
      startsAt: "2026-09-20T00:00:00Z",
      endsAt: "2026-09-30T23:59:59Z",
    });
  });

  it("creates a store-wide promotion with the snake_case wire body", async () => {
    const { callWith } = mockFetch(PROMOTION_PAYLOAD, { status: 201 });

    const promo = await createSellerPromotion({
      name: "Harvest sale",
      kind: "product_discount",
      discountType: "fixed",
      value: 50,
      minSpend: 500,
      minQty: 2,
      label: "₱50 off",
      startsAt: "2026-10-01T00:00",
      endsAt: "2026-10-07T23:59",
    });

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/seller/promotions/");
    expect(JSON.parse(post[1].body)).toEqual({
      name: "Harvest sale",
      kind: "product_discount",
      discount_type: "fixed",
      value: 50,
      min_spend: 500,
      min_qty: 2,
      target_type: "all",
      is_active: true,
      label: "₱50 off",
      starts_at: "2026-10-01T00:00",
      ends_at: "2026-10-07T23:59",
    });
    expect(promo.id).toBe(3);
  });

  it("omits the optional fields the seller left blank", async () => {
    const { callWith } = mockFetch(PROMOTION_PAYLOAD, { status: 201 });

    await createSellerPromotion({
      name: "Weekend deal",
      kind: "free_shipping",
      discountType: "percentage",
      value: 0,
    });

    expect(JSON.parse(callWith("POST")[1].body)).toEqual({
      name: "Weekend deal",
      kind: "free_shipping",
      discount_type: "percentage",
      value: 0,
      min_spend: 0,
      min_qty: 1,
      target_type: "all",
      is_active: true,
    });
  });

  it("toggles the active flag through PATCH", async () => {
    const { callWith } = mockFetch({ ...PROMOTION_PAYLOAD, is_active: false });

    const promo = await setSellerPromotionActive(3, false);

    const patch = callWith("PATCH");
    expect(patch[0]).toBe("/api/v1/seller/promotions/3/");
    expect(JSON.parse(patch[1].body)).toEqual({ is_active: false });
    expect(promo.isActive).toBe(false);
  });

  it("deactivates through DELETE without a body", async () => {
    const { callWith } = mockFetch({ status: "deactivated" });

    const result = await deactivateSellerPromotion(3);

    const del = callWith("DELETE");
    expect(del[0]).toBe("/api/v1/seller/promotions/3/");
    expect(del[1].body).toBeUndefined();
    expect(result).toEqual({ status: "deactivated" });
  });

  it("surfaces a seller-side rejection with the §8 envelope intact", async () => {
    mockFetch(
      { error: "no_store", detail: "Store not found." },
      { ok: false, status: 404 }
    );

    await expect(fetchSellerPromotions()).rejects.toMatchObject({
      status: 404,
      message: "Store not found.",
    });
  });
});
