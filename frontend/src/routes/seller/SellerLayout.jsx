/**
 * Seller studio shell (Phase 12) — the seller-side chrome: same Navbar as
 * the storefront, plus the seller navigation rail. Non-seller accounts get
 * an honest CTA instead of an empty shell (the backend re-checks the role
 * on every endpoint — this guard is UX, not security).
 */
import { Link, NavLink, Outlet } from "react-router-dom";
import { Navbar } from "../../components/layout/Navbar";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { useAuth } from "../../features/auth/AuthContext";
import { cx } from "../../lib/cx";
import {
  InboxIcon,
  PackageIcon,
  SettingsIcon,
  StoreIcon,
  TagIcon,
} from "../../components/ui/Icons";

const NAV = [
  { to: "/seller", label: "Dashboard", icon: StoreIcon, end: true },
  { to: "/seller/products", label: "Products", icon: TagIcon },
  { to: "/seller/inventory", label: "Inventory", icon: PackageIcon },
  { to: "/seller/orders", label: "Orders", icon: InboxIcon },
  { to: "/seller/settings", label: "Store settings", icon: SettingsIcon },
];

const navClass = ({ isActive }) =>
  cx(
    "inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-moss-100 text-moss-800 dark:bg-moss-900 dark:text-moss-200"
      : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
  );

export function SellerLayout() {
  const { user } = useAuth();

  if (!user?.is_seller) {
    return (
      <>
        <Navbar />
        <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
          <Alert tone="info" title="Seller account required">
            The seller studio is available to approved stores. Apply to sell,
            and staff will review your store.
          </Alert>
          <div className="mt-6">
            <Link to="/sell">
              <Button>Apply to sell on Jeyvro</Button>
            </Link>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-8 sm:px-6 lg:flex-row lg:px-8">
        <aside className="lg:w-56 lg:shrink-0">
          <p className="mb-3 hidden font-display text-lg font-semibold text-sand-900 dark:text-sand-100 lg:block">
            Seller studio
          </p>
          <nav
            aria-label="Seller navigation"
            className="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0"
          >
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={navClass}>
                <Icon size={16} className="shrink-0" />
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </>
  );
}
