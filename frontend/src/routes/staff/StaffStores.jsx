/**
 * Store oversight (Phase 13.3) — /staff/stores.
 *
 * Read broadly, write narrowly (marketplace-admin rule 6): the directory is
 * server-filtered ({count, items}) and the only writes are the audited
 * store-status transitions (suspend / reactivate) that run through the
 * moderation service — staff never edit store content here.
 */
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { Textarea } from "../../components/ui/Textarea";
import { StoreIcon } from "../../components/ui/Icons";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 10;

const STATUS_TONES = {
  active: "success",
  pending: "warning",
  suspended: "danger",
};

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

export function StaffStores() {
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
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchStaffStores({ status, q, page, pageSize: PAGE_SIZE })
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

  async function runStatusChange() {
    if (!pendingAction) return;
    const { store, action } = pendingAction;
    setBusyId(store.id);
    setNotice(null);
    try {
      await staffApi.setStoreStatus(store.id, action, reason.trim());
      setNotice({
        tone: "success",
        message:
          action === "suspend"
            ? `${store.name} suspended — the storefront is hidden until reactivated.`
            : `${store.name} reactivated — the storefront is public again.`,
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

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Stores
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Oversight of every store. Suspension hides a storefront without
          deleting data, and both directions are audit-logged.
        </p>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && <Alert tone="danger" title="Could not load stores">{error}</Alert>}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <SearchInput
            label="Search stores"
            placeholder="Store name, slug, or owner email…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onClear={() => {
              setSearch("");
              setParam("q", "");
            }}
          />
        </div>
        <div className="w-44">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("status", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="suspended">Suspended</option>
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
          icon={StoreIcon}
          title={q || status ? "No stores match" : "No stores yet"}
          description={
            q || status
              ? "Try another search or status filter."
              : "Stores appear here as soon as a seller application is filed."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Store</TH>
              <TH>Owner</TH>
              <TH>Products</TH>
              <TH>Created</TH>
              <TH>Status</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((store) => (
              <TR key={store.id}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {store.name}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {store.slug}
                  </p>
                </TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {store.ownerEmail}
                  </span>
                  {store.ownerName && (
                    <p className="text-xs text-sand-500 dark:text-sand-400">
                      {store.ownerName}
                    </p>
                  )}
                </TD>
                <TD className="tabular-nums">{store.productCount}</TD>
                <TD>{formatDate(store.createdAt)}</TD>
                <TD>
                  <Badge
                    tone={STATUS_TONES[store.status] || "neutral"}
                    variant="soft"
                  >
                    {store.status}
                  </Badge>
                  {store.status === "suspended" && store.suspendedAt && (
                    <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">
                      since {formatDate(store.suspendedAt)}
                    </p>
                  )}
                </TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    {store.status === "active" && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === store.id}
                        onClick={() => {
                          setPendingAction({ store, action: "suspend" });
                          setReason("");
                        }}
                      >
                        Suspend
                      </Button>
                    )}
                    {store.status === "suspended" && (
                      <Button
                        size="sm"
                        loading={busyId === store.id}
                        onClick={() => {
                          setPendingAction({ store, action: "activate" });
                          setReason("");
                        }}
                      >
                        Reactivate
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
        title={
          pendingAction?.action === "suspend"
            ? "Suspend store"
            : "Reactivate store"
        }
        description={
          pendingAction
            ? pendingAction.action === "suspend"
              ? `${pendingAction.store.name} disappears from the public storefront. Data is kept and the decision is audit-logged.`
              : `${pendingAction.store.name} becomes visible to shoppers again. The decision is audit-logged.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingAction(null)}>
              Cancel
            </Button>
            <Button
              variant={
                pendingAction?.action === "suspend" ? "destructive" : "primary"
              }
              type="submit"
              form="store-status-form"
              loading={busyId === pendingAction?.store?.id}
            >
              {pendingAction?.action === "suspend"
                ? "Suspend store"
                : "Reactivate store"}
            </Button>
          </>
        }
      >
        <form
          id="store-status-form"
          onSubmit={(event) => {
            event.preventDefault();
            runStatusChange();
          }}
        >
          <Textarea
            label={
              pendingAction?.action === "suspend"
                ? "Reason (recommended)"
                : "Note (optional)"
            }
            rows={3}
            maxLength={500}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            hint="Stored on the audit row so the decision is explainable later."
          />
        </form>
      </Modal>
    </div>
  );
}

