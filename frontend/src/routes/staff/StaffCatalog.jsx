/**
 * Catalog management (Phase 13.4) — /staff/catalog.
 *
 * The moderator console over every product status: server-filtered
 * ({count, items}) with the Phase 5 review transitions (publish/reject)
 * and the reason-gated staff takedown. Group access (moderator /
 * administrator) and every write are enforced and audit-logged
 * server-side (§4) — this page only renders what the API allows.
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
import { Price } from "../../components/ui/Price";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { Textarea } from "../../components/ui/Textarea";
import { PackageIcon } from "../../components/ui/Icons";
import { useAuth } from "../../features/auth/AuthContext";
import { getCategories } from "../../data/products";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 10;

const STATUS_TONES = {
  draft: "neutral",
  pending_review: "warning",
  published: "success",
  unpublished: "neutral",
  rejected: "danger",
  archived: "neutral",
};

const STATUS_LABELS = {
  draft: "Draft",
  pending_review: "Pending review",
  published: "Published",
  unpublished: "Unpublished",
  rejected: "Rejected",
  archived: "Archived",
};

const STATUSES = [
  "draft",
  "pending_review",
  "published",
  "unpublished",
  "rejected",
  "archived",
];

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

export function StaffCatalog() {
  const { user: viewer } = useAuth();
  const roles = viewer?.staff_roles ?? [];
  // UX only — the backend refuses out-of-group actions either way (§4).
  const canAct = roles.includes("moderator") || roles.includes("administrator");

  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [decision, setDecision] = useState("published");
  const [reason, setReason] = useState("");

  const q = searchParams.get("q") || "";
  const statusParam = searchParams.get("status");
  // Default view is the actionable queue; "all" widens to every status.
  const status = statusParam ?? "pending_review";
  const statusFilter = status === "all" ? "" : status;
  const category = searchParams.get("category") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchAdminProducts({
        q,
        status: statusFilter,
        category,
        page,
        pageSize: PAGE_SIZE,
      })
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
  }, [q, statusFilter, category, page]);

  useEffect(load, [load]);

  // Category filter labels come from the public catalog accessor so every
  // staff group can filter without holding taxonomy permissions.
  useEffect(() => {
    let cancelled = false;
    getCategories()
      .then((items) => {
        if (!cancelled) setCategories(items);
      })
      .catch(() => {
        if (!cancelled) setCategories([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function runAction() {
    if (!pendingAction) return;
    const { product, mode } = pendingAction;
    setBusyId(product.id);
    setNotice(null);
    try {
      if (mode === "review") {
        await staffApi.reviewProduct(product.id, decision, reason.trim());
        setNotice({
          tone: "success",
          message:
            decision === "published"
              ? `“${product.title}” published — it is live on the storefront.`
              : `“${product.title}” rejected — the seller sees the reason.`,
        });
      } else {
        await staffApi.unpublishProduct(product.id, reason.trim());
        setNotice({
          tone: "success",
          message: `“${product.title}” taken down — the seller sees the reason.`,
        });
      }
      setPendingAction(null);
      setReason("");
      setDecision("published");
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div>
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Catalog
        </h1>
        <p className="mt-1 text-sm text-sand-600 dark:text-sand-400">
          Every product on the marketplace — review submissions, publish or
          reject them, and take live listings down with a reason. Every
          decision is audit-logged.
        </p>
      </div>

      {notice && (
        <div className="mt-4">
          <Alert tone={notice.tone}>{notice.message}</Alert>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <Alert tone="danger" title="Could not load the catalog">
            {error}
          </Alert>
        </div>
      )}

      <form
        className="mt-6 flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <Input
            label="Search products"
            placeholder="Title, store, or owner email…"
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
            {STATUSES.map((option) => (
              <option key={option} value={option}>
                {STATUS_LABELS[option]}
              </option>
            ))}
            <option value="all">All statuses</option>
          </Select>
        </div>
        <div className="w-48">
          <Select
            label="Category"
            value={category}
            onChange={(event) => setParam("category", event.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((item) => (
              <option key={item.id} value={item.slug}>
                {item.name}
              </option>
            ))}
          </Select>
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {!data && !error && (
        <div className="mt-6 space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      )}

      {data && data.count === 0 && (
        <div className="mt-8">
          <EmptyState
            icon={PackageIcon}
            title="Nothing here"
            description="No products match these filters."
          />
        </div>
      )}

      {data && data.count > 0 && (
        <div className="mt-6">
          <Table>
            <THead>
              <TR>
                <TH>Product</TH>
                <TH>Store</TH>
                <TH>Status</TH>
                <TH>Price</TH>
                <TH>Variants</TH>
                <TH>Updated</TH>
                <TH className="text-right">Actions</TH>
              </TR>
            </THead>
            <TBody>
              {data.items.map((product) => (
                <TR key={product.id}>
                  <TD>
                    <p className="font-medium text-sand-900 dark:text-sand-100">
                      {product.title}
                    </p>
                    <p className="mt-0.5 text-xs text-sand-500 dark:text-sand-400">
                      {product.slug}
                      {product.categoryName ? ` · ${product.categoryName}` : ""}
                      {product.brandName ? ` · ${product.brandName}` : ""}
                    </p>
                  </TD>
                  <TD>
                    <p className="text-sand-900 dark:text-sand-100">
                      {product.storeName}
                    </p>
                    <p className="mt-0.5 text-xs text-sand-500 dark:text-sand-400">
                      {product.storeOwnerEmail}
                    </p>
                  </TD>
                  <TD>
                    <Badge
                      tone={STATUS_TONES[product.status] ?? "neutral"}
                      size="sm"
                    >
                      {STATUS_LABELS[product.status] ?? product.status}
                    </Badge>
                    {product.rejectionReason && (
                      <p className="mt-1 max-w-48 text-xs text-sand-500 dark:text-sand-400">
                        {product.rejectionReason}
                      </p>
                    )}
                  </TD>
                  <TD>
                    <Price amount={product.displayPrice} size="sm" />
                  </TD>
                  <TD className="tabular-nums">{product.variantCount}</TD>
                  <TD>{formatDate(product.updatedAt)}</TD>
                  <TD>
                    <div className="flex justify-end gap-2">
                      {canAct && product.status === "pending_review" && (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={busyId === product.id}
                          onClick={() => {
                            setPendingAction({ product, mode: "review" });
                            setDecision("published");
                            setReason("");
                          }}
                        >
                          Review
                        </Button>
                      )}
                      {canAct && product.status === "published" && (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={busyId === product.id}
                          onClick={() => {
                            setPendingAction({ product, mode: "unpublish" });
                            setReason("");
                          }}
                        >
                          Take down
                        </Button>
                      )}
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
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
        open={Boolean(pendingAction)}
        onClose={() => setPendingAction(null)}
        title={
          pendingAction?.mode === "unpublish"
            ? "Take down product"
            : "Review product"
        }
        description={
          pendingAction
            ? pendingAction.mode === "unpublish"
              ? `“${pendingAction.product.title}” disappears from the storefront immediately. The reason below is shown to the seller and audit-logged.`
              : `Decide “${pendingAction.product.title}” — publishing puts it live; rejecting returns it to the seller with your reason.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingAction(null)}>
              Cancel
            </Button>
            <Button
              variant={
                pendingAction?.mode === "unpublish" ||
                (pendingAction?.mode === "review" && decision === "rejected")
                  ? "destructive"
                  : "primary"
              }
              type="submit"
              form="catalog-action-form"
              loading={busyId === pendingAction?.product?.id}
              disabled={
                pendingAction?.mode === "unpublish"
                  ? !reason.trim()
                  : decision === "rejected" && !reason.trim()
              }
            >
              {pendingAction?.mode === "unpublish"
                ? "Take down"
                : decision === "published"
                  ? "Publish"
                  : "Reject"}
            </Button>
          </>
        }
      >
        <form
          id="catalog-action-form"
          onSubmit={(event) => {
            event.preventDefault();
            runAction();
          }}
        >
          <div className="space-y-4">
            {pendingAction?.mode === "review" && (
              <Select
                label="Decision"
                value={decision}
                onChange={(event) => setDecision(event.target.value)}
              >
                <option value="published">Publish — live on the storefront</option>
                <option value="rejected">Reject — back to the seller</option>
              </Select>
            )}
            <Textarea
              label={
                pendingAction?.mode === "unpublish" || decision === "rejected"
                  ? "Reason (required)"
                  : "Note (optional)"
              }
              rows={3}
              maxLength={500}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              hint="Stored on the audit row — and shown to the seller for takedowns and rejections."
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}