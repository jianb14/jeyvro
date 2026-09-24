/**
 * Wishlist (Phase 7.2) — the customer's saved products. Private per
 * customer (marketplace-community rule 5); availability is server truth,
 * so items that left the catalog show a remove-only state instead of a
 * broken card. Adding to cart reuses the shared quick-add behavior.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ProductGrid, ProductGridSkeleton } from "../components/ui/ProductCard";
import { useToast } from "../components/ui/ToastProvider";
import { AlertTriangleIcon, HeartIcon, TrashIcon } from "../components/ui/Icons";
import { useQuickAdd } from "../features/cart/useQuickAdd";
import { useWishlist } from "../features/wishlist/WishlistContext";

export function Wishlist() {
  const { entries, loading, remove } = useWishlist();
  const quickAdd = useQuickAdd();
  const { push } = useToast();
  const [busyId, setBusyId] = useState(null);

  const saved = entries.filter((entry) => entry.product);
  const available = saved.filter((entry) => entry.available).map((entry) => entry.product);
  const unavailable = saved.filter((entry) => !entry.available);

  const removeEntry = async (productId, title) => {
    setBusyId(productId);
    try {
      await remove(productId);
      push({ tone: "success", title: "Removed from wishlist", description: title });
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not remove the item",
        description: err.data?.detail || err.message,
      });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb className="mb-6" items={[{ label: "Home", to: "/" }, { label: "Wishlist" }]} />

        <div className="mb-6">
          <h1 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-3xl">
            Your wishlist
          </h1>
          <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
            Saved items, synced to your account.
          </p>
        </div>

        {loading && saved.length === 0 && <ProductGridSkeleton count={4} columns={4} />}

        {!loading && saved.length === 0 && (
          <EmptyState
            icon={HeartIcon}
            title="Nothing saved yet"
            description="Tap the heart on any product and it waits for you here."
            action={
              <Link to="/products">
                <Button>Browse products</Button>
              </Link>
            }
          />
        )}

        {available.length > 0 && (
          <ProductGrid products={available} onAddToCart={quickAdd} columns={4} />
        )}

        {unavailable.length > 0 && (
          <section className="mt-10 flex flex-col gap-3">
            <Alert tone="warning" title="No longer available">
              These saved items left the marketplace — remove them to tidy the list.
            </Alert>
            <ul className="flex flex-col gap-2">
              {unavailable.map((entry) => (
                <li
                  key={entry.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sand-200 bg-white p-4 dark:border-night-800 dark:bg-night-900"
                >
                  <span className="flex min-w-0 items-center gap-2 text-sm text-sand-500 dark:text-sand-400">
                    <AlertTriangleIcon size={15} className="shrink-0" />
                    <span className="truncate">{entry.product.title}</span>
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    leadingIcon={TrashIcon}
                    loading={busyId === entry.productId}
                    onClick={() => removeEntry(entry.productId, entry.product.title)}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
