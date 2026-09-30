/**
 * Marketplace navbar (Phase 6.1; cart & wishlist wired in Phase 7) — the
 * customer header: brand, server-side search (navigates to /products?q=),
 * category navigation from the API (never hardcoded — marketplace-catalog
 * rule 7), the cart link with a live server-count badge, the wishlist
 * link, the theme toggle, and the auth menu. Mobile presents the same nav
 * as a disclosure panel (frontend-responsive rule 6).
 */
import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { cx } from "../../lib/cx";
import { useAuth } from "../../features/auth/AuthContext";
import { useCart } from "../../features/cart/CartContext";
import { useCategories } from "../../features/catalog/useCategories";
import { SearchAutocomplete } from "./SearchAutocomplete";
import { LogoLockup, MenuIcon, XIcon, ShoppingCartIcon, HeartIcon } from "../ui/Icons";
import { Button } from "../ui/Button";
import { Avatar } from "../ui/Avatar";
import { DropdownMenu } from "../ui/DropdownMenu";
import { ThemeToggle } from "../ui/ThemeToggle";
import {
  UserIcon,
  SettingsIcon,
  LogOutIcon,
  StoreIcon,
  PackageIcon,
  ShieldCheckIcon,
} from "../ui/Icons";
import { NotificationBell } from "../ui/NotificationBell";
import { MessageSquareIcon, TagIcon } from "../ui/Icons";


const navRailClass = ({ isActive }) =>
  cx(
    "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
    isActive
      ? "text-moss-700 dark:text-moss-300"
      : "text-sand-600 hover:bg-sand-100 hover:text-moss-700 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-moss-300"
  );

// Right padding is supplied by SearchAutocomplete (it widens for the clear
// button), so this class must not set `pr-*`.
const searchInputClass =
  "h-10 w-full rounded-xl border border-sand-300 bg-white pl-10 text-sm text-sand-900 transition-[border-color] placeholder:text-sand-400 focus:border-moss-500 focus:outline-2 focus:outline-offset-2 focus:outline-moss-500 dark:border-night-700 dark:bg-night-900 dark:text-sand-100 dark:focus:border-moss-400";

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  // Top-level categories only in the rail; deeper levels arrive when the
  // catalog needs sub-navigation. The hook refetches on window focus so a
  // category created at /staff/taxonomy reaches this rail without a reload.
  const { topLevel: categories } = useCategories();
  const { user, loading, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    setMobileOpen(false);
    navigate("/");
  }

  // Suggestions and the full results page both live under /search, so the
  // navbar never sends a shopper to a page that cannot show facets.
  const runSearch = (q) => {
    setMobileOpen(false);
    navigate(q ? `/search?q=${encodeURIComponent(q)}` : "/search");
  };

  // Staff power is group-based (§4), so the roles list counts alongside the
  // staff flag — a user with either one works in the operator console. This only
  // decides which links to draw; StaffLayout and the backend still refuse the
  // pages themselves.
  const isStaff = Boolean(user?.is_staff || (user?.staff_roles ?? []).length > 0);
  const isSeller = Boolean(user?.is_seller);

  // The console and the studio are where these accounts actually work, so they
  // sit above the shopper entries rather than buried under them. Before these
  // links existed the only way into /staff was to type the URL by hand.
  const roleItems = [
    ...(isStaff
      ? [
          {
            key: "staff",
            label: "Operator console",
            icon: ShieldCheckIcon,
            onSelect: () => navigate("/staff"),
          },
        ]
      : []),
    ...(isSeller
      ? [
          {
            key: "seller",
            label: "Seller studio",
            icon: StoreIcon,
            onSelect: () => navigate("/seller"),
          },
        ]
      : []),
  ];
  const roleDivider = roleItems.length > 0 ? [{ key: "role-sep", divider: true }] : [];

  return (
    <header className="sticky top-0 z-40 border-b border-sand-200/80 bg-sand-50/85 backdrop-blur-md dark:border-night-800 dark:bg-night-950/85">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex shrink-0 items-center">
          <LogoLockup size={30} />
        </Link>

        <SearchAutocomplete
          className="hidden flex-1 md:block"
          inputClassName={searchInputClass}
          onSubmit={runSearch}
          onSelect={(path) => {
            setMobileOpen(false);
            navigate(path);
          }}
        />

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/vouchers"
            aria-label="Voucher center"
            title="Voucher center"
            className="hidden size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 sm:inline-flex dark:text-sand-300 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
          >
            <TagIcon size={20} />
          </Link>

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

          <NotificationBell />

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
                ...roleItems,
                ...roleDivider,
                { key: "messages", label: "Messages", icon: MessageSquareIcon, onSelect: () => navigate("/account/messages") },
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
        <div className="hidden border-t border-sand-200/50 dark:border-night-800/60 md:block">
          {/* py-2 gives the rail breathing room so the links never sit flush
              against the header's dividing line; the link padding itself
              (navRailClass) is deliberately tight so the row stays short. */}
          <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2 sm:px-6 lg:px-8">
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
          <SearchAutocomplete
            inputClassName={searchInputClass}
            onSubmit={runSearch}
            onSelect={(path) => {
              setMobileOpen(false);
              navigate(path);
            }}
          />

          <div className="mt-3 flex flex-col gap-1">
            <Link
              to="/cart"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
            >
              Cart{itemCount > 0 ? ` (${itemCount})` : ""}
            </Link>
            <Link
              to="/vouchers"
              onClick={() => setMobileOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
            >
              Vouchers
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

          {/* A staff or seller account needs the console/studio one tap away here
              too — this panel is the only nav a small-screen user gets. Its own
              row above the account buttons, since that row already carries the
              theme toggle, account and logout. */}
          {user && roleItems.length > 0 && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              {isStaff && (
                <Link to="/staff" onClick={() => setMobileOpen(false)}>
                  <Button variant="outline" className="w-full">Operator console</Button>
                </Link>
              )}
              {isSeller && (
                <Link to="/seller" onClick={() => setMobileOpen(false)}>
                  <Button variant="outline" className="w-full">Seller studio</Button>
                </Link>
              )}
            </div>
          )}

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
