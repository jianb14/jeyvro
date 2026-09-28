import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createSellerPromotion,
  createStaffCampaign,
  deactivateSellerPromotion,
  fetchPublicVouchers,
  fetchSellerPromotions,
  fetchStaffCampaigns,
  fetchStaffPromotions,
  setSellerPromotionActive,
  validateVoucher,
} from "./promotions";

const VOUCHER_PAYLOAD = {
  id: 12,
  code: "WELCOME10",
  title: "Welcome 10% off",
  description: "First order treat.",
  scope: "platform",
  store_id: null,
  store_name: null,
  store_slug: null,
  funded_by: "platform",
  discount_type: "percentage",
  value: 10,
  min_spend: 500,
  max_discount: 150,
  first_order_only: true,
  starts_at: "2026-09-01T00:00:00Z",
  ends_at: "2026-12-31T23:59:59Z",
  usage_limit: 100,
  per_user_limit: 1,
};

const CAMPAIGN_PAYLOAD = {
  id: 7,
  name: "Harvest sale",
  scope: "platform",
  store_id: null,
  store_name: null,
  description: "September marketplace-wide sale.",
  starts_at: "2026-09-20T00:00:00Z",
  ends_at: "2026-09-30T23:59:59Z",
  is_active: true,
  promotion_count: 3,
};

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

describe("voucher center accessor", () => {
  it("maps the public-safe voucher shape and never asks for counters", async () => {
    const { fetchMock } = mockFetch([VOUCHER_PAYLOAD]);

    const vouchers = await fetchPublicVouchers();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/vouchers/");
    expect(vouchers[0]).toEqual({
      id: 12,
      code: "WELCOME10",
      title: "Welcome 10% off",
      description: "First order treat.",
      scope: "platform",
      storeId: null,
      storeName: "",
      storeSlug: "",
      fundedBy: "platform",
      discountType: "percentage",
      value: 10,
      minSpend: 500,
      maxDiscount: 150,
      firstOrderOnly: true,
      startsAt: "2026-09-01T00:00:00Z",
      endsAt: "2026-12-31T23:59:59Z",
      usageLimit: 100,
      perUserLimit: 1,
    });
  });

  it("sends the scope filter as a query param", async () => {
    const { fetchMock } = mockFetch([VOUCHER_PAYLOAD]);

    await fetchPublicVouchers({ scope: "platform" });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/vouchers/?scope=platform");
  });

  it("prefers the store filter over the scope the server would ignore", async () => {
    const { fetchMock } = mockFetch([VOUCHER_PAYLOAD]);

    await fetchPublicVouchers({ store: "kalinga-crafts", scope: "seller" });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/vouchers/?store=kalinga-crafts"
    );
  });

  it("keeps a null max_discount null instead of inventing a cap", async () => {
    mockFetch([{ ...VOUCHER_PAYLOAD, max_discount: null, ends_at: null }]);

    const [voucher] = await fetchPublicVouchers();

    expect(voucher.maxDiscount).toBeNull();
    expect(voucher.endsAt).toBeNull();
  });

  it("names the store behind a seller voucher so the card can link it", async () => {
    mockFetch([
      {
        ...VOUCHER_PAYLOAD,
        scope: "seller",
        store_id: 9,
        store_name: "Kalinga Crafts",
        store_slug: "kalinga-crafts",
      },
    ]);

    const [voucher] = await fetchPublicVouchers({ scope: "seller" });

    expect(voucher.scope).toBe("seller");
    expect(voucher.storeName).toBe("Kalinga Crafts");
    expect(voucher.storeSlug).toBe("kalinga-crafts");
  });
});

describe("staff campaign console accessors", () => {
  it("lists campaigns from the plain list and maps the count the server sends", async () => {
    const { fetchMock } = mockFetch([CAMPAIGN_PAYLOAD]);

    const campaigns = await fetchStaffCampaigns();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/staff/campaigns/");
    expect(campaigns[0]).toEqual({
      id: 7,
      name: "Harvest sale",
      scope: "platform",
      storeId: null,
      storeName: "",
      description: "September marketplace-wide sale.",
      startsAt: "2026-09-20T00:00:00Z",
      endsAt: "2026-09-30T23:59:59Z",
      isActive: true,
      promotionCount: 3,
    });
  });

  it("creates a platform campaign with the snake_case body only", async () => {
    const { callWith } = mockFetch(CAMPAIGN_PAYLOAD, { status: 201 });

    const campaign = await createStaffCampaign({
      name: "Harvest sale",
      description: "September marketplace-wide sale.",
      startsAt: "2026-09-20T00:00",
      endsAt: "2026-09-30T23:59",
    });

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/staff/campaigns/");
    expect(JSON.parse(post[1].body)).toEqual({
      name: "Harvest sale",
      description: "September marketplace-wide sale.",
      is_active: true,
      starts_at: "2026-09-20T00:00",
      ends_at: "2026-09-30T23:59",
    });
    expect(campaign.id).toBe(7);
  });

  it("omits blank dates so an always-on campaign stays always-on", async () => {
    const { callWith } = mockFetch(CAMPAIGN_PAYLOAD, { status: 201 });

    await createStaffCampaign({ name: "Always on", isActive: false });

    expect(JSON.parse(callWith("POST")[1].body)).toEqual({
      name: "Always on",
      description: "",
      is_active: false,
    });
  });

  it("lists platform-wide promotions for oversight", async () => {
    const { fetchMock } = mockFetch([PROMOTION_PAYLOAD]);

    const promos = await fetchStaffPromotions();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/staff/promotions/");
    expect(promos[0]).toMatchObject({
      id: 3,
      kind: "flash_sale",
      campaignName: "Harvest sale",
      storeName: "Kalinga Crafts",
      storeSlug: "kalinga-crafts",
    });
  });

  it("surfaces the staff gate's refusal with the §8 envelope intact", async () => {
    mockFetch(
      { error: "forbidden", detail: "Staff access required." },
      { ok: false, status: 403 }
    );

    await expect(fetchStaffCampaigns()).rejects.toMatchObject({
      status: 403,
      message: "Staff access required.",
    });
  });
});
