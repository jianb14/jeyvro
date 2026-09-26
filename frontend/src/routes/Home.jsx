/**
 * Home (Phase 6.1) — customer discovery landing: hero, category
 * navigation, featured/trending shelves, promotional cards, featured
 * stores, and the recently-viewed foundation. Ordering is server-side
 * only (marketplace-catalog rule 3); every state renders (ux-patterns).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ProductShelf } from "../components/ui/ProductShelf";
import { Skeleton } from "../components/ui/Skeleton";
import { useQuickAdd } from "../features/cart/useQuickAdd";
import { useAuth } from "../features/auth/AuthContext";
import {
  ArrowRightIcon,
  LeafIcon,
  LogoMark,
  StoreIcon,
  TagIcon,
  ZapIcon,
} from "../components/ui/Icons";
import { getCategories, getProducts } from "../data/products";
import { fetchPublicStores } from "../data/stores";
import { getRecentlyViewed } from "../lib/recentlyViewed";

const PROMOS = [
  {
    href: "/products?sort=newest",
    icon: ZapIcon,
    title: "New arrivals",
    text: "The latest from our makers, newest first.",
  },
  {
    href: "/products?max_price=500",
    icon: TagIcon,
    title: "Under ₱500",
    text: "Everyday finds at small prices.",
  },
  {
    href: "/products?sort=discount",
    icon: LeafIcon,
    title: "Biggest savings",
    text: "Ranked by real discount — never a fake deal.",
  },
];

function FeaturedStoreCard({ store }) {
  return (
    <Link
      to={`/store/${store.slug}`}
      className="flex h-full flex-col gap-3 rounded-2xl border border-sand-200 bg-white p-5 shadow-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lift dark:border-night-800 dark:bg-night-900"
    >
      <div className="flex items-center gap-3">
        {store.logo_url ? (
          <img
            src={store.logo_url}
            alt={`${store.name} logo`}
            className="size-12 shrink-0 rounded-xl border border-sand-200 object-cover dark:border-night-700"
          />
        ) : (
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-moss-100 text-moss-700 dark:bg-moss-900 dark:text-moss-300">
            <StoreIcon size={20} />
          </span>
        )}
        <div className="min-w-0">
          <p className="truncate font-medium text-sand-900 dark:text-sand-100">{store.name}</p>
          <p className="text-xs text-sand-500 dark:text-sand-400">
            {store.rating != null ? `★ ${store.rating}` : "New store — no ratings yet"}
          </p>
        </div>
      </div>
      {store.description && (
        <p className="line-clamp-2 text-sm leading-relaxed text-sand-500 dark:text-sand-400">
          {store.description}
        </p>
      )}
    </Link>
  );
}

export function Home() {
  const addToCart = useQuickAdd();
  const { user } = useAuth();
  const [categories, setCategories] = useState(null);
  const [featured, setFeatured] = useState(null);
  const [featuredError, setFeaturedError] = useState(null);
  const [trending, setTrending] = useState(null);
  const [trendingError, setTrendingError] = useState(null);
  const [stores, setStores] = useState(null);
  const [storesError, setStoresError] = useState(null);
  const [recent] = useState(() => getRecentlyViewed());

  useEffect(() => {
    let alive = true;
    getCategories()
      .then((items) => {
        if (alive) setCategories(items.filter((category) => category.parent == null));
      })
      .catch(() => {
        if (alive) setCategories([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    getProducts({ sort: "newest", pageSize: 8 })
      .then((data) => {
        if (alive) setFeatured(data.items);
      })
      .catch(() => {
        if (alive) setFeaturedError("Could not load featured products.");
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    // Trending foundation: biggest real discount, computed server-side,
    // until order events bring true trend data (Phase 8).
    getProducts({ sort: "discount", pageSize: 8 })
      .then((data) => {
        if (alive) setTrending(data.items);
      })
      .catch(() => {
        if (alive) setTrendingError("Could not load trending products.");
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    fetchPublicStores({ pageSize: 4 })
      .then((data) => {
        if (alive) setStores(data.items);
      })
      .catch(() => {
        if (alive) setStoresError("Could not load featured stores.");
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-7xl space-y-14 px-4 pb-24 pt-8 sm:px-6 lg:px-8">
        <section className="animate-slide-up py-6 sm:py-10">
          <Badge tone="moss" variant="soft" size="sm" dot>
            Marketplace
          </Badge>
          <h1 className="mt-4 max-w-2xl font-display text-4xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-5xl">
            Handpicked local goods — <span className="text-moss-600 dark:text-moss-400">calm by design.</span>
          </h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-sand-500 dark:text-sand-400">
            Every product below comes straight from the marketplace API —
            real sellers, server-resolved prices, honest stock.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/products">
              <Button size="lg" trailingIcon={ArrowRightIcon}>Browse products</Button>
            </Link>
            {/* Sellers jump straight to the studio; everyone else starts the
                apply flow (ProtectedRoute handles logged-out visitors). */}
            <Link to={user?.is_seller ? "/seller" : "/sell"}>
              <Button size="lg" variant="outline">
                {user?.is_seller ? "Open Seller studio" : "Sell on Jeyvro"}
              </Button>
            </Link>
          </div>
        </section>

        {(categories === null || categories.length > 0) && (
          <section className="flex flex-col gap-4">
            <h2 className="font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
              Shop by category
            </h2>
            {categories === null ? (
              <div className="flex flex-wrap gap-2" aria-hidden="true">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-32 rounded-full" />
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {categories.map((category) => (
                  <Link
                    key={category.slug}
                    to={`/category/${category.slug}`}
                    className="rounded-full border border-sand-300 bg-white px-4 py-2 text-sm font-medium text-sand-700 transition-colors hover:border-moss-400 hover:text-moss-700 dark:border-night-700 dark:bg-night-900 dark:text-sand-300 dark:hover:border-moss-600 dark:hover:text-moss-300"
                  >
                    {category.name}
                  </Link>
                ))}
              </div>
            )}
          </section>
        )}

        <ProductShelf
          title="Featured products"
          subtitle="Fresh from our makers — newest first."
          viewAllHref="/products?sort=newest"
          products={featured}
          loading={featured === null && !featuredError}
          error={featuredError}
          onAddToCart={addToCart}
        />

        <ProductShelf
          title="Trending products"
          subtitle="Biggest savings right now — ranked by real discount."
          viewAllHref="/products?sort=discount"
          products={trending}
          loading={trending === null && !trendingError}
          error={trendingError}
          onAddToCart={addToCart}
        />

        <section className="grid gap-5 md:grid-cols-3">
          {PROMOS.map(({ href, icon: Icon, title, text }) => (
            <Link key={href} to={href}>
              <Card hover className="flex h-full items-start gap-4 p-5">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-moss-100 text-moss-700 dark:bg-moss-900 dark:text-moss-300">
                  <Icon size={20} />
                </span>
                <span className="flex flex-col gap-1">
                  <span className="font-display text-base font-semibold text-sand-900 dark:text-sand-100">
                    {title}
                  </span>
                  <span className="text-sm leading-relaxed text-sand-500 dark:text-sand-400">
                    {text}
                  </span>
                </span>
              </Card>
            </Link>
          ))}
        </section>

        <section className="flex flex-col gap-4">
          <div>
            <h2 className="font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
              Featured stores
            </h2>
            <p className="mt-0.5 text-sm text-sand-500 dark:text-sand-400">
              Independent sellers, run with care.
            </p>
          </div>
          {storesError ? (
            <Alert tone="danger" title="Could not load featured stores">
              {storesError}
            </Alert>
          ) : stores === null ? (
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4" aria-hidden="true">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-28 w-full rounded-2xl" />
              ))}
            </div>
          ) : stores.length === 0 ? (
            <EmptyState
              compact
              icon={StoreIcon}
              title="No stores yet"
              description="Approved stores appear here as sellers open up."
            />
          ) : (
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
              {stores.map((store) => (
                <FeaturedStoreCard key={store.slug} store={store} />
              ))}
            </div>
          )}
        </section>

        {recent.length > 0 && (
          <ProductShelf
            title="Recently viewed"
            subtitle="Pick up where you left off."
            products={recent}
            onAddToCart={addToCart}
          />
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
            to="/products"
            className="text-sm text-sand-500 transition-colors hover:text-moss-700 dark:text-sand-400 dark:hover:text-moss-300"
          >
            Browse all products
          </Link>
        </div>
      </footer>
    </div>
  );
}

