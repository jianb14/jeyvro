/**
 * Public storefront page (Phase 4.2) — /store/:slug. API truth only:
 * 404 → EmptyState; active stores only (server enforces it).
 */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { StoreIcon } from "../components/ui/Icons";
import { Skeleton } from "../components/ui/Skeleton";
import { fetchPublicStore } from "../data/stores";

export function Storefront() {
  const { slug } = useParams();
  const [state, setState] = useState({ slug, status: "loading", store: null, error: null });

  useEffect(() => {
    let cancelled = false;
    fetchPublicStore(slug)
      .then((data) => {
        if (!cancelled) setState({ slug, status: "ready", store: data, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        if (err.status === 404) {
          setState({ slug, status: "not-found", store: null, error: null });
        } else {
          setState({ slug, status: "error", store: null, error: err.message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // While a new slug loads, keep showing its loading state — never the
  // previous store's content (all setState calls live in async callbacks).
  const view = state.slug === slug ? state : { status: "loading" };
  const { store, error } = view;

  return (
    <div className="min-h-screen bg-sand-50 dark:bg-night-950">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-12">
        {error && (
          <Alert tone="danger" title="Could not load this store">{error}</Alert>
        )}
        {view.status === "loading" && !error && (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-40 w-full rounded-2xl" />
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}
        {view.status === "not-found" && !error && (
          <EmptyState
            icon={StoreIcon}
            title="Store not found"
            description="This storefront does not exist or is not open to the public yet."
            action={
              <Button onClick={() => window.history.back()}>Go back</Button>
            }
          />
        )}
        {view.status === "ready" && !error && (
          <article className="flex flex-col gap-8">
            <header className="overflow-hidden rounded-2xl border border-sand-200 bg-white dark:border-night-800 dark:bg-night-900">
              {store.banner_url ? (
                <img
                  src={store.banner_url}
                  alt={`${store.name} banner`}
                  className="h-40 w-full object-cover sm:h-56"
                />
              ) : (
                <div className="h-24 bg-moss-100 dark:bg-moss-900 sm:h-32" />
              )}
              <div className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:gap-5">
                {store.logo_url ? (
                  <img
                    src={store.logo_url}
                    alt={`${store.name} logo`}
                    className="size-20 rounded-2xl border border-sand-200 object-cover dark:border-night-700"
                  />
                ) : (
                  <div className="flex size-20 items-center justify-center rounded-2xl border border-sand-200 bg-sand-100 text-moss-700 dark:border-night-700 dark:bg-night-800 dark:text-moss-300">
                    <StoreIcon size={32} />
                  </div>
                )}
                <div className="flex flex-col gap-1">
                  <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
                    {store.name}
                  </h1>
                  <div className="flex items-center gap-2">
                    <Badge tone="success" variant="soft" size="sm">Open store</Badge>
                    {store.rating != null && (
                      <span className="text-sm text-sand-500 dark:text-sand-400">
                        ★ {store.rating}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </header>

            {store.description && (
              <section className="flex flex-col gap-2">
                <h2 className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
                  About this store
                </h2>
                <p className="whitespace-pre-line text-sand-600 dark:text-sand-300">
                  {store.description}
                </p>
              </section>
            )}

            <section className="grid gap-4 sm:grid-cols-2">
              {store.return_policy && (
                <div className="rounded-2xl border border-sand-200 p-5 dark:border-night-800">
                  <h3 className="mb-1 font-medium text-sand-900 dark:text-sand-100">Return policy</h3>
                  <p className="whitespace-pre-line text-sm text-sand-600 dark:text-sand-300">
                    {store.return_policy}
                  </p>
                </div>
              )}
              {store.shipping_policy && (
                <div className="rounded-2xl border border-sand-200 p-5 dark:border-night-800">
                  <h3 className="mb-1 font-medium text-sand-900 dark:text-sand-100">Shipping policy</h3>
                  <p className="whitespace-pre-line text-sm text-sand-600 dark:text-sand-300">
                    {store.shipping_policy}
                  </p>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-dashed border-sand-300 p-8 text-center dark:border-night-700">
              <StoreIcon size={24} className="mx-auto mb-2 text-sand-400" />
              <p className="text-sm text-sand-500 dark:text-sand-400">
                Products from this store arrive with the catalog phase.
              </p>
            </section>
          </article>
        )}
      </main>
    </div>
  );
}