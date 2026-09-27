/**
 * Product reviews (Phase 14) — the buyer-facing section of a product page.
 *
 * Nothing here decides anything: eligibility is the server verdict that
 * picks between "write a review", "edit your review", "buy it first", and
 * "already reviewed"; the average/count badges render the aggregates the
 * review services keep on the product row and are never recomputed in the
 * browser. Reports go through the abuse intake and are invisible to the
 * reporter afterwards (moderators decide).
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Rating } from "../../components/ui/Rating";
import { ReviewCard } from "../../components/ui/ReviewCard";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Textarea } from "../../components/ui/Textarea";
import { ShieldCheckIcon, StarIcon } from "../../components/ui/Icons";
import { useToast } from "../../components/ui/ToastProvider";
import { useAuth } from "../auth/AuthContext";
import * as reviewsApi from "../../data/reviews";

const PAGE_SIZE = 5;

const REPORT_REASONS = [
  { value: "spam", label: "Spam or advertising" },
  { value: "abusive", label: "Abusive or harassing" },
  { value: "irrelevant", label: "Not about this product" },
  { value: "other", label: "Something else" },
];

const EMPTY_FORM = { rating: 5, title: "", body: "", imageUrl: "" };

/** Card contract adapter — the API row told into the ReviewCard primitives. */
function toCard(review) {
  return {
    author: review.author,
    rating: review.rating,
    verifiedPurchase: review.verifiedPurchase,
    text: review.body,
    photos: review.images.map((image) => image.url),
    date: review.date,
  };
}

