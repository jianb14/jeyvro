/**
 * Marketplace navbar (Phase 6.1; cart & wishlist wired in Phase 7) — the
 * customer header: brand, server-side search (navigates to /products?q=),
 * category navigation from the API (never hardcoded — marketplace-catalog
 * rule 7), the cart link with a live server-count badge, the wishlist
 * link, the theme toggle, and the auth menu. Mobile presents the same nav
 * as a disclosure panel (frontend-responsive rule 6).
 */
import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { cx } from "../../lib/cx";
import { useTheme } from "../../lib/useTheme";
import { useAuth } from "../../features/auth/AuthContext";
import { useCart } from "../../features/cart/CartContext";
import { getCategories } from "../../data/products";
import { LogoMark, MenuIcon, XIcon, SunIcon, MoonIcon, SearchIcon, ShoppingCartIcon, HeartIcon } from "../ui/Icons";
import { Button } from "../ui/Button";
import { Avatar } from "../ui/Avatar";
import { DropdownMenu } from "../ui/DropdownMenu";
import {
  UserIcon,
  SettingsIcon,
  LogOutIcon,
  StoreIcon,
  PackageIcon,
} from "../ui/Icons";

const navRailClass = ({ isActive }) =>
  cx(
    "whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "text-moss-700 dark:text-moss-300"
      : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
  );

const searchInputClass = (hasClear) =>
  cx(
    "h-10 w-full rounded-xl border border-sand-300 bg-white pl-10 text-sm text-sand-900 transition-[border-color] placeholder:text-sand-400 focus:border-moss-500 focus:outline-2 focus:outline-offset-2 focus:outline-moss-500 dark:border-night-700 dark:bg-night-900 dark:text-sand-100 dark:focus:border-moss-400",
    hasClear ? "pr-10" : "pr-3.5"
  );

