/**
 * Promotions & vouchers accessors (Phase 16 — ROADMAP §16.1, §16.2, §16.4).
 *
 * The ONLY data access point for the promotion engine's wire contract:
 * - `validateVoucher` posts a code (never an amount) and returns the
 *   server's verdict for display;
 * - the seller CRUD accessors drive `/api/v1/seller/promotions/`.
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
    storeName: p.store_name ?? "",
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