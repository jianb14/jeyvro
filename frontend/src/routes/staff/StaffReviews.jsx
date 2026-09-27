/**
 * Review moderation (Phase 14.3) — /staff/reviews.
 *
 * The queue is server-filtered ({count, items}) and every action runs
 * through the moderation service: hiding demands a reason, is audit-logged
 * with the acting staff member, and pulls the review out of the public
 * list and the rating aggregates; restore returns it. Support reads along
 * per the §4 matrix; the backend refuses out-of-group writes regardless.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Rating } from "../../components/ui/Rating";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
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

export function StaffReviews() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [reason, setReason] = useState("");

  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const reported = searchParams.get("reported") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    reviewsApi
      .fetchModerationQueue({ status, reported, q, page, pageSize: PAGE_SIZE })
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
  }, [status, reported, q, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function runAction() {
    if (!pendingAction) return;
    const { review, action } = pendingAction;
    setBusyId(review.id);
    setNotice(null);
    try {
      await reviewsApi.moderateReview(review.id, {
        action,
        reason: reason.trim(),
      });
      setNotice({
        tone: "success",
        message:
          action === "hide"
            ? `Review #${review.id} hidden — it left the public list and the rating.`
            : `Review #${review.id} restored — it is public again.`,
      });
      setPendingAction(null);
      setReason("");
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  async function resolveReports(review) {
    setBusyId(review.id);
    setNotice(null);
    try {
      const result = await reviewsApi.resolveReviewReports(review.id);
      setNotice({
        tone: "success",
        message:
          result.resolved > 0
            ? `${result.resolved} report${result.resolved === 1 ? "" : "s"} marked resolved.`
            : "No open reports on that review.",
      });
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            Review moderation
          </h1>
          <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
            Reports flag a review for staff; hiding needs a reason and is
            audit-logged. Sellers can reply but never hide a review.
          </p>
        </div>
        <Link to="/staff/audit">
          <Button variant="ghost" size="sm">Audit log</Button>
        </Link>
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
            placeholder="Product, store or buyer"
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
            label="Reports"
            value={reported}
            onChange={(event) => setParam("reported", event.target.value)}
          >
            <option value="">All reviews</option>
            <option value="1">Reported or flagged</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">Apply</Button>
      </form>

      {!data && !error && <Skeleton className="h-40 w-full rounded-2xl" />}

      {data && data.count === 0 && (
        <EmptyState
          compact
          icon={StarIcon}
          title="Nothing to moderate"
          description="No review matches these filters — flagged and reported rows land here first."
        />
      )}

      {data && data.count > 0 && (
        <Table>
          <THead>
            <TR>
              <TH>Review</TH>
              <TH>Buyer</TH>
              <TH>Status</TH>
              <TH>Reports</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((review) => (
              <TR key={review.id}>
                <TD>
                  <div className="flex flex-col gap-1">
                    <Link
                      to={`/product/${review.productSlug}`}
                      className="text-sm font-medium text-sand-900 hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
                    >
                      {review.productTitle}
                    </Link>
                    <span className="text-xs text-sand-500 dark:text-sand-400">
                      {review.storeName} · {review.orderNumber} ·{" "}
                      {formatDate(review.createdAt)}
                    </span>
                    <p className="max-w-md text-xs leading-relaxed text-sand-600 dark:text-sand-300">
                      {review.body.length > 140
                        ? `${review.body.slice(0, 140)}…`
                        : review.body}
                    </p>
                  </div>
                </TD>
                <TD>
                  <div className="flex flex-col gap-1">
                    <span className="text-sm text-sand-700 dark:text-sand-300">
                      {review.author}
                    </span>
                    <Rating value={review.rating} readonly size="sm" />
                  </div>
                </TD>
                <TD>
                  <div className="flex flex-col gap-1">
                    <Badge tone={STATUS_TONES[review.status] ?? "neutral"} size="sm">
                      {review.status}
                    </Badge>
                    {review.moderationReason && (
                      <span className="text-xs text-sand-500 dark:text-sand-400">
                        {review.moderationReason}
                      </span>
                    )}
                  </div>
                </TD>
                <TD>
                  <span className="text-sm tabular-nums text-sand-700 dark:text-sand-300">
                    {review.reportCount}
                  </span>
                  {review.openReportCount > 0 && (
                    <span className="ml-2 text-xs text-warning-600 dark:text-warning-400">
                      {review.openReportCount} open
                    </span>
                  )}
                </TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    {review.openReportCount > 0 && (
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={busyId === review.id}
                        onClick={() => resolveReports(review)}
                      >
                        Resolve reports
                      </Button>
                    )}
                    {review.status !== "hidden" ? (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === review.id}
                        onClick={() => {
                          setPendingAction({ review, action: "hide" });
                          setReason("");
                        }}
                      >
                        Hide
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        loading={busyId === review.id}
                        onClick={() => {
                          setPendingAction({ review, action: "restore" });
                          setReason("");
                        }}
                      >
                        Restore
                      </Button>
                    )}
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {data && data.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(data.count / PAGE_SIZE)}
          current={page}
          onChange={(next) => setParam("page", String(next))}
        />
      )}

      <Modal
        open={Boolean(pendingAction)}
        onClose={() => setPendingAction(null)}
        title={pendingAction?.action === "hide" ? "Hide review" : "Restore review"}
        description={
          pendingAction
            ? pendingAction.action === "hide"
              ? `Review #${pendingAction.review.id} leaves the public product page and stops counting toward the product and store ratings. The buyer keeps their history; the decision is audit-logged.`
              : `Review #${pendingAction.review.id} becomes public again and counts toward the ratings.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingAction(null)}>
              Cancel
            </Button>
            <Button
              variant={pendingAction?.action === "hide" ? "destructive" : "primary"}
              type="submit"
              form="review-moderate-form"
              loading={busyId === pendingAction?.review?.id}
            >
              {pendingAction?.action === "hide" ? "Hide review" : "Restore review"}
            </Button>
          </>
        }
      >
        <form
          id="review-moderate-form"
          onSubmit={(event) => {
            event.preventDefault();
            runAction();
          }}
        >
          {pendingAction?.action === "hide" && (
            <Textarea
              label="Reason (required)"
              rows={3}
              maxLength={255}
              required
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              hint="Stored on the review and the audit row so the decision stays explainable."
            />
          )}
        </form>
      </Modal>
    </div>
  );
}
