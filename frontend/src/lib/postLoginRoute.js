/**
 * Where a freshly authenticated user belongs (Phase 3.3 follow-up).
 *
 * The login response is the same `UserSerializer` payload as `/auth/me`, so it
 * already carries `is_staff`, `staff_roles` and `is_seller` — the role is known
 * the moment the session exists. The previous behaviour hardcoded `/account`,
 * which dropped an operator into the shopper shell and left the staff console
 * reachable only by typing its URL.
 *
 * This is UX, never security: `IsStaff` / `InStaffGroup` on the backend remain
 * the gate (§4, §10.1). A mislabelled account must still be refused server-side.
 */

/**
 * The destination after a successful login.
 *
 * An explicit `from` (ProtectedRoute bounced the user off a deep link) always
 * wins — somebody who was sent to `/orders/123` before signing in means it, and
 * role-prioritising would ignore the page they actually asked for. `/login`
 * itself is ignored so a self-referencing `from` can never loop.
 *
 * Staff outranks seller: an operator who also owns a store works in the console
 * first, and both layouts keep the storefront navbar, so returning to shopping
 * is one click away.
 */
export function postLoginRoute(user, from) {
  if (from && from !== "/login") return from;
  if (!user) return "/account";
  const roles = user.staff_roles ?? [];
  if (user.is_staff || roles.length > 0) return "/staff";
  if (user.is_seller) return "/seller";
  return "/account";
}