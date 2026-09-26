/**
 * User management (Phase 13.2) — /staff/users.
 *
 * Read broadly, write narrowly (marketplace-admin rule 6): support gets
 * read-only oversight of every account; suspension and reactivation are
 * administrator actions that run through the accounts service — the server
 * revokes live sessions on suspension and audit-logs every change
 * (§4 v1.10).
 */
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { Textarea } from "../../components/ui/Textarea";
import { UserIcon } from "../../components/ui/Icons";
import { useAuth } from "../../features/auth/AuthContext";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 10;

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

export function StaffUsers() {
  const { user: viewer } = useAuth();
  // The backend re-checks everything — this only decides what to render.
  const canAct = (viewer?.staff_roles ?? []).includes("administrator");

  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [reason, setReason] = useState("");
  const [detailUser, setDetailUser] = useState(null);

  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const role = searchParams.get("role") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchAdminUsers({ q, status, role, page, pageSize: PAGE_SIZE })
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [q, status, role, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function runStatusChange() {
    if (!pendingAction) return;
    const { account, action } = pendingAction;
    setBusyId(account.id);
    setNotice(null);
    try {
      await staffApi.setUserStatus(account.id, action, reason.trim());
      setNotice({
        tone: "success",
        message:
          action === "suspend"
            ? `${account.email} suspended — live sessions are revoked immediately and the decision is audit-logged.`
            : `${account.email} reactivated — they can sign in again. The decision is audit-logged.`,
      });
      setPendingAction(null);
      setReason("");
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Users
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Every account in the marketplace. Support has read-only oversight;
          suspension and reactivation are administrator actions and always
          audit-logged.
        </p>
      </header>

      {!canAct && (
        <Alert tone="info" title="Read-only oversight">
          Your role can review accounts but not change them — suspension is an
          administrator action.
        </Alert>
      )}
      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && <Alert tone="danger" title="Could not load users">{error}</Alert>}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <Input
            label="Search users"
            placeholder="Email, name, or phone…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="w-40">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("status", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </Select>
        </div>
        <div className="w-40">
          <Select
            label="Role"
            value={role}
            onChange={(event) => setParam("role", event.target.value)}
          >
            <option value="">All roles</option>
            <option value="customer">Customers</option>
            <option value="seller">Sellers</option>
            <option value="staff">Staff</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {!data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={UserIcon}
          title={q || status || role ? "No users match" : "No users yet"}
          description={
            q || status || role
              ? "Try another search or filter."
              : "Accounts appear here as soon as someone registers."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>User</TH>
              <TH>Roles</TH>
              <TH>Status</TH>
              <TH>Joined</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((account) => (
              <TR key={account.id}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {account.fullName || "—"}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {account.email}
                  </p>
                </TD>
                <TD>
                  <div className="flex flex-wrap gap-1">
                    {account.isSeller && (
                      <Badge tone="info" size="sm">
                        Seller
                      </Badge>
                    )}
                    {account.staffRoles.map((roleName) => (
                      <Badge key={roleName} tone="moss" size="sm">
                        {roleName.replace(/_/g, " ")}
                      </Badge>
                    ))}
                    {!account.isSeller && !account.isStaff && (
                      <Badge tone="neutral" size="sm">
                        Customer
                      </Badge>
                    )}
                  </div>
                </TD>
                <TD>
                  <Badge
                    tone={
                      account.accountStatus === "suspended" ? "danger" : "success"
                    }
                    size="sm"
                  >
                    {account.accountStatus}
                  </Badge>
                  {account.accountStatus === "suspended" && account.suspendedAt && (
                    <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">
                      since {formatDate(account.suspendedAt)}
                    </p>
                  )}
                </TD>
                <TD>{formatDate(account.joinedAt)}</TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setDetailUser(account)}
                    >
                      Details
                    </Button>
                    {canAct && account.accountStatus === "active" && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === account.id}
                        onClick={() => {
                          setPendingAction({ account, action: "suspend" });
                          setReason("");
                        }}
                      >
                        Suspend
                      </Button>
                    )}
                    {canAct && account.accountStatus === "suspended" && (
                      <Button
                        size="sm"
                        loading={busyId === account.id}
                        onClick={() => {
                          setPendingAction({ account, action: "reactivate" });
                          setReason("");
                        }}
                      >
                        Reactivate
                      </Button>
                    )}
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {data && data.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(data.count / PAGE_SIZE)}
          current={page}
          onChange={(next) => setParam("page", String(next))}
        />
      )}

      <Modal
        open={Boolean(detailUser)}
        onClose={() => setDetailUser(null)}
        title="Account details"
        description={detailUser ? detailUser.email : ""}
        footer={
          <Button variant="ghost" onClick={() => setDetailUser(null)}>
            Close
          </Button>
        }
      >
        {detailUser && (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-sand-500 dark:text-sand-400">
                Name
              </dt>
              <dd className="mt-0.5 text-sand-900 dark:text-sand-100">
                {detailUser.fullName || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-sand-500 dark:text-sand-400">
                Phone
              </dt>
              <dd className="mt-0.5 text-sand-900 dark:text-sand-100">
                {detailUser.phone || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-sand-500 dark:text-sand-400">
                Roles
              </dt>
              <dd className="mt-0.5 text-sand-900 dark:text-sand-100">
                {[
                  detailUser.isSeller && "Seller",
                  detailUser.isStaff && "Staff",
                  ...detailUser.staffRoles,
                ]
                  .filter(Boolean)
                  .join(", ") || "Customer"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-sand-500 dark:text-sand-400">
                Email verified
              </dt>
              <dd className="mt-0.5 text-sand-900 dark:text-sand-100">
                {detailUser.emailVerified ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-sand-500 dark:text-sand-400">
                Status
              </dt>
              <dd className="mt-0.5 text-sand-900 dark:text-sand-100">
                {detailUser.accountStatus}
                {detailUser.suspendedAt
                  ? ` since ${formatDate(detailUser.suspendedAt)}`
                  : ""}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-sand-500 dark:text-sand-400">
                Joined
              </dt>
              <dd className="mt-0.5 text-sand-900 dark:text-sand-100">
                {formatDate(detailUser.joinedAt)}
              </dd>
            </div>
          </dl>
        )}
      </Modal>

      <Modal
        open={Boolean(pendingAction)}
        onClose={() => setPendingAction(null)}
        title={
          pendingAction?.action === "suspend"
            ? "Suspend account"
            : "Reactivate account"
        }
        description={
          pendingAction
            ? pendingAction.action === "suspend"
              ? `${pendingAction.account.email} is locked out immediately — live sessions are revoked and the decision is audit-logged.`
              : `${pendingAction.account.email} can sign in again. The decision is audit-logged.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingAction(null)}>
              Cancel
            </Button>
            <Button
              variant={
                pendingAction?.action === "suspend" ? "destructive" : "primary"
              }
              type="submit"
              form="user-status-form"
              loading={busyId === pendingAction?.account?.id}
            >
              {pendingAction?.action === "suspend"
                ? "Suspend account"
                : "Reactivate account"}
            </Button>
          </>
        }
      >
        <form
          id="user-status-form"
          onSubmit={(event) => {
            event.preventDefault();
            runStatusChange();
          }}
        >
          <Textarea
            label={
              pendingAction?.action === "suspend"
                ? "Reason (recommended)"
                : "Note (optional)"
            }
            rows={3}
            maxLength={500}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            hint="Stored on the audit row so the decision is explainable later."
          />
        </form>
      </Modal>
    </div>
  );
}
