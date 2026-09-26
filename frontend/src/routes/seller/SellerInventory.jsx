/**
 * Seller inventory (Phase 12.3) — /seller/inventory.
 *
 * Stock lives per variant and only moves through the stock service, so
 * every change here writes an append-only movement row (the history
 * drawer shows it). The low-stock filter and counts are server-side.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Drawer } from "../../components/ui/Drawer";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Price } from "../../components/ui/Price";
import { Skeleton } from "../../components/ui/Skeleton";
import { StockIndicator } from "../../components/ui/StockIndicator";
import { Switch } from "../../components/ui/Switch";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { PackageIcon } from "../../components/ui/Icons";
import * as sellerApi from "../../data/seller";

const PAGE_SIZE = 15;

const MOVEMENT_LABELS = {
  initial: "Initial stock",
  restock: "Restock",
  adjustment: "Adjustment",
  reserve: "Reserved",
  release: "Released",
  sale: "Sale",
};

function InventoryTable({ rows, onAdjust, onThreshold, onHistory }) {
  return (
    <Table>
      <THead>
        <TR>
          <TH>Product</TH>
          <TH>Variant</TH>
          <TH>Price</TH>
          <TH>On hand</TH>
          <TH>Reserved</TH>
          <TH>Available</TH>
          <TH>Alert level</TH>
          <TH className="text-right">Actions</TH>
        </TR>
      </THead>
      <TBody>
        {rows.map((row) => (
          <TR key={row.variantId}>
            <TD>
              <Link
                to={`/seller/products/${row.productId}`}
                className="font-medium text-sand-900 hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
              >
                {row.productTitle}
              </Link>
            </TD>
            <TD>
              <span className="text-sand-700 dark:text-sand-300">
                {row.name || "Default"}
              </span>
              <p className="text-xs text-sand-500 dark:text-sand-400">{row.sku}</p>
            </TD>
            <TD>
              <Price amount={row.price} size="sm" />
            </TD>
            <TD className="tabular-nums">{row.inventory?.onHand ?? 0}</TD>
            <TD className="tabular-nums">{row.inventory?.reserved ?? 0}</TD>
            <TD>
              <StockIndicator
                count={row.inventory?.available ?? 0}
                threshold={row.inventory?.lowStockThreshold ?? 0}
              />
            </TD>
            <TD className="tabular-nums">
              {row.inventory?.lowStockThreshold ?? 0}
            </TD>
            <TD>
              <div className="flex justify-end gap-2">
                <Button size="sm" variant="outline" onClick={() => onAdjust(row)}>
                  Adjust
                </Button>
                <Button size="sm" variant="outline" onClick={() => onThreshold(row)}>
                  Alert level
                </Button>
                <Button size="sm" variant="ghost" onClick={() => onHistory(row)}>
                  History
                </Button>
              </div>
            </TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

export function SellerInventory() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [adjusting, setAdjusting] = useState(null);
  const [thresholding, setThresholding] = useState(null);
  const [historyFor, setHistoryFor] = useState(null);
  const [history, setHistory] = useState(null);
  const [delta, setDelta] = useState("");
  const [note, setNote] = useState("");
  const [threshold, setThreshold] = useState("");
  const [busy, setBusy] = useState(false);

  const q = searchParams.get("q") || "";
  const lowStock = searchParams.get("low_stock") === "1";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    sellerApi
      .fetchInventory({ q, lowStock, page, pageSize: PAGE_SIZE })
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [q, lowStock, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function submitAdjust(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await sellerApi.adjustStock({
        variantId: adjusting.variantId,
        delta: Number(delta),
        note,
      });
      setNotice({ tone: "success", message: "Stock adjusted — movement recorded." });
      setAdjusting(null);
      setDelta("");
      setNote("");
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  }

  async function submitThreshold(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await sellerApi.setLowStockThreshold(
        thresholding.variantId,
        Number(threshold)
      );
      setNotice({ tone: "success", message: "Low-stock alert level updated." });
      setThresholding(null);
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  }

  async function openHistory(row) {
    setHistoryFor(row);
    setHistory(null);
    try {
      setHistory(await sellerApi.fetchStockHistory(row.variantId));
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Inventory
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Stock lives per variant; every adjustment is row-locked and appended
          to the movement history.
        </p>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && <Alert tone="danger" title="Could not load inventory">{error}</Alert>}

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
            label="Search inventory"
            placeholder="Product, variant, or SKU…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="pb-1">
          <Switch
            label="Low stock only"
            checked={lowStock}
            onChange={(checked) => setParam("low_stock", checked ? "1" : "")}
          />
        </div>
        <Button type="submit" variant="outline">Search</Button>
      </form>

      {!rows ? (
        <Skeleton className="h-72 w-full" />
      ) : rows.items.length === 0 ? (
        <EmptyState
          icon={PackageIcon}
          title={lowStock ? "Nothing needs restocking" : "No inventory yet"}
          description={
            lowStock
              ? "Every variant is above its low-stock threshold."
              : "Add products with variants and their stock rows appear here."
          }
        />
      ) : (
        <InventoryTable
          rows={rows.items}
          onAdjust={(row) => {
            setAdjusting(row);
            setDelta("");
            setNote("");
          }}
          onThreshold={(row) => {
            setThresholding(row);
            setThreshold(String(row.inventory?.lowStockThreshold ?? 0));
          }}
          onHistory={openHistory}
        />
      )}

      {rows && rows.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(rows.count / PAGE_SIZE)}
          current={page}
          onChange={(next) => setParam("page", String(next))}
        />
      )}

      <Modal
        open={Boolean(adjusting)}
        onClose={() => setAdjusting(null)}
        title="Adjust stock"
        description={
          adjusting
            ? `${adjusting.productTitle} — ${adjusting.name || adjusting.sku}. Positive numbers restock; negative numbers correct shrinkage.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setAdjusting(null)}>Cancel</Button>
            <Button
              type="submit"
              form="adjust-stock-form"
              loading={busy}
              disabled={delta === "" || Number(delta) === 0}
            >
              Apply adjustment
            </Button>
          </>
        }
      >
        <form id="adjust-stock-form" onSubmit={submitAdjust} className="flex flex-col gap-4">
          <Input
            label="Quantity change"
            type="number"
            step="1"
            required
            hint="e.g. 12 to restock, -3 to correct a breakage."
            value={delta}
            onChange={(event) => setDelta(event.target.value)}
          />
          <Input
            label="Note (optional)"
            maxLength={255}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </form>
      </Modal>

      <Modal
        open={Boolean(thresholding)}
        onClose={() => setThresholding(null)}
        title="Low-stock alert level"
        description="Variants at or below this available quantity surface in the dashboard alerts."
        footer={
          <>
            <Button variant="ghost" onClick={() => setThresholding(null)}>Cancel</Button>
            <Button type="submit" form="threshold-form" loading={busy}>
              Save alert level
            </Button>
          </>
        }
      >
        <form id="threshold-form" onSubmit={submitThreshold}>
          <Input
            label="Threshold"
            type="number"
            min="0"
            step="1"
            required
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
          />
        </form>
      </Modal>

      <Drawer
        open={Boolean(historyFor)}
        onClose={() => setHistoryFor(null)}
        title="Stock history"
        description={historyFor ? `${historyFor.productTitle} — ${historyFor.sku}` : ""}
        size="lg"
      >
        {!history ? (
          <Skeleton className="h-40 w-full" />
        ) : history.items.length === 0 ? (
          <p className="text-sm text-sand-500 dark:text-sand-400">
            No movements recorded yet.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {history.items.map((movement) => (
              <li
                key={movement.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-sand-200 px-4 py-3 dark:border-night-800"
              >
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-sand-800 dark:text-sand-200">
                    {MOVEMENT_LABELS[movement.reason] || movement.reason}
                  </span>
                  <span className="text-xs text-sand-500 dark:text-sand-400">
                    {new Date(movement.createdAt).toLocaleString("en-PH", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                    {movement.note ? ` · ${movement.note}` : ""}
                  </span>
                </div>
                <div className="text-right">
                  <p
                    className={
                      movement.delta > 0
                        ? "text-sm font-semibold tabular-nums text-success-700 dark:text-success-400"
                        : movement.delta < 0
                          ? "text-sm font-semibold tabular-nums text-danger-600 dark:text-danger-400"
                          : "text-sm font-semibold tabular-nums text-sand-500"
                    }
                  >
                    {movement.delta > 0 ? `+${movement.delta}` : movement.delta}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    → {movement.resultingOnHand} on hand
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Drawer>
    </div>
  );
}
