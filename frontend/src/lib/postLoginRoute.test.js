import { describe, it, expect } from "vitest";
import { postLoginRoute } from "./postLoginRoute";

// Snake_case exactly as `/auth/login` and `/auth/me` send it — the helper reads
// the raw payload, so the fixtures must not be renamed to a camelCase contract.
const CUSTOMER = {
  id: 1,
  email: "buyer@example.com",
  is_seller: false,
  is_staff: false,
  staff_roles: [],
};
const SELLER = { ...CUSTOMER, id: 2, is_seller: true };
const STAFF = { ...CUSTOMER, id: 3, is_staff: true, staff_roles: ["administrator"] };
// Power is group-based, not all-or-nothing (§4): a staffer with no group in the
// serialised roles list is still staff.
const FLAG_ONLY = { ...CUSTOMER, id: 4, is_staff: true, staff_roles: [] };
const SELLER_STAFF = { ...SELLER, id: 5, is_staff: true, staff_roles: ["support"] };

describe("postLoginRoute", () => {
  it("sends a plain shopper to their account", () => {
    expect(postLoginRoute(CUSTOMER)).toBe("/account");
  });

  it("sends a seller to the seller studio", () => {
    expect(postLoginRoute(SELLER)).toBe("/seller");
  });

  it("sends staff to the operator console", () => {
    expect(postLoginRoute(STAFF)).toBe("/staff");
  });

  it("treats the staff flag as staff even with an empty roles list", () => {
    expect(postLoginRoute(FLAG_ONLY)).toBe("/staff");
  });

  it("sends a staff member who also sells to the console, not the studio", () => {
    expect(postLoginRoute(SELLER_STAFF)).toBe("/staff");
  });

  it("honours an explicit destination over the role", () => {
    // Deep link bounced by ProtectedRoute — the page asked for is the one wanted.
    expect(postLoginRoute(STAFF, "/orders")).toBe("/orders");
    expect(postLoginRoute(CUSTOMER, "/account/messages")).toBe("/account/messages");
  });

  it("ignores a self-referencing /login from so it cannot loop", () => {
    expect(postLoginRoute(STAFF, "/login")).toBe("/staff");
  });

  it("falls back to /account when there is no session payload", () => {
    expect(postLoginRoute(null)).toBe("/account");
    expect(postLoginRoute(undefined, null)).toBe("/account");
  });

  it("tolerates a payload with no staff_roles key at all", () => {
    expect(postLoginRoute({ id: 6, email: "x@example.com" })).toBe("/account");
  });
});