export function ProductReviews({ slug, product }) {
  const { user } = useAuth();
  const { push } = useToast();
  const [page, setPage] = useState(1);
  const [list, setList] = useState(null);
  const [listError, setListError] = useState(null);
  const [verdictState, setVerdictState] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);
  const [reporting, setReporting] = useState(null);
  const [reportReason, setReportReason] = useState("spam");
  const [reportNotes, setReportNotes] = useState("");
  const [reportBusy, setReportBusy] = useState(false);

  const load = useCallback(() => {
    let cancelled = false;
    reviewsApi
      .fetchProductReviews(slug, { page, pageSize: PAGE_SIZE })
      .then((result) => {
        if (!cancelled) {
          setList(result);
          setListError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) setListError(error.data?.detail || error.message);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, page]);

  useEffect(load, [load]);

  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;
    reviewsApi
      .fetchReviewEligibility(slug)
      .then((result) => {
        if (!cancelled) {
          setVerdictState({ ...result, slug, userId: user.id });
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [slug, user, list]);

  // A stale verdict (previous user or product) is never rendered — the
  // comparison happens here, so nothing needs resetting inside an effect.
  const verdict =
    verdictState &&
    verdictState.slug === slug &&
    verdictState.userId === user?.id
      ? verdictState
      : null;

  const editingId = verdict?.reviewId ?? null;

  function openForm() {
    const own = editingId ? list?.items.find((row) => row.id === editingId) : null;
    setForm(
      own
        ? { rating: own.rating, title: own.title, body: own.body, imageUrl: "" }
        : EMPTY_FORM
    );
    setFormError(null);
    setFormOpen(true);
  }

  async function submitReview(event) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      if (form.body.trim().length < 10) {
        setFormError("Please write at least a few words about the product.");
        setSaving(false);
        return;
      }
      if (editingId) {
        await reviewsApi.updateProductReview(editingId, {
          rating: form.rating,
          title: form.title,
          body: form.body,
        });
        push({ tone: "success", message: "Your review has been updated." });
      } else {
        await reviewsApi.createProductReview(slug, {
          rating: form.rating,
          title: form.title,
          body: form.body,
          imageUrls: form.imageUrl.trim() ? [form.imageUrl.trim()] : [],
        });
        push({ tone: "success", message: "Salamat! Your review is now published." });
      }
      setFormOpen(false);
      setForm(EMPTY_FORM);
      setPage(1);
      load();
    } catch (error) {
      setFormError(error.data?.detail || error.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitReport(event) {
    event.preventDefault();
    if (!reporting) return;
    setReportBusy(true);
    try {
      await reviewsApi.reportReview(reporting.id, {
        reason: reportReason,
        notes: reportNotes,
      });
      setReporting(null);
      setReportNotes("");
      setReportReason("spam");
      push({
        tone: "success",
        message: "Report sent — our moderators will review it.",
      });
    } catch (error) {
      push({ tone: "danger", message: error.data?.detail || error.message });
    } finally {
      setReportBusy(false);
    }
  }

  // Aggregates come from the product row (rewritten inside the review
  // transaction by the services) — the browser renders, never recomputes.
  const count = product?.ratingCount ?? 0;
  const average = product?.rating ?? null;

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
            Ratings &amp; reviews
          </h2>
          <div className="flex items-center gap-2">
            {count > 0 ? (
              <>
                <Rating value={Math.round(average)} readonly size="sm" />
                <span className="text-sm text-sand-500 dark:text-sand-400">
                  {average.toFixed(1)} average · {count} verified review{count === 1 ? "" : "s"}
                </span>
              </>
            ) : (
              <span className="text-sm text-sand-500 dark:text-sand-400">
                No reviews yet — verified buyers go first.
              </span>
            )}
          </div>
        </div>

        {user ? (
          verdict?.canReview || editingId ? (
            <Button variant={verdict?.canReview ? "primary" : "outline"} onClick={openForm}>
              {editingId ? "Edit my review" : "Write a review"}
            </Button>
          ) : null
        ) : (
          <Link to="/login">
            <Button variant="outline">Sign in to review</Button>
          </Link>
        )}
      </div>

      {user && verdict && !verdict.canReview && !editingId && (
        <Alert tone="info">
          {verdict.reason === "already_reviewed"
            ? "You already reviewed this product."
            : "Only customers whose order was delivered can review this product — buy it first, then share your experience."}
        </Alert>
      )}

      {verdict?.canReview && (
        <div className="flex items-center gap-2 text-xs text-sand-500 dark:text-sand-400">
          <ShieldCheckIcon size={14} className="shrink-0 text-moss-600 dark:text-moss-400" />
          Verified purchase{verdict.orderNumber ? ` · order ${verdict.orderNumber}` : ""}
        </div>
      )}

      {listError && <Alert tone="danger">{listError}</Alert>}

      {!list && !listError && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-28 w-full rounded-2xl" />
          <Skeleton className="h-28 w-full rounded-2xl" />
        </div>
      )}

      {list && list.count === 0 && (
        <EmptyState
          compact
          icon={StarIcon}
          title="No reviews yet"
          description="Reviews come from buyers whose orders were delivered — nothing is seeded or faked."
        />
      )}

      {list && list.count > 0 && (
        <div className="flex flex-col gap-4">
          {list.items.map((review) => (
            <div key={review.id} className="flex flex-col gap-2">
              <ReviewCard review={toCard(review)} />
              {review.sellerReply && (
                <div className="ml-4 rounded-xl border-l-2 border-moss-300 bg-moss-50/60 px-4 py-3 dark:border-moss-800 dark:bg-night-800/60">
                  <p className="text-xs font-semibold uppercase tracking-wide text-moss-700 dark:text-moss-300">
                    Response from the seller
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-sand-600 dark:text-sand-300">
                    {review.sellerReply}
                  </p>
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3 pl-1">
                {review.id === editingId && (
                  <Badge tone="moss" size="sm">Your review</Badge>
                )}
                {user && review.id !== editingId && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setReporting(review);
                      setReportReason("spam");
                      setReportNotes("");
                    }}
                  >
                    Report
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {list && list.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(list.count / PAGE_SIZE)}
          current={page}
          onChange={setPage}
        />
      )}

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editingId ? "Edit your review" : "Write a review"}
        description={
          editingId
            ? "Your edit republishes the review and updates the product's rating."
            : "Only verified buyers can review — this product's rating updates the moment you publish."
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="review-form" loading={saving}>
              {editingId ? "Save changes" : "Publish review"}
            </Button>
          </>
        }
      >
        <form id="review-form" className="flex flex-col gap-4" onSubmit={submitReview}>
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-sand-800 dark:text-sand-200">
              Your rating
            </span>
            <Rating
              value={form.rating}
              onChange={(rating) => setForm((current) => ({ ...current, rating }))}
              size="lg"
              showValue
            />
          </div>
          <Input
            label="Headline (optional)"
            maxLength={150}
            value={form.title}
            onChange={(event) =>
              setForm((current) => ({ ...current, title: event.target.value }))
            }
            placeholder="Sulit, arrived quickly"
          />
          <Textarea
            label="Your review"
            rows={5}
            maxLength={4000}
            required
            value={form.body}
            onChange={(event) =>
              setForm((current) => ({ ...current, body: event.target.value }))
            }
            hint="What did you buy, how did it arrive, and would you recommend it?"
            error={formError}
          />
          {!editingId && (
            <Input
              label="Photo link (optional)"
              type="url"
              value={form.imageUrl}
              onChange={(event) =>
                setForm((current) => ({ ...current, imageUrl: event.target.value }))
              }
              placeholder="https://…"
              hint="Reviews take photo links today; uploads arrive with the media phase."
            />
          )}
        </form>
      </Modal>

      <Modal
        open={Boolean(reporting)}
        onClose={() => setReporting(null)}
        title="Report this review"
        description="Reports go to the moderation queue. A review with several distinct reports is flagged for staff review."
        footer={
          <>
            <Button variant="ghost" onClick={() => setReporting(null)}>
              Cancel
            </Button>
            <Button type="submit" form="review-report-form" loading={reportBusy}>
              Send report
            </Button>
          </>
        }
      >
        <form id="review-report-form" className="flex flex-col gap-4" onSubmit={submitReport}>
          <Select
            label="Reason"
            value={reportReason}
            onChange={(event) => setReportReason(event.target.value)}
          >
            {REPORT_REASONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Textarea
            label="Notes (optional)"
            rows={3}
            maxLength={1000}
            value={reportNotes}
            onChange={(event) => setReportNotes(event.target.value)}
            hint="Anything else the moderators should know."
          />
        </form>
      </Modal>
    </section>
  );
}

