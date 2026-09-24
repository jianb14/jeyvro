/**
 * Browse (Phase 6.2) — product listing with server-side search, filters,
 * sort, and pagination. All discovery state lives in the URL
 * (frontend-state rule 6) so refresh/Back work; the same component serves
 * the category page when routed under /category/:slug.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { cx } from "../lib/cx";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { FilterIcon, InboxIcon, XIcon } from "../components/ui/Icons";
import { Input } from "../components/ui/Input";
import { Pagination } from "../components/ui/Pagination";
import { ProductGrid, ProductGridSkeleton } from "../components/ui/ProductCard";
import { Select } from "../components/ui/Select";
import { useQuickAdd } from "../features/cart/useQuickAdd";
import { getCategories, getProducts } from "../data/products";

const PAGE_SIZE = 12;

const SORT_OPTIONS = [
  { value: "", label: "Newest first" },
  { value: "price", label: "Price: low to high" },
  { value: "-price", label: "Price: high to low" },
  { value: "discount", label: "Biggest discount" },
  { value: "title", label: "Title A–Z" },
];

function PriceFilter({ minPrice, maxPrice, onApply }) {
  const [min, setMin] = useState(minPrice);
  const [max, setMax] = useState(maxPrice);
  const numeric = (value) => value.replace(/[^\d.]/g, "");

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onApply({ min, max });
      }}
      className="flex flex-col gap-2"
    >
      <div className="flex gap-2">
        <Input
          aria-label="Minimum price in pesos"
          placeholder="₱ Min"
          inputMode="numeric"
          value={min}
          onChange={(event) => setMin(numeric(event.target.value))}
        />
        <Input
          aria-label="Maximum price in pesos"
          placeholder="₱ Max"
          inputMode="numeric"
          value={max}
          onChange={(event) => setMax(numeric(event.target.value))}
        />
      </div>
      <Button type="submit" variant="outline" size="sm">Apply price</Button>
    </form>
  );
}

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

export function Browse() {
  const [params, setParams] = useSearchParams();
  const { slug: routeCategory } = useParams();
  const navigate = useNavigate();
  const addToCart = useQuickAdd();

  const query = params.get("q") ?? "";
  const category = routeCategory || params.get("category") || "";
  const sort = params.get("sort") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const minPrice = params.get("min_price") ?? "";
  const maxPrice = params.get("max_price") ?? "";

  const [categories, setCategories] = useState([]);
  const [reload, setReload] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Request identity — a change here is a new fetch. State is only written
  // in async callbacks (Storefront pattern; frontend-state rule 7).
  const requestKey = [query, category, sort, page, minPrice, maxPrice, reload].join("|");
  const [state, setState] = useState({ key: null, status: "idle", data: null, error: null });

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

  useEffect(() => {
    let cancelled = false;
    getProducts({
      q: query,
      category,
      sort,
      page,
      minPrice,
      maxPrice,
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
  }, [requestKey, query, category, sort, page, minPrice, maxPrice]);

  const view =
    state.key === requestKey ? state : { status: "loading", data: null, error: null };

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
    if (routeCategory) navigate("/products");
    else setParams(new URLSearchParams());
  };

  const topCategories = categories.filter((item) => item.parent == null);
  const currentCategory = categories.find((item) => item.slug === category);
  const { status, data, error } = view;
  const pageCount = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;
  const hasFilters = Boolean(query || category || minPrice || maxPrice || sort);
  const title = currentCategory?.name ?? (query ? `Results for “${query}”` : "All products");

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
          items={[
            { label: "Home", to: "/" },
            ...(currentCategory ? [{ label: "Products", to: "/products" }] : []),
            { label: title },
          ]}
        />

        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-3xl">
              {title}
            </h1>
            <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
              {status === "ready"
                ? `${data.count} ${data.count === 1 ? "product" : "products"}`
                : "Loading products…"}
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
              aria-label="Sort products"
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

        <div className="grid gap-8 lg:grid-cols-[240px_minmax(0,1fr)]">
          <aside className={cx("flex-col gap-6", filtersOpen ? "flex" : "hidden", "lg:flex")}>
            {!routeCategory && (
              <div>
                <h2 className="mb-2 text-sm font-semibold text-sand-900 dark:text-sand-100">
                  Category
                </h2>
                <ul className="flex flex-col gap-0.5">
                  <li>
                    <button
                      type="button"
                      onClick={() => updateParams({ category: "" })}
                      className={cx(
                        "w-full rounded-lg px-3 py-2 text-left text-sm transition-colors",
                        !category
                          ? "bg-moss-50 font-medium text-moss-700 dark:bg-night-800 dark:text-moss-300"
                          : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
                      )}
                    >
                      All categories
                    </button>
                  </li>
                  {topCategories.map((item) => (
                    <li key={item.slug}>
                      <button
                        type="button"
                        onClick={() => updateParams({ category: item.slug })}
                        className={cx(
                          "w-full rounded-lg px-3 py-2 text-left text-sm transition-colors",
                          category === item.slug
                            ? "bg-moss-50 font-medium text-moss-700 dark:bg-night-800 dark:text-moss-300"
                            : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
                        )}
                      >
                        {item.name}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <h2 className="mb-2 text-sm font-semibold text-sand-900 dark:text-sand-100">
                Price (₱)
              </h2>
              <PriceFilter
                key={`${minPrice}|${maxPrice}`}
                minPrice={minPrice}
                maxPrice={maxPrice}
                onApply={({ min, max }) => updateParams({ min_price: min, max_price: max })}
              />
            </div>

            {hasFilters && (
              <Button variant="ghost" size="sm" onClick={clearAll}>
                Clear all filters
              </Button>
            )}
          </aside>

          <section className="min-w-0" aria-busy={status === "loading"}>
            {(query || category || minPrice || maxPrice) && (
              <div className="mb-4 flex flex-wrap items-center gap-2">
                {query && (
                  <ActiveChip label={`“${query}”`} onRemove={() => updateParams({ q: "" })} />
                )}
                {category && (
                  <ActiveChip
                    label={currentCategory?.name ?? category}
                    onRemove={clearAll}
                  />
                )}
                {minPrice && (
                  <ActiveChip
                    label={`From ₱${minPrice}`}
                    onRemove={() => updateParams({ min_price: "" })}
                  />
                )}
                {maxPrice && (
                  <ActiveChip
                    label={`Up to ₱${maxPrice}`}
                    onRemove={() => updateParams({ max_price: "" })}
                  />
                )}
              </div>
            )}

            {status === "error" && (
              <Alert tone="danger" title="Could not load products">
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
                icon={InboxIcon}
                title="No products found"
                description="Try a different keyword, or clear the filters to see everything."
                action={
                  <Button variant="outline" onClick={clearAll}>
                    Clear filters
                  </Button>
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
