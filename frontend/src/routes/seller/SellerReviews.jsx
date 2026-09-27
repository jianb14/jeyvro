/**
 * Seller reviews desk (Phase 14.2) — /seller/reviews.
 *
 * Sellers read their own store's reviews and answer each one exactly once:
 * replies are public copy on the product page, moderation stays with staff
 * (§6 — a seller can never hide a review). The list is server-filtered.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, CardContent } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Rating } from "../../components/ui/Rating";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Textarea } from "../../components/ui/Textarea";
import { StarIcon } from "../../components/ui/Icons";
import * as reviewsApi from "../../data/reviews";

const PAGE_SIZE = 10;

const STATUS_TONES = {
  published: "success",
  flagged: "warning",
  hidden: "danger",
};

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

export function SellerReviews() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [replying, setReplying] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [saving, setSaving] = useState(false);

  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const unanswered = searchParams.get("unanswered") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    reviewsApi
      .fetchStoreReviews({ status, unanswered, q, page, pageSize: PAGE_SIZE })
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [status, unanswered, q, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function submitReply(event) {
    event.preventDefault();
    if (!replying) return;
    setSaving(true);
    setNotice(null);
    try {
      await reviewsApi.replyToStoreReview(replying.id, replyText.trim());
      setNotice({
        tone: "success",
        message: "Reply published — shoppers see it under the review.",
      });
      setReplying(null);
      setReplyText("");
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Reviews desk
        </h1>
        <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
          Every published review of your products, newest first. Answer once —
          replies are public and moderators handle anything abusive.
        </p>
      </div>

      {notice && <Alert tone={notice.tone}>{notice.message}</Alert>}
      {error && <Alert tone="danger">{error}</Alert>}

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="w-56">
          <Input
            label="Search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Product or review text"
          />
        </div>
        <div className="w-44">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("status", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="published">Published</option>
            <option value="flagged">Flagged</option>
            <option value="hidden">Hidden</option>
          </Select>
        </div>
        <div className="w-44">
          <Select
            label="Replies"
            value={unanswered}
            onChange={(event) => setParam("unanswered", event.target.value)}
          >
            <option value="">All reviews</option>
            <option value="1">Waiting for a reply</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">Apply</Button>
      </form>

      {!data && !error && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-32 w-full rounded-2xl" />
          <Skeleton className="h-32 w-full rounded-2xl" />
        </div>
      )}

      {data && data.count === 0 && (
        <EmptyState
          compact
          icon={StarIcon}
          title="No reviews yet"
          description="Reviews come from buyers whose orders were delivered — nothing is seeded or faked."
        />
      )}

      {data && data.count > 0 && (
        <div className="flex flex-col gap-4">
          {data.items.map((review) => (
            <Card key={review.id}>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-3">
                    <Rating value={review.rating} readonly size="sm" />
                    <Link
                      to={`/product/${review.productSlug}`}
                      className="truncate text-sm font-medium text-sand-900 hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
                    >
                      {review.productTitle}
                    </Link>
                  </div>
                  <Badge tone={STATUS_TONES[review.status] ?? "neutral"} size="sm">
                    {review.status}
                  </Badge>
                </div>

                <div>
                  <p className="text-sm leading-relaxed text-sand-600 dark:text-sand-300">
                    {review.body}
                  </p>
                  <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">
                    {review.author} · {review.orderNumber} ·{" "}
                    {formatDate(review.createdAt)}
                  </p>
                </div>

                {review.sellerReply ? (
                  <div className="rounded-xl border-l-2 border-moss-300 bg-moss-50/60 px-4 py-3 dark:border-moss-800 dark:bg-night-800/60">
                    <p className="text-xs font-semibold uppercase tracking-wide text-moss-700 dark:text-moss-300">
                      Your reply
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-sand-600 dark:text-sand-300">
                      {review.sellerReply}
                    </p>
                  </div>
                ) : (
                  <div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setReplying(review);
                        setReplyText("");
                      }}
                    >
                      Reply to this review
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {data && data.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(data.count / PAGE_SIZE)}
          current={page}
          onChange={(next) => setParam("page", String(next))}
        />
      )}

      <Modal
        open={Boolean(replying)}
        onClose={() => setReplying(null)}
        title="Reply to this review"
        description="One reply per review — it appears publicly under the buyer's words."
        footer={
          <>
            <Button variant="ghost" onClick={() => setReplying(null)}>
              Cancel
            </Button>
            <Button type="submit" form="review-reply-form" loading={saving}>
              Publish reply
            </Button>
          </>
        }
      >
        <form id="review-reply-form" className="flex flex-col gap-4" onSubmit={submitReply}>
          <Textarea
            label="Your reply"
            rows={4}
            maxLength={2000}
            required
            value={replyText}
            onChange={(event) => setReplyText(event.target.value)}
            hint="Thank the buyer, explain what happened, or invite them to message you."
          />
        </form>
      </Modal>
    </div>
  );
}
