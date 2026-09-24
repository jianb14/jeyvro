/**
 * Cart (Phase 7.1) — store-grouped server cart with live revalidation.
 * Every number on this page comes from the cart API (§6): totals, store
 * subtotals, and line prices. Guests see their session cart with a sign-in
 * prompt; checkout itself arrives with Phase 8.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { CartItem } from "../components/ui/CartItem";
import { CartSummary } from "../components/ui/CartSummary";
import { EmptyState } from "../components/ui/EmptyState";
import { Modal } from "../components/ui/Modal";
import { Price } from "../components/ui/Price";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/ToastProvider";
import { ShoppingCartIcon, TrashIcon } from "../components/ui/Icons";
import { useAuth } from "../features/auth/AuthContext";
import { useCart } from "../features/cart/CartContext";

const EMPTY_TOTALS = { lineCount: 0, itemCount: 0, subtotal: 0, savings: 0 };

export function Cart() {
  const { cart, loading, updateItem, removeItem, clear } = useCart();
  const { user } = useAuth();
  const { push } = useToast();
  const [busyId, setBusyId] = useState(null);
  const [confirmClear, setConfirmClear] = useState(false);

  const items = cart?.items ?? [];
  const groups = cart?.groups ?? [];
  const totals = cart?.totals ?? EMPTY_TOTALS;
  const hasIssues = items.some((item) => !item.purchasable || item.stockLimited);
  const isGuest = cart?.owner === "guest" && !user;

  const changeQty = async (itemId, quantity) => {
    setBusyId(itemId);
    try {
      await updateItem(itemId, quantity);
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not update quantity",
        description: err.data?.detail || err.message,
      });
    } finally {
      setBusyId(null);
    }
  };

  const removeLine = async (itemId) => {
    const line = items.find((item) => item.id === itemId);
    setBusyId(itemId);
    try {
      await removeItem(itemId);
      push({
        tone: "success",
        title: "Removed from cart",
        description: line?.title,
      });
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not remove item",
        description: err.data?.detail || err.message,
      });
    } finally {
      setBusyId(null);
    }
  };

  const clearAll = async () => {
    setConfirmClear(false);
    try {
      await clear();
      push({ tone: "success", title: "Cart cleared" });
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not clear the cart",
        description: err.data?.detail || err.message,
      });
    }
  };

  const checkout = () =>
    push({
      tone: "info",
      title: "Checkout arrives in Phase 8",
      description: "Address, shipping, and order creation are the next build step.",
    });

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb className="mb-6" items={[{ label: "Home", to: "/" }, { label: "Cart" }]} />

        {loading && !cart && (
          <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
            <div className="flex flex-col gap-3">
              {[0, 1, 2].map((row) => (
                <Skeleton key={row} className="h-28 w-full rounded-2xl" />
              ))}
            </div>
            <Skeleton className="h-72 w-full rounded-2xl" />
          </div>
        )}

        {!loading && items.length === 0 && (
          <EmptyState
            icon={ShoppingCartIcon}
            title="Your cart is empty"
            description="Add products from any store — they all live in this one cart."
            action={
              <Link to="/products">
                <Button>Browse products</Button>
              </Link>
            }
          />
        )}

        {items.length > 0 && (
          <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
            <section className="flex flex-col gap-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h1 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
                  Your cart
                </h1>
                <Button
                  variant="ghost"
                  size="sm"
                  leadingIcon={TrashIcon}
                  onClick={() => setConfirmClear(true)}
                >
                  Clear cart
                </Button>
              </div>

              {hasIssues && (
                <Alert tone="warning" title="Some items need attention">
                  Stock or availability changed since they were added — fix the
                  highlighted lines to continue.
                </Alert>
              )}

              {groups.map((group) => (
                <div key={group.storeSlug} className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Link
                      to={`/store/${group.storeSlug}`}
                      className="text-sm font-medium text-sand-700 transition-colors hover:text-moss-700 dark:text-sand-300 dark:hover:text-moss-300"
                    >
                      {group.storeName}
                    </Link>
                    <span className="flex items-center gap-2 text-xs text-sand-500 dark:text-sand-400">
                      {group.itemCount} {group.itemCount === 1 ? "item" : "items"}
                      <Price amount={group.subtotal} size="sm" />
                    </span>
                  </div>
                  <ul className="flex flex-col gap-3">
                    {group.items.map((item) => (
                      <CartItem
                        key={item.id}
                        item={item}
                        onQtyChange={changeQty}
                        onRemove={removeLine}
                        busy={busyId === item.id}
                      />
                    ))}
                  </ul>
                </div>
              ))}

              {isGuest && (
                <Alert tone="info" title="This cart is saved on this device">
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span>Log in and it merges into your account cart automatically.</span>
                    <Link
                      to="/login"
                      state={{ from: "/cart" }}
                      className="font-medium underline underline-offset-4"
                    >
                      Log in
                    </Link>
                  </span>
                </Alert>
              )}
            </section>

            <aside className="lg:sticky lg:top-24 lg:self-start">
              <CartSummary
                totals={totals}
                onCheckout={checkout}
                checkoutDisabled={hasIssues}
                checkoutNote={
                  hasIssues
                    ? "Fix the highlighted lines before checking out."
                    : "Shipping and payment methods are chosen at checkout (Phase 8)."
                }
              />
            </aside>
          </div>
        )}
      </main>

      <Modal
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Clear your cart?"
        description="This removes every line from your cart. It cannot be undone."
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmClear(false)}>
              Keep items
            </Button>
            <Button variant="destructive" onClick={clearAll}>
              Clear cart
            </Button>
          </>
        }
      />
    </div>
  );
}
