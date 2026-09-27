/**
 * Review accessors (Phase 14) — the ONLY data access point for the review
 * surfaces: the product review list + write flow, the eligibility verdict,
 * abuse reports, the seller reply console, and the staff moderation queue.
 *
 * Shapes are mapped here so components render API truth as-is: rating
 * aggregates come from the server (never recomputed client-side), and the
 * public card contract (author / rating / verified / text / photos) is
 * produced in one place.
 */

import { ensureCsrfToken, request } from "../lib/api";

const CATALOG = "/api/v1/catalog";
const REVIEWS = "/api/v1/reviews";

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

// --- Shape mapping ---------------------------------------------------------

export function mapReview(review) {
  return {
    id: review.id,
    rating: review.rating,
    title: review.title ?? "",
    body: review.body ?? "",
    author: review.author ?? "Jeyvro buyer",
    verifiedPurchase: Boolean(review.verified_purchase),
    images: (review.images ?? []).map((image) => ({
      id: image.id,
      url: image.image_url,
      caption: image.caption ?? "",
    })),
    sellerReply: review.seller_reply ?? "",
    sellerRepliedAt: review.seller_replied_at ?? null,
    createdAt: review.created_at,
    date: formatDate(review.created_at),
  };
}

/** Console row (staff queue + seller studio) — moderation context included. */
export function mapConsoleReview(review) {
  return {
    ...mapReview(review),
    productTitle: review.product_title ?? "",
    productSlug: review.product_slug ?? "",
    storeName: review.store_name ?? "",
    storeSlug: review.store_slug ?? "",
    orderNumber: review.order_number ?? "",
    authorEmail: review.author_email ?? "",
    status: review.status,
    reportCount: review.report_count ?? 0,
    openReportCount: review.open_report_count ?? 0,
    moderationReason: review.moderation_reason ?? "",
    moderatedByEmail: review.moderated_by_email ?? null,
    moderatedAt: review.moderated_at ?? null,
  };
}

// --- Public surface (product detail) ---------------------------------------

export async function fetchProductReviews(slug, { page = "", pageSize = "" } = {}) {
  const query = buildQuery({ page, page_size: pageSize });
  const data = await request(
    CATALOG,
    `/products/${encodeURIComponent(slug)}/reviews/${query}`
  );
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapReview),
  };
}

/** The server's verdict behind the "Write a review" button (§6). */
export async function fetchReviewEligibility(slug) {
  const data = await request(
    CATALOG,
    `/products/${encodeURIComponent(slug)}/reviews/eligibility/`
  );
  return {
    canReview: Boolean(data.can_review),
    reason: data.reason ?? "",
    orderNumber: data.order_number ?? null,
    reviewId: data.review_id ?? null,
  };
}

export async function createProductReview(
  slug,
  { rating, title = "", body, imageUrls = [] }
) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, `/products/${encodeURIComponent(slug)}/reviews/`, {
    method: "POST",
    csrf,
    body: { rating, title, body, image_urls: imageUrls },
  });
  return mapReview(data);
}

export async function updateProductReview(id, patch) {
  const csrf = await ensureCsrfToken();
  const data = await request(REVIEWS, `/${id}/`, {
    method: "PATCH",
    csrf,
    body: patch,
  });
  return mapReview(data);
}

export async function reportReview(id, { reason, notes = "" }) {
  const csrf = await ensureCsrfToken();
  return request(REVIEWS, `/${id}/report/`, {
    method: "POST",
    csrf,
    body: { reason, notes },
  });
}

// --- Seller studio (14.2) --------------------------------------------------

export async function fetchStoreReviews({
  status = "",
  unanswered = "",
  q = "",
  page = "",
  pageSize = "",
} = {}) {
  const query = buildQuery({
    status,
    unanswered,
    q,
    page,
    page_size: pageSize,
  });
  const data = await request(REVIEWS, `/store/${query}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapConsoleReview),
  };
}

export async function replyToStoreReview(id, text) {
  const csrf = await ensureCsrfToken();
  const data = await request(REVIEWS, `/${id}/reply/`, {
    method: "POST",
    csrf,
    body: { text },
  });
  return mapConsoleReview(data);
}

// --- Staff moderation (14.3) ----------------------------------------------

export async function fetchModerationQueue({
  status = "",
  reported = "",
  q = "",
  page = "",
  pageSize = "",
} = {}) {
  const query = buildQuery({
    status,
    reported,
    q,
    page,
    page_size: pageSize,
  });
  const data = await request(REVIEWS, `/moderation/${query}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapConsoleReview),
  };
}

/** Hide/restore — the service demands a reason for hiding and audit-logs it. */
export async function moderateReview(id, { action, reason = "" }) {
  const csrf = await ensureCsrfToken();
  const data = await request(REVIEWS, `/${id}/moderate/`, {
    method: "POST",
    csrf,
    body: { action, reason },
  });
  return mapConsoleReview(data);
}

export async function resolveReviewReports(id) {
  const csrf = await ensureCsrfToken();
  return request(REVIEWS, `/${id}/reports/resolve/`, { method: "POST", csrf });
}
