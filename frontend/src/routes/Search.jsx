/**
 * Search (Phase 18 §18.1) — ranked results with faceted filters.
 *
 * Every piece of discovery state lives in the URL (frontend-state rule 6) so
 * a shopper can share or reload a narrowed search and land on the same list.
 * Unlike `/products`, the counts beside each filter come from the server's
 * OR-count facets: picking a category does not zero out its siblings, so the
 * sidebar keeps telling the shopper what else is one click away.
 *
 * The sort vocabulary here is the search service's own (`relevance`,
 * `price_asc`, …) rather than the catalog list's — they are different
 * endpoints with different capabilities, and sending a catalog sort to the
 * search API is a 400.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { cx } from "../lib/cx";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { Checkbox } from "../components/ui/Checkbox";
import { EmptyState } from "../components/ui/EmptyState";
import {
  FilterIcon,
  SearchIcon,
  StoreIcon,
  TagIcon,
  XIcon,
} from "../components/ui/Icons";
import { Pagination } from "../components/ui/Pagination";
import { ProductGrid, ProductGridSkeleton } from "../components/ui/ProductCard";
import { Select } from "../components/ui/Select";
import { useQuickAdd } from "../features/cart/useQuickAdd";
import { searchResults } from "../data/search";

const PAGE_SIZE = 12;

// Blank means "best match" — the default the service already applies.
const SORT_OPTIONS = [
  { value: "", label: "Best match" },
  { value: "newest", label: "Newest first" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "rating", label: "Best rated" },
];

function ActiveChip({ label, onRemove }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-sand-100 px-3 py-1 text-xs font-medium text-sand-700 dark:bg-night-800 dark:text-sand-300">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove filter ${label}`}
        className="rounded-full p-0.5 transition-colors hover:bg-sand-200 dark:hover:bg-night-700"
      >
        <XIcon size={12} />
      </button>
    </span>
  );
}

/**
 * One filter list. Rows whose count is zero are still rendered when they are
 * the active choice — otherwise the only way to leave a filter would be to
 * know it exists before clicking it.
 */
