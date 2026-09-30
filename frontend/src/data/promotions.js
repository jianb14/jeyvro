/**
 * Promotions & vouchers accessors (Phase 16 — ROADMAP §16.1, §16.2, §16.4).
 *
 * The ONLY data access point for the promotion engine's wire contract:
 * - `validateVoucher` posts a code (never an amount) and returns the
 *   server's verdict for display;
 * - `fetchPublicVouchers` feeds the browse-side voucher center;
 * - the seller CRUD accessors drive `/api/v1/seller/promotions/`;
 * - the staff accessors drive `/api/v1/staff/campaigns/` and
 *   `/api/v1/staff/promotions/` (the operator console).
 * Every number here is computed by the backend — components render it and
 * never recalculate (marketplace rule 1).
 */
import { ensureCsrfToken, request } from "../lib/api";

const BASE = "/api/v1";

/** serialize_promotion (backend) → the component contract. */
export function mapPromotion(p) {
  return {
    id: p.id,
    name: p.name ?? "",
    label: p.label ?? "",
    kind: p.kind,
    discountType: p.discount_type,
    value: p.value ?? 0,
    minSpend: p.min_spend ?? 0,
    minQty: p.min_qty ?? 1,
    isActive: Boolean(p.is_active),
    campaignId: p.campaign_id,
    campaignName: p.campaign_name ?? "",
    startsAt: p.starts_at ?? null,
    endsAt: p.ends_at ?? null,
    storeId: p.store_id ?? null,
    storeName: p.store_name ?? "",
    storeSlug: p.store_slug ?? "",
    // Buy-X-get-Y carries its own pair — the console renders which two
    // products the rule couples, straight from the server's ids.
    buyProductId: p.buy_product_id ?? null,
    buyQty: p.buy_qty ?? null,
    getProductId: p.get_product_id ?? null,
    getQty: p.get_qty ?? null,
  };
}

/**
 * serialize_voucher (backend) → the component contract. Public-safe: the
 * engine's counters are never exposed, so the center shows the rule and the
 * window, and redemption stays a server verdict.
 */
export function mapVoucher(v) {
  return {
    id: v.id,
    code: v.code ?? "",
    title: v.title ?? "",
    description: v.description ?? "",
    scope: v.scope,
    storeId: v.store_id ?? null,
    // Store vouchers name and link their store; platform vouchers carry none.
    storeName: v.store_name ?? "",
    storeSlug: v.store_slug ?? "",
    fundedBy: v.funded_by,
    discountType: v.discount_type,
    value: v.value ?? 0,
    minSpend: v.min_spend ?? 0,
    maxDiscount: v.max_discount ?? null,
    firstOrderOnly: Boolean(v.first_order_only),
    startsAt: v.starts_at ?? null,
    endsAt: v.ends_at ?? null,
    usageLimit: v.usage_limit ?? null,
    perUserLimit: v.per_user_limit ?? null,
  };
}

/** serialize_campaign (backend) → the component contract. */
export function mapCampaign(c) {
  return {
    id: c.id,
    name: c.name ?? "",
    scope: c.scope,
    storeId: c.store_id ?? null,
    storeName: c.store_name ?? "",
    description: c.description ?? "",
    startsAt: c.starts_at ?? null,
    endsAt: c.ends_at ?? null,
    isActive: Boolean(c.is_active),
    promotionCount: c.promotion_count ?? 0,
  };
}

/**
 * POST /api/v1/vouchers/validate/ — the code alone; the response carries
 * {code, title, discountTotal, eligibleSubtotal}. A refusal throws with
 * the server's `{error, detail}` attached (`.data`) for inline display.
 */
export async function validateVoucher(code) {
  const csrf = await ensureCsrfToken();
  const data = await request(BASE, "/vouchers/validate/", {
    method: "POST",
    body: { code },
    csrf,
  });
  return {
    valid: Boolean(data.valid),
    code: data.code ?? "",
    title: data.voucher?.title ?? "",
    discountTotal: data.discount_total ?? 0,
    eligibleSubtotal: data.eligible_subtotal ?? 0,
  };
}

/** GET /api/v1/seller/promotions/ — this store's promotions (plain list). */
export async function fetchSellerPromotions() {
  const data = await request(BASE, "/seller/promotions/");
  return (Array.isArray(data) ? data : (data.items ?? [])).map(mapPromotion);
}

/**
 * POST /api/v1/seller/promotions/ — creates the campaign + promotion.
 * Takes camelCase form values; the server owns every rule and number.
 */
