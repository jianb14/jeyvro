import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ProductGrid, ProductGridSkeleton } from "../components/ui/ProductCard";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Alert } from "../components/ui/Alert";
import { EmptyState } from "../components/ui/EmptyState";
import { ToastViewport } from "../components/ui/Toast";
import { useToasts } from "../lib/useToasts";
import { LogoMark, SearchIcon, InboxIcon } from "../components/ui/Icons";
import { getProducts } from "../data/products";

export function Home() {
  const [products, setProducts] = useState(null); // null = loading
  const [error, setError] = useState(null);
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const { toasts, push, dismiss } = useToasts();

  useEffect(() => {
    let alive = true;
    getProducts({ q: query })
      .then((items) => {
        if (alive) setProducts(items);
      })
      .catch(() => {
        if (alive) setError("Hindi na-load ang mga produkto. Subukan muli.");
      });
    return () => {
      alive = false;
    };
  }, [query]);

  const runSearch = (q) => {
    setProducts(null); // skeleton while fetching
    setError(null);
    setQuery(q);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    runSearch(input.trim());
  };

  const clearSearch = () => {
    setInput("");
    runSearch("");
  };

  const addToCart = (product) => {
    push({ tone: "success", title: "Added to cart", description: product.title });
  };

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <header className="sticky top-0 z-40 border-b border-sand-200/80 bg-sand-50/85 backdrop-blur-md dark:border-night-800 dark:bg-night-950/85">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <span className="flex items-center gap-2.5">
            <LogoMark size={30} />
            <span className="font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">Jeyvro</span>
            <Badge tone="moss" variant="soft" size="sm" dot>
              Marketplace
            </Badge>
          </span>
          <Link
            to="/design-system"
            className="text-sm font-medium text-sand-500 transition-colors hover:text-moss-700 dark:text-sand-400 dark:hover:text-moss-300"
          >
            Design system
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="animate-slide-up py-12 sm:py-16">
          <h1 className="max-w-2xl font-display text-4xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-5xl">
            Handpicked local goods — <span className="text-moss-600 dark:text-moss-400">calm by design.</span>
          </h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-sand-500 dark:text-sand-400">
            Mock data muna habang binubuo ang Django API — parehong accessors, parehong loading
            at error states, isang file lang ang papalitan kapag handa na ang totoong backend.
          </p>

          <form onSubmit={handleSearch} role="search" className="mt-8 flex w-full max-w-md gap-2">
            <div className="relative flex-1">
              <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sand-400">
                <SearchIcon size={17} />
              </span>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                aria-label="Search products"
                placeholder="Search products…"
                className="h-11 w-full rounded-xl border border-sand-300 bg-white pl-10 pr-3.5 text-sm text-sand-900 transition-[border-color] placeholder:text-sand-400 focus:border-moss-500 focus:outline-2 focus:outline-offset-2 focus:outline-moss-500 dark:border-night-700 dark:bg-night-900 dark:text-sand-100 dark:focus:border-moss-400"
              />
            </div>
            <Button type="submit">Search</Button>
          </form>
        </div>

        {error && (
          <Alert tone="danger" title="May problema" className="mb-6">
            {error}
          </Alert>
        )}

        {products === null ? (
          <ProductGridSkeleton count={6} columns={3} />
        ) : products.length === 0 ? (
          <EmptyState
            icon={InboxIcon}
            title={`No results for "${query}"`}
            description="Subukan ang ibang keyword o i-clear ang search."
            action={
              <Button size="sm" variant="outline" onClick={clearSearch}>
                Clear search
              </Button>
            }
          />
        ) : (
          <>
            <p className="mb-4 text-sm text-sand-500 dark:text-sand-400">
              {products.length} {products.length === 1 ? "product" : "products"}
              {query && (
                <>
                  {" "}for <b>&ldquo;{query}&rdquo;</b>
                </>
              )}
            </p>
            <ProductGrid products={products} onAddToCart={addToCart} columns={3} />
          </>
        )}
      </main>

      <footer className="border-t border-sand-200 py-8 dark:border-night-800">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <span className="flex items-center gap-2">
            <LogoMark size={22} />
            <span className="text-sm text-sand-500 dark:text-sand-400">
              Jeyvro Marketplace · {new Date().getFullYear()}
            </span>
          </span>
          <Link
            to="/design-system"
            className="text-xs text-sand-400 transition-colors hover:text-moss-600 dark:hover:text-moss-300"
          >
            Built on the Jeyvro Design System
          </Link>
        </div>
      </footer>

      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}