function FacetGroup({ title, items, activeValue, onSelect, emptyLabel = "Nothing here yet" }) {
  if (!items.length) {
    return (
      <div>
        <h2 className="mb-2 text-sm font-semibold text-sand-900 dark:text-sand-100">{title}</h2>
        <p className="px-1 text-sm text-sand-400">{emptyLabel}</p>
      </div>
    );
  }
  return (
    <div>
      <h2 className="mb-2 text-sm font-semibold text-sand-900 dark:text-sand-100">{title}</h2>
      <ul className="flex flex-col gap-0.5">
        {items.map((item) => {
          const selected = item.value === activeValue;
          return (
            <li key={item.value}>
              <button
                type="button"
                onClick={() => onSelect(selected ? "" : item.value)}
                aria-pressed={selected}
                className={cx(
                  "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                  selected
                    ? "bg-moss-50 font-medium text-moss-700 dark:bg-night-800 dark:text-moss-300"
                    : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
                )}
              >
                <span className="min-w-0 truncate">{item.label}</span>
                <span className="shrink-0 text-xs tabular-nums text-sand-400">{item.count}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function Search() {
  const [params, setParams] = useSearchParams();
  const addToCart = useQuickAdd();

  const query = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const brand = params.get("brand") ?? "";
  const minPrice = params.get("min_price") ?? "";
  const maxPrice = params.get("max_price") ?? "";
  const minRating = params.get("min_rating") ?? "";
  const inStock = params.get("in_stock") ?? "";
  const sort = params.get("sort") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);

  const [reload, setReload] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Request identity — a change here is a new fetch. State is only written in
  // async callbacks (frontend-state rule 7).
  const requestKey = [
    query, category, brand, minPrice, maxPrice, minRating, inStock, sort, page, reload,
  ].join("|");
  const [state, setState] = useState({ key: null, status: "idle", data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    searchResults({
      q: query,
      category,
      brand,
      minPrice,
      maxPrice,
      minRating,
      inStock,
      sort,
      page,
      pageSize: PAGE_SIZE,
    })
      .then((data) => {
        if (!cancelled) setState({ key: requestKey, status: "ready", data, error: null });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            key: requestKey,
            status: "error",
            data: null,
            error: err.data?.detail || err.message,
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [requestKey, query, category, brand, minPrice, maxPrice, minRating, inStock, sort, page]);

  const view = state.key === requestKey ? state : { status: "loading", data: null, error: null };
  const { status, data, error } = view;

  const updateParams = (patch) => {
    const next = new URLSearchParams(params);
    Object.entries(patch).forEach(([key, value]) => {
      if (value === "" || value === null || value === undefined) next.delete(key);
      else next.set(key, String(value));
    });
    // Any filter change restarts pagination; page changes keep their value.
    if (!("page" in patch)) next.delete("page");
    setParams(next);
  };

  const clearAll = () => {
    // The keyword is the reason the shopper is here — "clear filters" must
    // not throw away their search.
    const next = new URLSearchParams();
    if (query) next.set("q", query);
    setParams(next);
  };

  const hasFilters = Boolean(
    category || brand || minPrice || maxPrice || minRating || inStock
  );
  const pageCount = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;
  const facets = data?.facets;

  const goToPage = (nextPage) => {
    updateParams({ page: nextPage > 1 ? nextPage : "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb
          className="mb-6"
          items={[{ label: "Home", to: "/" }, { label: "Search" }, ...(query ? [{ label: `“${query}”` }] : [])]}
        />

        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-3xl">
              {query ? <>Results for “{query}”</> : "All products"}
            </h1>
            <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
              {status === "ready"
                ? `${data.count} ${data.count === 1 ? "product" : "products"}`
                : "Searching…"}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              leadingIcon={FilterIcon}
              className="lg:hidden"
              onClick={() => setFiltersOpen((open) => !open)}
              aria-expanded={filtersOpen}
            >
              Filters
            </Button>
            <Select
              aria-label="Sort results"
              className="w-full sm:w-56"
              value={sort}
              onChange={(event) => updateParams({ sort: event.target.value })}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        {status === "ready" && data.fuzzy && (
          <Alert tone="info" className="mb-6" title="Showing close matches">
            Nothing matched “{query}” exactly, so these are the closest products we
            could find. Check the spelling or try a shorter word.
          </Alert>
        )}

        <div className="grid gap-8 lg:grid-cols-[240px_minmax(0,1fr)]">
          <aside
            className={cx("flex-col gap-6", filtersOpen ? "flex" : "hidden", "lg:flex")}
          >
            <FacetGroup
              title="Category"
              activeValue={category}
              onSelect={(value) => updateParams({ category: value })}
              items={(facets?.categories ?? []).map((row) => ({
                value: row.slug,
                label: row.name,
                count: row.count,
              }))}
            />

            <FacetGroup
              title="Brand"
              activeValue={brand}
              onSelect={(value) => updateParams({ brand: value })}
              items={(facets?.brands ?? []).map((row) => ({
                value: row.slug,
                label: row.name,
                count: row.count,
              }))}
              emptyLabel="No brands match yet"
            />

            <div>
              <h2 className="mb-2 text-sm font-semibold text-sand-900 dark:text-sand-100">
                Price (₱)
              </h2>
              <ul className="flex flex-col gap-0.5">
                {(facets?.prices ?? []).map((band) => {
                  // A band is a range, so "selected" compares both bounds.
                  const selected = String(minPrice) === String(band.min ?? "")
                    && String(maxPrice) === String(band.max ?? "");
                  return (
                    <li key={band.label}>
                      <button
                        type="button"
                        onClick={() =>
                          updateParams({
                            min_price: selected ? "" : band.min ?? "",
                            max_price: selected ? "" : band.max ?? "",
                          })
                        }
                        aria-pressed={selected}
                        className={cx(
                          "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                          selected
                            ? "bg-moss-50 font-medium text-moss-700 dark:bg-night-800 dark:text-moss-300"
                            : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
                        )}
                      >
                        <span className="min-w-0 truncate">{band.label}</span>
                        <span className="shrink-0 text-xs tabular-nums text-sand-400">
                          {band.count}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            <FacetGroup
              title="Rating"
              activeValue={minRating}
              onSelect={(value) => updateParams({ min_rating: value })}
              items={(facets?.ratings ?? []).map((row) => ({
                value: String(row.min),
                label: row.label,
                count: row.count,
              }))}
              emptyLabel="No rated products here yet"
            />

            <div>
              <h2 className="mb-2 text-sm font-semibold text-sand-900 dark:text-sand-100">
                Availability
              </h2>
              <Checkbox
                label="In stock only"
                description={
                  facets
                    ? `${facets.stock.inStock} of ${facets.stock.total} available`
                    : undefined
                }
                checked={Boolean(inStock)}
                onChange={(event) =>
                  updateParams({ in_stock: event.target.checked ? "1" : "" })
                }
              />
            </div>

            {hasFilters && (
              <Button variant="ghost" size="sm" onClick={clearAll}>
                Clear all filters
              </Button>
            )}
          </aside>

          <section className="min-w-0" aria-busy={status === "loading"}>
            {hasFilters && (
              <div className="mb-4 flex flex-wrap items-center gap-2">
                {category && (
                  <ActiveChip
                    label={facets?.categories.find((row) => row.slug === category)?.name ?? category}
                    onRemove={() => updateParams({ category: "" })}
                  />
                )}
                {brand && (
                  <ActiveChip
                    label={facets?.brands.find((row) => row.slug === brand)?.name ?? brand}
                    onRemove={() => updateParams({ brand: "" })}
                  />
                )}
                {minPrice && <ActiveChip label={`From ₱${minPrice}`} onRemove={() => updateParams({ min_price: "" })} />}
                {maxPrice && <ActiveChip label={`Up to ₱${maxPrice}`} onRemove={() => updateParams({ max_price: "" })} />}
                {minRating && <ActiveChip label={`${minRating}★ & up`} onRemove={() => updateParams({ min_rating: "" })} />}
                {inStock && <ActiveChip label="In stock only" onRemove={() => updateParams({ in_stock: "" })} />}
              </div>
            )}

            {/* Companion strips — §18.1 "search by store / by category". They
                only appear for a keyword search, where they are an answer. */}
            {status === "ready" && query && (data.stores.length > 0 || data.categories.length > 0) && (
              <div className="mb-6 flex flex-col gap-4">
                {data.stores.length > 0 && (
                  <div>
                    <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-sand-900 dark:text-sand-100">
                      <StoreIcon size={15} className="text-moss-600 dark:text-moss-400" />
                      Stores matching “{query}”
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {data.stores.map((store) => (
                        <a
                          key={store.slug}
                          href={`/store/${store.slug}`}
                          className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white px-3.5 py-1.5 text-sm text-sand-700 transition-colors hover:border-moss-300 hover:text-moss-700 dark:border-night-800 dark:bg-night-900 dark:text-sand-300 dark:hover:border-moss-700 dark:hover:text-moss-300"
                        >
                          <span className="font-medium">{store.name}</span>
                          <span className="text-xs text-sand-400">{store.productCount}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
                {data.categories.length > 0 && (
                  <div>
                    <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-sand-900 dark:text-sand-100">
                      <TagIcon size={15} className="text-moss-600 dark:text-moss-400" />
                      Categories matching “{query}”
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {data.categories.map((row) => (
                        <a
                          key={row.slug}
                          href={`/category/${row.slug}`}
                          className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-white px-3.5 py-1.5 text-sm text-sand-700 transition-colors hover:border-moss-300 hover:text-moss-700 dark:border-night-800 dark:bg-night-900 dark:text-sand-300 dark:hover:border-moss-700 dark:hover:text-moss-300"
                        >
                          <span className="font-medium">{row.name}</span>
                          <span className="text-xs text-sand-400">{row.productCount}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {status === "error" && (
              <Alert tone="danger" title="Search failed">
                <div className="flex flex-wrap items-center gap-3">
                  <span>{error}</span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setReload((value) => value + 1)}
                  >
                    Try again
                  </Button>
                </div>
              </Alert>
            )}

            {status === "ready" && data.items.length === 0 && (
              <EmptyState
                icon={SearchIcon}
                title={query ? `No results for “${query}”` : "Nothing to show"}
                description={
                  hasFilters
                    ? "No products match every filter — try removing one."
                    : "Try a different keyword, or browse the whole catalogue instead."
                }
                action={
                  hasFilters ? (
                    <Button variant="outline" onClick={clearAll}>
                      Clear filters
                    </Button>
                  ) : (
                    <Button variant="outline" onClick={() => setParams(new URLSearchParams())}>
                      Browse all products
                    </Button>
                  )
                }
              />
            )}

            {status === "ready" && data.items.length > 0 && (
              <>
                <ProductGrid products={data.items} onAddToCart={addToCart} columns={3} />
                {pageCount > 1 && (
                  <Pagination
                    className="mt-8 justify-center"
                    total={pageCount}
                    current={page}
                    onChange={goToPage}
                  />
                )}
              </>
            )}

            {status === "loading" && <ProductGridSkeleton count={PAGE_SIZE} columns={3} />}
          </section>
        </div>
      </main>
    </div>
  );
}
