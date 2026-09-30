/**
 * Staff console shell (Phase 13) — the operator-side chrome: the AdminShell
 * (grouped rail + own topbar), plus the access guard. Access is group-based and
 * enforced server-side (PROJECT_CONTEXT §4) — this guard is UX, not security,
 * and non-staff accounts get an honest notice instead of an empty shell.
 *
 * The storefront `Navbar` used to sit on top of this layout, which stacked three
 * navigation layers over one page (customer nav, category rail, staff rail) and
 * put a cart badge above a moderation queue. AdminShell replaces all of it.
 */
import { Link, Outlet } from "react-router-dom";
// Only the non-staff branch still wears the storefront chrome, and that is
// deliberate: someone who wandered into /staff without staff access is a
// customer, so they get the normal header and a way out rather than an
// operator shell they cannot use.
import { Navbar } from "../../components/layout/Navbar";
import { AdminShell } from "../../components/layout/AdminShell";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { useAuth } from "../../features/auth/AuthContext";
import {
  ChartIcon,
  ClockIcon,
  CreditCardIcon,
  InboxIcon,
  MegaphoneIcon,
  PackageIcon,
  SettingsIcon,
  ShieldCheckIcon,
  ShoppingBagIcon,
  StarIcon,
  StoreIcon,
  TagIcon,
  UserIcon,
} from "../../components/ui/Icons";

// `groups` narrows a nav item to the §4 matrix roles; the backend refuses
// out-of-group actions regardless (this is UX, not security).
//
// `section` is presentational grouping only — it keeps the rail scannable the
// way an operator thinks about the work (sellers, catalog, money, people,
// system) instead of one flat twelve-item list. It grants nothing.
const NAV = [
  { to: "/staff", label: "Seller approvals", icon: InboxIcon, end: true, section: "Sellers" },
  { to: "/staff/stores", label: "Stores", icon: StoreIcon, section: "Sellers" },
  { to: "/staff/catalog", label: "Catalog", icon: PackageIcon, groups: ["moderator", "administrator"], section: "Catalog" },
  { to: "/staff/taxonomy", label: "Categories & brands", icon: TagIcon, groups: ["operations", "administrator"], section: "Catalog" },
  { to: "/staff/reviews", label: "Reviews", icon: StarIcon, groups: ["support", "moderator", "administrator"], section: "Catalog" },
  { to: "/staff/orders", label: "Orders", icon: ShoppingBagIcon, groups: ["support", "finance", "operations", "administrator"], section: "Orders & money" },
  { to: "/staff/payments", label: "Payments", icon: CreditCardIcon, groups: ["support", "finance", "administrator"], section: "Orders & money" },
  { to: "/staff/campaigns", label: "Campaigns & promos", icon: MegaphoneIcon, groups: ["finance", "operations", "administrator"], section: "Orders & money" },
  // The groups here are the union of the two read gates (§19.1): finance and
  // administrator see the whole page, support and operations see product
  // activity. The page itself hides the money cards rather than the link, so a
  // support operator still gets the half they may read.
  { to: "/staff/analytics", label: "Analytics", icon: ChartIcon, groups: ["support", "operations", "finance", "administrator"], section: "Orders & money" },
  { to: "/staff/users", label: "Users", icon: UserIcon, section: "People" },
  { to: "/staff/team", label: "Staff & roles", icon: ShieldCheckIcon, administratorOnly: true, section: "People" },
  { to: "/staff/settings", label: "Platform settings", icon: SettingsIcon, groups: ["administrator", "finance", "operations"], section: "System" },
  { to: "/staff/audit", label: "Audit log", icon: ClockIcon, section: "System" },
];

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

  // Filter first, group second. A section the viewer has no access to at all
  // must not leave a bare heading behind, so empty groups are dropped. This
  // relies on NAV above being listed in section order — a new entry belongs in
  // its section's block, not appended to the end of the array.
  const sections = [];
  for (const item of navItems) {
    const last = sections[sections.length - 1];
    if (last && last.label === item.section) last.items.push(item);
    else sections.push({ label: item.section, items: [item] });
  }

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
    <AdminShell sections={sections} roles={roles}>
      <Outlet />
    </AdminShell>
  );
}
