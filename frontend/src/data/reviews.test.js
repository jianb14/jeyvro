import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createProductReview,
  fetchModerationQueue,
  fetchProductReviews,
  fetchReviewEligibility,
  fetchStoreReviews,
  mapConsoleReview,
  mapReview,
  moderateReview,
  reportReview,
  replyToStoreReview,
  resolveReviewReports,
  updateProductReview,
} from "./reviews";

const REVIEW_PAYLOAD = {
  id: 7,
  rating: 4,
  title: "Worth it",
  body: "Solid item, matches the photos.",
  author: "Bea B.",
  verified_purchase: true,
  images: [{ id: 1, image_url: "http://api/media/reviews/1.png", caption: "" }],
  seller_reply: "",
  seller_replied_at: null,
  created_at: "2026-09-20T10:00:00Z",
  updated_at: "2026-09-20T10:00:00Z",
};

const CONSOLE_PAYLOAD = {
  ...REVIEW_PAYLOAD,
  product_title: "Woven Basket",
  product_slug: "woven-basket",
  store_name: "Kalinga Crafts",
  store_slug: "kalinga-crafts",
  order_number: "JV-20260901-AAAA1111",
  author_email: "bea@example.com",
  status: "flagged",
  report_count: 3,
  open_report_count: 2,
  moderation_reason: "",
  moderated_by_email: null,
  moderated_at: null,
};

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async (url) => {
    // CSRF preflight always succeeds; assertions target the review calls.
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

describe("review shape mapping", () => {
  it("maps the public row to the ReviewCard contract", () => {
    const review = mapReview(REVIEW_PAYLOAD);
    expect(review.verifiedPurchase).toBe(true);
    expect(review.author).toBe("Bea B.");
    expect(review.images[0].url).toBe("http://api/media/reviews/1.png");
    expect(review.date).not.toBe("");
  });

  it("carries moderation context for the console rows", () => {
    const row = mapConsoleReview(CONSOLE_PAYLOAD);
    expect(row.productTitle).toBe("Woven Basket");
    expect(row.storeName).toBe("Kalinga Crafts");
    expect(row.orderNumber).toBe("JV-20260901-AAAA1111");
    expect(row.status).toBe("flagged");
    expect(row.reportCount).toBe(3);
    expect(row.openReportCount).toBe(2);
    expect(row.moderatedByEmail).toBeNull();
  });

  it("tolerates empty payloads (older rows, no images)", () => {
    const review = mapReview({ id: 1, rating: 5 });
    expect(review.author).toBe("Jeyvro buyer");
    expect(review.images).toEqual([]);
    expect(review.verifiedPurchase).toBe(false);
    expect(review.sellerReply).toBe("");
  });
});

describe("public review accessors", () => {
  it("lists reviews with filters", async () => {
    const { fetchMock } = mockFetch({ count: 1, items: [REVIEW_PAYLOAD] });
    const data = await fetchProductReviews("woven-basket", {
      page: 2,
      pageSize: 5,
    });
    expect(data.count).toBe(1);
    expect(data.items[0].rating).toBe(4);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/catalog/products/woven-basket/reviews/?page=2&page_size=5"
    );
  });

  it("reads the server eligibility verdict", async () => {
    mockFetch({
      can_review: false,
      reason: "already_reviewed",
      order_number: null,
      review_id: 7,
    });
    const verdict = await fetchReviewEligibility("woven-basket");
    expect(verdict.canReview).toBe(false);
    expect(verdict.reason).toBe("already_reviewed");
    expect(verdict.reviewId).toBe(7);
  });

  it("posts a review with CSRF and maps the response", async () => {
    const { callWith } = mockFetch(REVIEW_PAYLOAD);
    const review = await createProductReview("woven-basket", {
      rating: 4,
      body: "Solid item, matches the photos.",
      imageUrls: ["http://cdn.example.com/a.png"],
    });
    expect(review.id).toBe(7);
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/catalog/products/woven-basket/reviews/");
    expect(JSON.parse(post[1].body).image_urls).toEqual([
      "http://cdn.example.com/a.png",
    ]);
  });

  it("edits and reports through the row endpoints", async () => {
    const { callWith } = mockFetch(REVIEW_PAYLOAD);
    await updateProductReview(7, { rating: 3 });
    const patch = callWith("PATCH");
    expect(patch[0]).toBe("/api/v1/reviews/7/");
    expect(JSON.parse(patch[1].body)).toEqual({ rating: 3 });
    await reportReview(7, { reason: "spam", notes: "Copied text." });
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/reviews/7/report/");
    expect(JSON.parse(post[1].body)).toEqual({
      reason: "spam",
      notes: "Copied text.",
    });
  });
});

describe("console accessors", () => {
  it("fetches the seller store list and posts a reply", async () => {
    const { fetchMock, callWith } = mockFetch({ count: 1, items: [CONSOLE_PAYLOAD] });
    const mine = await fetchStoreReviews({ status: "published", unanswered: "1" });
    expect(mine.items[0].productTitle).toBe("Woven Basket");
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/reviews/store/?status=published&unanswered=1"
    );
    await replyToStoreReview(7, "Salamat sa feedback!");
    expect(callWith("POST")[0]).toBe("/api/v1/reviews/7/reply/");
  });

  it("fetches the moderation queue and hides with a reason", async () => {
    // Route responses by URL: the queue returns rows, the action returns
    // the updated console row (status flipped to hidden by the service).
    const fetchMock = vi.fn(async (url) => {
      if (String(url).includes("/csrf")) {
        return { ok: true, status: 200, json: async () => ({ detail: "ok" }) };
      }
      if (String(url).includes("/moderation")) {
        return { ok: true, status: 200, json: async () => ({ count: 1, items: [CONSOLE_PAYLOAD] }) };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ ...CONSOLE_PAYLOAD, status: "hidden" }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    const callWith = (method) =>
      fetchMock.mock.calls.find(([, options]) => options?.method === method);

    await fetchModerationQueue({ reported: "1", q: "basket" });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/reviews/moderation/?reported=1&q=basket"
    );
    const hidden = await moderateReview(7, { action: "hide", reason: "Contacts." });
    expect(hidden.status).toBe("hidden");
    expect(JSON.parse(callWith("POST")[1].body)).toEqual({
      action: "hide",
      reason: "Contacts.",
    });
  });

  it("resolves abuse reports", async () => {
    const { callWith } = mockFetch({ review_id: 7, resolved: 3 });
    const result = await resolveReviewReports(7);
    expect(result.resolved).toBe(3);
    expect(callWith("POST")[0]).toBe("/api/v1/reviews/7/reports/resolve/");
  });

  it("surfaces the server error envelope", async () => {
    mockFetch(
      { error: "reason_required", detail: "A reason is required." },
      { ok: false, status: 400 }
    );
    await expect(moderateReview(7, { action: "hide" })).rejects.toMatchObject({
      status: 400,
      data: { error: "reason_required" },
    });
  });
});
