/**
 * Audit log viewer (Phase 13.7) — /staff/audit.
 *
 * The safety net for every other staff surface: who did what, to which
 * object, when (marketplace-admin best practice). Read-only by design —
 * the API is group-gated (administrator / operations / moderator) and rows
 * are append-only, so nothing on this page can rewrite history.
 */
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { ShieldCheckIcon } from "../../components/ui/Icons";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 20;

const ACTION_TONES = [
  ["approved", "success"],
  ["activated", "success"],
  ["rejected", "danger"],
  ["suspended", "warning"],
  ["failed", "danger"],
];

function actionTone(action) {
  const match = ACTION_TONES.find(([needle]) => action.includes(needle));
  return match ? match[1] : "neutral";
}

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString("en-PH", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";
}

export function StaffAuditLog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [actor, setActor] = useState(searchParams.get("actor") || "");
  const [action, setAction] = useState(searchParams.get("action") || "");
  const [objectType, setObjectType] = useState(searchParams.get("object_type") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const actorParam = searchParams.get("actor") || "";
  const actionParam = searchParams.get("action") || "";
  const objectTypeParam = searchParams.get("object_type") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchAuditEvents({
        actor: actorParam,
        action: actionParam,
        objectType: objectTypeParam,
        page,
        pageSize: PAGE_SIZE,
      })
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
  }, [actorParam, actionParam, objectTypeParam, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  const filtersActive = Boolean(actorParam || actionParam || objectTypeParam);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Audit log
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Every sensitive action — approvals, suspensions, moderation, refunds,
          settings, and role changes — with its actor, target, and timestamp.
        </p>
      </header>

      {error && <Alert tone="danger" title="Could not load the audit log">{error}</Alert>}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          const next = new URLSearchParams();
          if (actor.trim()) next.set("actor", actor.trim());
          if (action.trim()) next.set("action", action.trim());
          if (objectType.trim()) next.set("object_type", objectType.trim());
          setSearchParams(next);
        }}
      >
        <div className="min-w-48 flex-1">
          <Input
            label="Actor email"
            placeholder="admin@example.com"
            value={actor}
            onChange={(event) => setActor(event.target.value)}
          />
        </div>
        <div className="min-w-48 flex-1">
          <Input
            label="Action"
            placeholder="seller_application_approved"
            value={action}
            onChange={(event) => setAction(event.target.value)}
          />
        </div>
        <div className="min-w-44 flex-1">
          <Input
            label="Object type"
            placeholder="stores.sellerapplication"
            value={objectType}
            onChange={(event) => setObjectType(event.target.value)}
          />
        </div>
        <Button type="submit" variant="outline">
          Filter
        </Button>
        {filtersActive && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setActor("");
              setAction("");
              setObjectType("");
              setSearchParams(new URLSearchParams());
            }}
          >
            Clear
          </Button>
        )}
      </form>

      {!data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={ShieldCheckIcon}
          title={filtersActive ? "No events match" : "No events recorded yet"}
          description={
            filtersActive
              ? "Try a different actor, action, or object type."
              : "Staff actions write an audit row the moment they happen."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>When</TH>
              <TH>Actor</TH>
              <TH>Action</TH>
              <TH>Target</TH>
              <TH>Detail</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((event) => (
              <TR key={event.id}>
                <TD className="whitespace-nowrap text-sm">
                  {formatDate(event.createdAt)}
                </TD>
                <TD className="text-sm">{event.actorEmail}</TD>
                <TD>
                  <Badge tone={actionTone(event.action)} variant="soft">
                    {event.action}
                  </Badge>
                </TD>
                <TD>
                  <span className="font-mono text-xs text-sand-700 dark:text-sand-300">
                    {event.objectType}
                  </span>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    #{event.objectId}
                  </p>
                </TD>
                <TD>
                  <pre className="max-w-72 whitespace-pre-wrap break-words font-mono text-xs text-sand-500 dark:text-sand-400">
                    {Object.keys(event.detail).length > 0
                      ? JSON.stringify(event.detail)
                      : "—"}
                  </pre>
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
    </div>
  );
}

