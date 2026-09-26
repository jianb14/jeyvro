/**
 * Seller products (Phase 12.2) — /seller/products.
 *
 * Server-side search/filter/pagination ({count, items}); lifecycle moves
 * (submit / unpublish / archive / delete) all round-trip through the API,
 * which resolves delete into archive when order history exists. Bulk
 * actions report per-id results from the server.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Checkbox } from "../../components/ui/Checkbox";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Price } from "../../components/ui/Price";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { TagIcon } from "../../components/ui/Icons";
import * as sellerApi from "../../data/seller";

const PAGE_SIZE = 10;

const STATUS_TONES = {
  draft: "neutral",
  pending_review: "warning",
  published: "success",
  unpublished: "neutral",
  rejected: "danger",
  archived: "neutral",
};

export function SellerProducts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [notice, setNotice] = useState(null);
  const [selected, setSelected] = useState([]);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    sellerApi
      .fetchMyProducts({ q, status, page, pageSize: PAGE_SIZE })
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setSelected([]);
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

  async function runAction(product, action) {
    setBusyId(product.id);
    setNotice(null);
    try {
      const runner = {
        submit: sellerApi.submitProduct,
        unpublish: sellerApi.unpublishProduct,
        archive: sellerApi.archiveProduct,
      }[action];
      await runner(product.id);
      setNotice({ tone: "success", message: `${product.title}: ${action} succeeded.` });
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete() {
    if (!confirmDelete) return;
    setBusyId(confirmDelete.id);
    setNotice(null);
    try {
      const result = await sellerApi.deleteProduct(confirmDelete.id);
      setNotice({
        tone: "success",
        message: result.detail || `${confirmDelete.title}: removed.`,
      });
      setConfirmDelete(null);
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  async function runBulk(action) {
    if (selected.length === 0) return;
    setNotice(null);
    try {
      const result = await sellerApi.bulkProducts(action, selected);
      const failed = (result.results || []).filter((row) => !row.ok);
      setNotice({
        tone: failed.length ? "warning" : "success",
        message: failed.length
          ? `${result.results.length - failed.length} succeeded, ${failed.length} failed: ${failed
              .map((row) => row.detail)
              .join(" ")}`
          : `${result.results.length} products updated.`,
      });
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    }
  }

  const allSelected =
    data && data.items.length > 0 && selected.length === data.items.length;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            Products
          </h1>
          <p className="text-sm text-sand-500 dark:text-sand-400">
            Draft, submit for review, unpublish, or archive — status changes
            run through the marketplace review flow.
          </p>
        </div>
        <Link to="/seller/products/new">
          <Button>Add product</Button>
        </Link>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && <Alert tone="danger" title="Could not load products">{error}</Alert>}

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
            label="Search products"
            placeholder="Title or description…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="w-48">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("status", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="pending_review">Pending review</option>
            <option value="published">Published</option>
            <option value="unpublished">Unpublished</option>
            <option value="rejected">Rejected</option>
            <option value="archived">Archived</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">Search</Button>
      </form>

      {selected.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-moss-200 bg-moss-50 px-4 py-3 dark:border-moss-900 dark:bg-moss-950/40">
          <span className="text-sm font-medium text-moss-800 dark:text-moss-200">
            {selected.length} selected
          </span>
          <Button size="sm" variant="outline" onClick={() => runBulk("submit")}>
            Submit for review
          </Button>
          <Button size="sm" variant="outline" onClick={() => runBulk("unpublish")}>
            Unpublish
          </Button>
          <Button size="sm" variant="outline" onClick={() => runBulk("archive")}>
            Archive
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSelected([])}>
            Clear
          </Button>
        </div>
      )}

      {!data ? (
        <Skeleton className="h-72 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={TagIcon}
          title={q || status ? "No products match" : "No products yet"}
          description={
            q || status
              ? "Try a different search or status filter."
              : "Create your first product, add variants and images, then submit it for review."
          }
          action={
            <Link to="/seller/products/new">
              <Button>Add product</Button>
            </Link>
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH className="w-10">
                <Checkbox
                  aria-label="Select all products"
                  checked={allSelected}
                  onChange={() =>
                    setSelected(
                      allSelected ? [] : data.items.map((item) => item.id)
                    )
                  }
                />
              </TH>
              <TH>Product</TH>
              <TH>Status</TH>
              <TH>Price</TH>
              <TH>Stock</TH>
              <TH>Variants</TH>
              <TH>Updated</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((product) => (
              <TR key={product.id}>
                <TD>
                  <Checkbox
                    aria-label={`Select ${product.title}`}
                    checked={selected.includes(product.id)}
                    onChange={() =>
                      setSelected((current) =>
                        current.includes(product.id)
                          ? current.filter((id) => id !== product.id)
                          : [...current, product.id]
                      )
                    }
                  />
                </TD>
                <TD>
                  <Link
                    to={`/seller/products/${product.id}`}
                    className="font-medium text-sand-900 hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
                  >
                    {product.title}
                  </Link>
                  {product.status === "rejected" && product.rejectionReason && (
                    <p className="mt-0.5 max-w-64 text-xs text-danger-600 dark:text-danger-400">
                      {product.rejectionReason}
                    </p>
                  )}
                </TD>
                <TD>
                  <Badge
                    tone={STATUS_TONES[product.status] || "neutral"}
                    variant="soft"
                  >
                    {product.status.replace("_", " ")}
                  </Badge>
                </TD>
                <TD>
                  <Price amount={Number(product.displayPrice)} size="sm" />
                </TD>
                <TD className="tabular-nums">{product.stockTotal}</TD>
                <TD className="tabular-nums">{product.variants.length}</TD>
                <TD>
                  {new Date(product.updatedAt).toLocaleDateString("en-PH", {
                    dateStyle: "medium",
                  })}
                </TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    {["draft", "rejected", "unpublished"].includes(product.status) && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === product.id}
                        onClick={() => runAction(product, "submit")}
                      >
                        Submit
                      </Button>
                    )}
                    {product.status === "published" && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === product.id}
                        onClick={() => runAction(product, "unpublish")}
                      >
                        Unpublish
                      </Button>
                    )}
                    {["draft", "rejected", "unpublished"].includes(product.status) && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === product.id}
                        onClick={() => runAction(product, "archive")}
                      >
                        Archive
                      </Button>
                    )}
                    {product.status !== "archived" && (
                      <>
                        <Link to={`/seller/products/${product.id}`}>
                          <Button size="sm" variant="ghost">Edit</Button>
                        </Link>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busyId === product.id}
                          onClick={() => setConfirmDelete(product)}
                        >
                          Delete
                        </Button>
                      </>
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
        open={Boolean(confirmDelete)}
        onClose={() => setConfirmDelete(null)}
        title="Delete this product?"
        description="Products that have already been ordered are archived instead — past orders always keep their history."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={busyId === confirmDelete?.id}
              onClick={handleDelete}
            >
              Delete product
            </Button>
          </>
        }
      >
        {confirmDelete?.title}
      </Modal>
    </div>
  );
}
