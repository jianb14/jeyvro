/**
 * useCategories — the single source of category navigation state.
 *
 * The taxonomy is read from the API (never hardcoded — marketplace-catalog
 * rule 7) and three surfaces render it: the Navbar rail, the Browse filter
 * sidebar, and the Home category strip. Each used to run its own mount-only
 * effect, which left the Navbar rail stale after staff edited the taxonomy at
 * /staff/taxonomy — the rail outlives the route, so a new category only
 * appeared after a full reload.
 *
 * Refetching on window focus is the fix: staff who creates a category and
 * navigates back to the storefront sees it without a reload, and the request
 * is small enough that the extra call is cheap. Mount + focus are the only two
 * triggers — filter and sort changes must NOT re-request the taxonomy.
 *
 * `topLevel` is the parent==null subset every navigation surface wants;
 * `all` keeps the tree for callers that need children (seller product form,
 * staff console). A failure resolves to an empty list rather than throwing:
 * the footer and the nav rail must never break the page around a nav fetch.
 */
import { useCallback, useEffect, useState } from "react";
import { getCategories } from "../../data/products";

export function useCategories() {
  const [all, setAll] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    getCategories()
      .then((items) => {
        if (cancelled) return;
        setAll(items);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setAll([]);
        setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(load, [load]);

  useEffect(() => {
    // The taxonomy is fetched on mount already; only a *return* to the tab
    // needs a refetch, otherwise every route change would re-request it.
    const onFocus = () => {
      load();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [load]);

  return {
    all,
    topLevel: all.filter((category) => category.parent == null),
    loading,
    error,
    reload: load,
  };
}