const searchClearClass =
  "absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:hover:bg-night-800 dark:hover:text-sand-200";

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="inline-flex size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-sand-300 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
    >
      {theme === "dark" ? <SunIcon size={20} /> : <MoonIcon size={20} />}
    </button>
  );
}

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [categories, setCategories] = useState([]);
  const [input, setInput] = useState("");
  const { user, loading, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    getCategories()
      .then((items) => {
        // Top-level categories only in the rail; deeper levels arrive when
        // the catalog needs sub-navigation.
        if (!cancelled) setCategories(items.filter((category) => category.parent == null));
      })
      .catch(() => {
        if (!cancelled) setCategories([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogout() {
    await logout();
    setMobileOpen(false);
    navigate("/");
  }

  const submitSearch = (event) => {
    event.preventDefault();
    const q = input.trim();
    setMobileOpen(false);
    navigate(q ? `/products?q=${encodeURIComponent(q)}` : "/products");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-sand-200/80 bg-sand-50/85 backdrop-blur-md dark:border-night-800 dark:bg-night-950/85">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex shrink-0 items-center gap-2.5">
          <LogoMark size={30} />
          <span className="hidden font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:inline">
            Jeyvro
          </span>
        </Link>

        <form onSubmit={submitSearch} role="search" className="relative hidden flex-1 md:block">
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sand-400">
            <SearchIcon size={16} />
          </span>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            aria-label="Search products"
            placeholder="Search products…"
            className={searchInputClass(Boolean(input))}
          />
          {input && (
            <button
              type="button"
              onClick={() => setInput("")}
              aria-label="Clear search"
              className={searchClearClass}
            >
              <XIcon size={15} />
            </button>
          )}
        </form>

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/wishlist"
            aria-label="Wishlist"
            title="Wishlist"
            className="hidden size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 sm:inline-flex dark:text-sand-300 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
          >
            <HeartIcon size={20} />
          </Link>

          <Link
            to="/cart"
            aria-label={itemCount > 0 ? `Cart, ${itemCount} items` : "Cart"}
            title="Cart"
            className="relative inline-flex size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-sand-300 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
          >
            <ShoppingCartIcon size={20} />
            {itemCount > 0 && (
              <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-moss-600 px-1 text-[10px] font-semibold text-white dark:bg-moss-500">
                {itemCount > 99 ? "99+" : itemCount}
              </span>
            )}
          </Link>

          <div className="hidden items-center gap-2.5 md:flex">
          <ThemeToggle />
          {loading ? null : user ? (
            <DropdownMenu
              align="end"
              trigger={
                <button aria-label="Account menu" className="rounded-full outline-offset-2 outline-moss-600/60 focus-visible:outline-2">
                  <Avatar name={user.first_name || user.email} size="sm" status="online" />
                </button>
              }
              items={[
                { key: "profile", label: "My account", icon: UserIcon, onSelect: () => navigate("/account") },
                { key: "orders", label: "My orders", icon: PackageIcon, onSelect: () => navigate("/orders") },
                { key: "sell", label: "Sell on Jeyvro", icon: StoreIcon, onSelect: () => navigate("/sell") },
                { key: "settings", label: "Settings", icon: SettingsIcon, onSelect: () => navigate("/account") },
                { key: "sep", divider: true },
                { key: "logout", label: "Log out", icon: LogOutIcon, tone: "danger", onSelect: handleLogout },
              ]}
            />
          ) : (
            <>
              <Link to="/login">
                <Button variant="outline" size="sm">Log in</Button>
              </Link>
              <Link to="/register">
                <Button size="sm">Sign up</Button>
              </Link>
            </>
          )}
        </div>

        <button
          onClick={() => setMobileOpen((o) => !o)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          className="inline-flex size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-sand-300 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400 md:hidden"
        >
          {mobileOpen ? <XIcon size={20} /> : <MenuIcon size={20} />}
          </button>
        </div>
      </nav>

      {categories.length > 0 && (
        <div className="hidden border-t border-sand-200/70 dark:border-night-800/70 md:block">
          <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 sm:px-6 lg:px-8">
            <NavLink to="/products" end className={navRailClass}>
              All products
            </NavLink>
            {categories.map((category) => (
              <NavLink key={category.slug} to={`/category/${category.slug}`} className={navRailClass}>
                {category.name}
              </NavLink>
            ))}
          </div>
        </div>
      )}

      {mobileOpen && (
        <div className="animate-fade-in border-t border-sand-200 bg-sand-50 px-4 pb-5 pt-3 dark:border-night-800 dark:bg-night-950 md:hidden">
          <form onSubmit={submitSearch} role="search" className="relative">
            <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sand-400">
              <SearchIcon size={16} />
            </span>
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              aria-label="Search products"
              placeholder="Search products…"
              className={searchInputClass(Boolean(input))}
            />
            {input && (
              <button
                type="button"
                onClick={() => setInput("")}
                aria-label="Clear search"
                className={searchClearClass}
              >
                <XIcon size={15} />
              </button>
            )}
          </form>

          <div className="mt-3 flex flex-col gap-1">
            <Link
              to="/cart"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
            >
              Cart{itemCount > 0 ? ` (${itemCount})` : ""}
            </Link>
            <Link
              to="/wishlist"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
            >
              Wishlist
            </Link>
            <Link
              to="/orders"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
            >
              My orders
            </Link>
            <Link
              to="/products"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
            >
              All products
            </Link>
            {categories.map((category) => (
              <Link
                key={category.slug}
                to={`/category/${category.slug}`}
                onClick={() => setMobileOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
              >
                {category.name}
              </Link>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <ThemeToggle />
            {loading ? null : user ? (
              <>
                <Link to="/account" className="flex-1" onClick={() => setMobileOpen(false)}>
                  <Button variant="outline" className="w-full">My account</Button>
                </Link>
                <Button variant="outline" onClick={handleLogout}>Log out</Button>
              </>
            ) : (
              <>
                <Link to="/login" className="flex-1" onClick={() => setMobileOpen(false)}>
                  <Button variant="outline" className="w-full">Log in</Button>
                </Link>
                <Link to="/register" className="flex-1" onClick={() => setMobileOpen(false)}>
                  <Button className="w-full">Sign up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