export async function createSellerPromotion(payload) {
  const csrf = await ensureCsrfToken();
  const body = {
    name: payload.name,
    kind: payload.kind,
    discount_type: payload.discountType ?? "percentage",
    value: payload.value ?? 0,
    min_spend: payload.minSpend ?? 0,
    min_qty: payload.minQty ?? 1,
    target_type: payload.targetType ?? "all",
    is_active: payload.isActive ?? true,
  };
  if (payload.label) body.label = payload.label;
  if (payload.startsAt) body.starts_at = payload.startsAt;
  if (payload.endsAt) body.ends_at = payload.endsAt;
  return mapPromotion(
    await request(BASE, "/seller/promotions/", { method: "POST", body, csrf })
  );
}

/** PATCH /api/v1/seller/promotions/<id>/ — flip the active flag. */
export async function setSellerPromotionActive(id, isActive) {
  const csrf = await ensureCsrfToken();
  return mapPromotion(
    await request(BASE, `/seller/promotions/${id}/`, {
      method: "PATCH",
      body: { is_active: Boolean(isActive) },
      csrf,
    })
  );
}

/**
 * DELETE /api/v1/seller/promotions/<id>/ — deactivates (never hard-deletes)
 * and returns `{status: "deactivated"}`.
 */
export async function deactivateSellerPromotion(id) {
  const csrf = await ensureCsrfToken();
  return request(BASE, `/seller/promotions/${id}/`, {
    method: "DELETE",
    csrf,
  });
}

// --- Voucher center (public, §16.4) -----------------------------------------

/**
 * GET /api/v1/vouchers/ — the active vouchers the center browses. Public and
 * anonymous-safe: the server returns only its public-safe voucher shape, so
 * the page can render a code without ever learning the redemption counters.
 * `store` narrows to one store's vouchers; otherwise `scope` picks
 * `platform` / `seller` (the server ignores `scope` when `store` is sent).
 */
export async function fetchPublicVouchers({ store = "", scope = "" } = {}) {
  const params = new URLSearchParams();
  if (store) params.set("store", store);
  else if (scope) params.set("scope", scope);
  const query = params.toString();
  const data = await request(BASE, `/vouchers/${query ? `?${query}` : ""}`);
  return (Array.isArray(data) ? data : (data.items ?? [])).map(mapVoucher);
}

/**
 * GET /api/v1/campaigns/ — the active campaigns the storefront promo strip
 * renders. Public and anonymous-safe (backend apps/promotions/views.py).
 *
 * The server has already filtered to `is_active=True` and applied no window
 * check of its own, so a client must not assume every row is currently live —
 * the strip reads `endsAt` and drops anything already finished rather than
 * advertising a "Summer Sale" that expired last month.
 *
 * Every number here is the server's: `promotionCount` is the real count of
 * rules inside the campaign, never a discount percentage invented client-side.
 */
export async function fetchPublicCampaigns() {
  const data = await request(BASE, "/campaigns/");
  return (Array.isArray(data) ? data : (data.items ?? [])).map(mapCampaign);
}

// --- Staff campaign & promotion console (§16.4) -----------------------------

/** GET /api/v1/staff/campaigns/ — every campaign, newest first (plain list). */
export async function fetchStaffCampaigns() {
  const data = await request(BASE, "/staff/campaigns/");
  return (Array.isArray(data) ? data : (data.items ?? [])).map(mapCampaign);
}

/**
 * POST /api/v1/staff/campaigns/ — a platform-wide campaign. The staff accessor
 * only ever sends the campaign's own fields; the server fixes the scope to
 * `platform` and writes the `campaign.created` audit row itself, so a caller
 * can never smuggle a store in or skip the trail.
 */
export async function createStaffCampaign(payload) {
  const csrf = await ensureCsrfToken();
  const body = {
    name: payload.name,
    description: payload.description ?? "",
    is_active: payload.isActive ?? true,
  };
  if (payload.startsAt) body.starts_at = payload.startsAt;
  if (payload.endsAt) body.ends_at = payload.endsAt;
  return mapCampaign(
    await request(BASE, "/staff/campaigns/", { method: "POST", body, csrf })
  );
}

/** GET /api/v1/staff/promotions/ — platform-wide promotion oversight. */
export async function fetchStaffPromotions() {
  const data = await request(BASE, "/staff/promotions/");
  return (Array.isArray(data) ? data : (data.items ?? [])).map(mapPromotion);
}