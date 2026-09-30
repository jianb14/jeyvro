/**
 * Home (Phase 6.1) — customer discovery landing: hero, category
 * navigation, featured/trending shelves, promotional cards, featured
 * stores, and the recently-viewed foundation. Ordering is server-side
 * only (marketplace-catalog rule 3); every state renders (ux-patterns).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { HeroBanner } from "../components/layout/HeroBanner";
import { CategoryGrid } from "../components/layout/CategoryGrid";
import { PromoStrip } from "../components/layout/PromoStrip";
import { Alert } from "../components/ui/Alert";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ProductShelf } from "../components/ui/ProductShelf";
import { Skeleton } from "../components/ui/Skeleton";
import { useQuickAdd } from "../features/cart/useQuickAdd";
import {
  LeafIcon,
  LogoMark,
  StoreIcon,
  TagIcon,
  ZapIcon,
} from "../components/ui/Icons";
import { useCategories } from "../features/catalog/useCategories";
import { getProducts } from "../data/products";
import { fetchPlatformInfo } from "../data/platform";
import { recommendations } from "../data/search";
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
  const [featured, setFeatured] = useState(null);
  const [featuredError, setFeaturedError] = useState(null);
  const [trending, setTrending] = useState(null);
  const [trendingError, setTrendingError] = useState(null);
  const [popular, setPopular] = useState(null);
  const [popularError, setPopularError] = useState(null);
  const [forYou, setForYou] = useState([]);
  const [stores, setStores] = useState(null);
  const [storesError, setStoresError] = useState(null);
  // `null` keeps the section's skeleton until the first load resolves (the
  // strip hides itself entirely once an empty taxonomy comes back).
  const { topLevel, loading: categoriesLoading } = useCategories();
  const categories = categoriesLoading ? null : topLevel;
  const [recent] = useState(() => getRecentlyViewed());

  const [platform, setPlatform] = useState(null);

  // Marketplace name + support contact are platform settings (Phase 13.6);
  // the chrome falls back to the built-in default if the fetch ever fails.
  useEffect(() => {
    let alive = true;
    fetchPlatformInfo()
      .then((info) => {
        if (alive) setPlatform(info);
      })
      .catch(() => {
        /* the footer must never break the page — defaults render instead */
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
    // §18.3: trending is now a real ranking — units sold inside the server's
    // window, not the biggest markdown. Order data finally exists, so the
    // placeholder that ranked by discount is gone rather than kept as a
    // fallback: it was never "trending", and labelling it so was a lie.
    recommendations({ kind: "trending", limit: 8 })
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
    // All-time best sellers, which is a different question from trending and a
    // different answer: something can sell steadily for a year and never trend.
    recommendations({ kind: "popular", limit: 8 })
      .then((data) => {
        if (alive) setPopular(data.items);
      })
      .catch(() => {
        if (alive) setPopularError("Could not load best sellers.");
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    // Personalized from the visitor's own recently-viewed history (§18.3).
    // It travels with the request and is discarded with it — no account, no
    // server-side profile. A first visit resolves to an empty shelf, so this
    // starts as `[]` and the section is simply not rendered.
    const seen = recent.map((item) => item.id).filter(Boolean);
    // No history means there is nothing to personalize from, and the shelf
    // already starts empty — returning here is not "resetting" it, it is
    // declining to ask a question with no answer.
    if (seen.length === 0) return undefined;
    recommendations({ kind: "personalized", seen, limit: 8 })
      .then((data) => {
        if (alive) setForYou(data.items);
      })
      .catch(() => {
        // A failed suggestion is not a reason to interrupt the homepage.
        if (alive) setForYou([]);
      });
    return () => {
      alive = false;
    };
  }, [recent]);

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

      <main className="mx-auto max-w-7xl space-y-10 px-4 pb-24 pt-8 sm:px-6 lg:px-8">
        <HeroBanner />

        {(categories === null || categories.length > 0) && (
          <section className="flex flex-col gap-4">
            <div className="flex items-end justify-between gap-4">
              <h2 className="font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
                Shop by category
              </h2>
              <Link
                to="/products"
                className="shrink-0 text-sm font-medium text-moss-700 transition-colors hover:text-moss-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-moss-300 dark:hover:text-moss-200 dark:focus-visible:outline-moss-400"
              >
                View all
              </Link>
            </div>
            <CategoryGrid categories={categories} loading={categories === null} />
          </section>
        )}

        <PromoStrip />

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
          subtitle="What the marketplace is actually buying right now."
          viewAllHref="/products"
          products={trending}
          loading={trending === null && !trendingError}
          error={trendingError}
          onAddToCart={addToCart}
        />

        <ProductShelf
          title="Best sellers"
          subtitle="All-time favourites, by units sold."
          viewAllHref="/products"
          products={popular}
          loading={popular === null && !popularError}
          error={popularError}
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

        {forYou.length > 0 && (
          <ProductShelf
            title="Recommended for you"
            subtitle="Based on what you've looked at — stays in this browser."
            products={forYou}
            onAddToCart={addToCart}
          />
        )}
      </main>

      <footer className="border-t border-sand-200 py-8 dark:border-night-800">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <span className="flex items-center gap-2">
            <LogoMark size={26} />
            <span className="text-sm text-sand-500 dark:text-sand-400">
              {platform?.platformName ?? "Jeyvro"} Marketplace ·{" "}
              {new Date().getFullYear()}
              {platform?.supportEmail ? (
                <>
                  {" · "}
                  <a
                    href={`mailto:${platform.supportEmail}`}
                    className="transition-colors hover:text-moss-700 dark:hover:text-moss-300"
                  >
                    {platform.supportEmail}
                  </a>
                </>
              ) : null}
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

