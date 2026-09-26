/**
 * Seller approvals (Phase 13.3) — /staff.
 *
 * The operator's review queue: pending, approved, and rejected seller
 * applications ({count, items}, server-filtered). Approving flips the store
 * active and the applicant to seller; rejecting demands a reason — both run
 * through the moderation service, so every decision is audit-logged (§9).
 * Staff cannot review their own application (server-enforced).
 */
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { Textarea } from "../../components/ui/Textarea";
import { InboxIcon } from "../../components/ui/Icons";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 10;

const STATUS_TONES = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
};

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString("en-PH", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";
}

export function StaffSellerApplications() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [rejecting, setRejecting] = useState(null);
  const [reason, setReason] = useState("");

  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "pending";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchApplicationQueue({ status, q, page, pageSize: PAGE_SIZE })
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
  }, [q, status, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function approve(application) {
    setBusyId(application.id);
    setNotice(null);
    try {
      await staffApi.reviewApplication(application.id, { decision: "approved" });
      setNotice({
        tone: "success",
        message: `${application.storeName} approved — the seller studio is unlocked for ${application.applicantEmail}.`,
      });
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  async function reject() {
    if (!rejecting) return;
    setBusyId(rejecting.id);
    setNotice(null);
    try {
      await staffApi.reviewApplication(rejecting.id, {
        decision: "rejected",
        reason: reason.trim(),
      });
      setNotice({
        tone: "success",
        message: `${rejecting.storeName} rejected — the applicant sees your reason and may reapply.`,
      });
      setRejecting(null);
      setReason("");
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }


  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Seller approvals
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Review applications to open a store. Approving unlocks the seller
          studio; rejecting requires a reason the applicant can act on.
        </p>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && <Alert tone="danger" title="Could not load the queue">{error}</Alert>}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <Input
            label="Search applications"
            placeholder="Store name or applicant email…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="w-44">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("status", event.target.value)}
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="">All statuses</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {!data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={InboxIcon}
          title={q ? "No applications match" : "Nothing to review"}
          description={
            q
              ? "Try a different store name or applicant email."
              : status === "pending"
                ? "New applications land here the moment a customer applies to sell."
                : "No applications with this status yet."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Store</TH>
              <TH>Applicant</TH>
              <TH>Submitted</TH>
              <TH>Status</TH>
              <TH className="text-right">Decision</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((application) => (
              <TR key={application.id}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {application.storeName}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {application.storeSlug} · store {application.storeStatus}
                  </p>
                </TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {application.applicantEmail}
                  </span>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {application.contactPhone || "No phone given"}
                  </p>
                </TD>
                <TD>{formatDate(application.createdAt)}</TD>
                <TD>
                  <Badge
                    tone={STATUS_TONES[application.status] || "neutral"}
                    variant="soft"
                  >
                    {application.status}
                  </Badge>
                  {application.status === "rejected" &&
                    application.rejectionReason && (
                      <p className="mt-1 max-w-56 text-xs text-danger-600 dark:text-danger-400">
                        {application.rejectionReason}
                      </p>
                    )}
                </TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    {application.status === "pending" ? (
                      <>
                        <Button
                          size="sm"
                          loading={busyId === application.id}
                          onClick={() => approve(application)}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busyId === application.id}
                          onClick={() => {
                            setRejecting(application);
                            setReason("");
                          }}
                        >
                          Reject
                        </Button>
                      </>
                    ) : (
                      <span className="text-xs text-sand-500 dark:text-sand-400">
                        {application.reviewedAt
                          ? `Reviewed ${formatDate(application.reviewedAt)}`
                          : "—"}
                      </span>
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
        open={Boolean(rejecting)}
        onClose={() => setRejecting(null)}
        title="Reject application"
        description={
          rejecting
            ? `${rejecting.storeName} (${rejecting.applicantEmail}) — the applicant reads this reason, so make it actionable.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setRejecting(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              type="submit"
              form="reject-application-form"
              loading={busyId === rejecting?.id}
              disabled={!reason.trim()}
            >
              Reject application
            </Button>
          </>
        }
      >
        <form
          id="reject-application-form"
          onSubmit={(event) => {
            event.preventDefault();
            reject();
          }}
        >
          <Textarea
            label="Reason (required)"
            rows={3}
            maxLength={500}
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            hint="Sent to the applicant so they can fix it and reapply."
          />
        </form>
      </Modal>
    </div>
  );
}

