/**
 * Staff & roles (Phase 13.1) — /staff/team.
 *
 * The permission-audit surface: who can act in the operator console, with
 * which role. Role changes are administrator actions that run through the
 * accounts service — every assign/remove is audit-logged, self and superuser
 * targets are refused server-side, and the last administrator can never be
 * demoted (§4 v1.10). The backend re-checks all of it; the guard here is UX.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { ShieldCheckIcon, XIcon } from "../../components/ui/Icons";
import { useAuth } from "../../features/auth/AuthContext";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 10;

const ASSIGNABLE_GROUPS = [
  "support",
  "moderator",
  "finance",
  "operations",
  "administrator",
  "super_administrator",
];

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

function roleLabel(roleName) {
  return roleName.replace(/_/g, " ");
}

export function StaffTeam() {
  const { user: viewer } = useAuth();
  const isAdministrator = (viewer?.staff_roles ?? []).includes("administrator");

  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [assignTarget, setAssignTarget] = useState(null);
  const [assignGroup, setAssignGroup] = useState("");
  const [removeTarget, setRemoveTarget] = useState(null);

  const q = searchParams.get("q") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    if (!isAdministrator) return undefined;
    let cancelled = false;
    staffApi
      .fetchStaffMembers({ q, page, pageSize: PAGE_SIZE })
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
  }, [q, page, isAdministrator]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function runRoleChange() {
    const pending = removeTarget
      ? { ...removeTarget, action: "remove" }
      : assignTarget && assignGroup
        ? { member: assignTarget, group: assignGroup, action: "assign" }
        : null;
    if (!pending) return;
    setBusyId(pending.member.id);
    setNotice(null);
    try {
      await staffApi.changeStaffRole(pending.member.id, pending.action, pending.group);
      setNotice({
        tone: "success",
        message:
          pending.action === "assign"
            ? `${roleLabel(pending.group)} granted to ${pending.member.email} — audit-logged.`
            : `${roleLabel(pending.group)} removed from ${pending.member.email} — audit-logged.`,
      });
      setAssignTarget(null);
      setAssignGroup("");
      setRemoveTarget(null);
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  if (!isAdministrator) {
    return (
      <div className="flex flex-col gap-6">
        <Alert tone="info" title="Administrators only">
          Staff role assignment is an administrator power — every action is
          permission-checked server-side, so this page stays closed to other
          groups.
        </Alert>
        <div>
          <Link to="/staff">
            <Button variant="outline">Back to seller approvals</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Staff &amp; roles
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Who can act in the operator console, with which powers. Role changes
          are administrator actions — every assign and remove is audit-logged
          and appears in the audit log.
        </p>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && (
        <Alert tone="danger" title="Could not load staff">
          {error}
        </Alert>
      )}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <SearchInput
            label="Search staff"
            placeholder="Email or name…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onClear={() => {
              setSearch("");
              setParam("q", "");
            }}
          />
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {!data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={ShieldCheckIcon}
          title={q ? "No staff match" : "No staff accounts yet"}
          description={
            q
              ? "Try another search."
              : "Promoted staff appear here the moment an administrator grants a role."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Member</TH>
              <TH>Roles</TH>
              <TH>Status</TH>
              <TH>Joined</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((member) => (
              <TR key={member.id}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {member.fullName || "—"}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {member.email}
                  </p>
                </TD>
                <TD>
                  {member.isSuperuser ? (
                    <>
                      <Badge tone="warning" size="sm">
                        super administrator
                      </Badge>
                      <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">
                        Managed through Django superusers — no role changes here.
                      </p>
                    </>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {member.staffRoles.map((roleName) => (
                        <span
                          key={roleName}
                          className="inline-flex items-center gap-1"
                        >
                          <Badge tone="moss" size="sm">
                            {roleLabel(roleName)}
                          </Badge>
                          <button
                            type="button"
                            aria-label={`Remove the ${roleLabel(roleName)} role from ${member.email}`}
                            className="rounded p-0.5 text-sand-400 transition-colors hover:text-danger-600 dark:hover:text-danger-400"
                            onClick={() => setRemoveTarget({ member, group: roleName })}
                          >
                            <XIcon size={12} />
                          </button>
                        </span>
                      ))}
                      {member.staffRoles.length === 0 && (
                        <span className="text-xs text-sand-500 dark:text-sand-400">
                          No staff roles
                        </span>
                      )}
                    </div>
                  )}
                </TD>
                <TD>
                  <Badge
                    tone={
                      member.accountStatus === "suspended" ? "danger" : "success"
                    }
                    size="sm"
                  >
                    {member.accountStatus}
                  </Badge>
                </TD>
                <TD>{formatDate(member.joinedAt)}</TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    {!member.isSuperuser && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === member.id}
                        onClick={() => {
                          setAssignTarget(member);
                          setAssignGroup("");
                        }}
                      >
                        Assign role
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
        open={Boolean(assignTarget)}
        onClose={() => setAssignTarget(null)}
        title="Assign staff role"
        description={
          assignTarget
            ? `Grant one group's powers to ${assignTarget.email}. The change is audit-logged and effective immediately.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setAssignTarget(null)}>
              Cancel
            </Button>
            <Button
              type="submit"
              form="assign-role-form"
              disabled={!assignGroup}
              loading={busyId === assignTarget?.id}
            >
              Assign role
            </Button>
          </>
        }
      >
        <form
          id="assign-role-form"
          onSubmit={(event) => {
            event.preventDefault();
            runRoleChange();
          }}
        >
          <Select
            label="Staff role"
            value={assignGroup}
            onChange={(event) => setAssignGroup(event.target.value)}
          >
            <option value="">Choose a role…</option>
            {ASSIGNABLE_GROUPS.filter(
              (group) => !(assignTarget?.staffRoles ?? []).includes(group)
            ).map((group) => (
              <option key={group} value={group}>
                {roleLabel(group)}
              </option>
            ))}
          </Select>
        </form>
      </Modal>

      <Modal
        open={Boolean(removeTarget)}
        onClose={() => setRemoveTarget(null)}
        title="Remove staff role"
        description={
          removeTarget
            ? `${removeTarget.member.email} loses the ${roleLabel(removeTarget.group)} powers immediately — the decision is audit-logged.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setRemoveTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              type="submit"
              form="remove-role-form"
              loading={busyId === removeTarget?.member?.id}
            >
              Remove role
            </Button>
          </>
        }
      >
        <form
          id="remove-role-form"
          onSubmit={(event) => {
            event.preventDefault();
            runRoleChange();
          }}
        >
          <p className="text-sm text-sand-600 dark:text-sand-300">
            Removing the last administrator is refused server-side, and no one
            can change their own roles — the safety guards are enforced by the
            API, not this dialog.
          </p>
        </form>
      </Modal>
    </div>
  );
}
