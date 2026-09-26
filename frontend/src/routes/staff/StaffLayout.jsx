/**
 * Staff console shell (Phase 13) — the operator-side chrome: same Navbar as
 * the storefront, plus the staff navigation rail. Access is group-based and
 * enforced server-side (PROJECT_CONTEXT §4) — this guard is UX, not security,
 * and non-staff accounts get an honest notice instead of an empty shell.
 */
import { Link, NavLink, Outlet } from "react-router-dom";
import { Navbar } from "../../components/layout/Navbar";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { useAuth } from "../../features/auth/AuthContext";
import { cx } from "../../lib/cx";
import {
  ClockIcon,
  InboxIcon,
  PackageIcon,
  ShieldCheckIcon,
  StoreIcon,
  TagIcon,
  UserIcon,
} from "../../components/ui/Icons";

// `groups` narrows a nav item to the §4 matrix roles; the backend refuses
// out-of-group actions regardless (this is UX, not security).
const NAV = [
  { to: "/staff", label: "Seller approvals", icon: InboxIcon, end: true },
  { to: "/staff/stores", label: "Stores", icon: StoreIcon },
  {
    to: "/staff/catalog",
    label: "Catalog",
    icon: PackageIcon,
    groups: ["moderator", "administrator"],
  },
  {
    to: "/staff/taxonomy",
    label: "Categories & brands",
    icon: TagIcon,
    groups: ["operations", "administrator"],
  },
  { to: "/staff/users", label: "Users", icon: UserIcon },
  {
    to: "/staff/team",
    label: "Staff & roles",
    icon: ShieldCheckIcon,
    administratorOnly: true,
  },
  { to: "/staff/audit", label: "Audit log", icon: ClockIcon },
];

const navClass = ({ isActive }) =>
  cx(
    "inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-moss-100 text-moss-800 dark:bg-moss-900 dark:text-moss-200"
      : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
  );

export function StaffLayout() {
  const { user } = useAuth();
  // /auth/me sends snake_case (`staff_roles`); there is no `is_superuser` in the
  // payload — `is_staff` plus the roles list is the whole contract.
  const roles = user?.staff_roles ?? [];
  const isStaff = Boolean(user?.is_staff || roles.length > 0);
  // Role administration is administrator-only (§4) and each catalog surface
  // belongs to its matrix groups — hide links the role cannot use; the
  // backend refuses them regardless.
  const navItems = NAV.filter((item) => {
    if (item.administratorOnly && !roles.includes("administrator")) return false;
    if (item.groups && !item.groups.some((group) => roles.includes(group))) {
      return false;
    }
    return true;
  });

  if (!isStaff) {
    return (
      <>
        <Navbar />
        <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
          <Alert tone="info" title="Staff access required">
            The operator console is limited to marketplace staff. Access is
            granted per role — every staff action is permission-checked and
            audit-logged, so nothing here is self-service.
          </Alert>
          <div className="mt-6">
            <Link to="/account">
              <Button variant="outline">Back to my account</Button>
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
          <div className="mb-3 hidden flex-col gap-2 lg:flex">
            <p className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
              Operator console
            </p>
            {roles.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {roles.map((role) => (
                  <Badge key={role} tone="moss" size="sm">
                    {role.replace(/_/g, " ")}
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <nav
            aria-label="Staff navigation"
            className="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0"
          >
            {navItems.map(({ to, label, icon: Icon, end }) => (
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
