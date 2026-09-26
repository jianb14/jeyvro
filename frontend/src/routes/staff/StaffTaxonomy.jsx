/**
 * Categories & brands (Phase 13.4) — /staff/taxonomy.
 *
 * Operations/administrator taxonomy management (§4 matrix): the category
 * tree and brand records. Writes run through the audited catalog services —
 * cycles, duplicate brands, and non-empty category deletes are refused
 * server-side and their messages surface here. v1 renders the whole
 * taxonomy (pageSize 100); pagination lands if the tree outgrows it.
 */
import { useCallback, useEffect, useState } from "react";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { Textarea } from "../../components/ui/Textarea";
import { TagIcon } from "../../components/ui/Icons";
import { useAuth } from "../../features/auth/AuthContext";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 100; // taxonomy fits one page (v1)

export function StaffTaxonomy() {
  const { user: viewer } = useAuth();
  const roles = viewer?.staff_roles ?? [];
  const canManage =
    roles.includes("operations") || roles.includes("administrator");

  const [categories, setCategories] = useState(null);
  const [brands, setBrands] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [categoryDraft, setCategoryDraft] = useState(null);
  const [brandDraft, setBrandDraft] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    Promise.all([
      staffApi.fetchAdminCategories({ pageSize: PAGE_SIZE }),
      staffApi.fetchAdminBrands({ pageSize: PAGE_SIZE }),
    ])
      .then(([categoryData, brandData]) => {
        if (!cancelled) {
          setCategories(categoryData.items);
          setBrands(brandData.items);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(load, [load]);

  const parentName = (parentId) =>
    categories?.find((item) => item.id === parentId)?.name ?? "—";

  async function saveCategory() {
    if (!categoryDraft) return;
    setBusy(true);
    setNotice(null);
    try {
      const payload = {
        name: categoryDraft.name.trim(),
        parent: categoryDraft.parentId ? Number(categoryDraft.parentId) : null,
        description: categoryDraft.description.trim(),
        position: Number(categoryDraft.position) || 0,
        is_active: categoryDraft.isActive,
      };
      if (categoryDraft.mode === "create") {
        await staffApi.createCategory(payload);
        setNotice({ tone: "success", message: `“${payload.name}” created.` });
      } else {
        await staffApi.updateCategory(categoryDraft.id, payload);
        setNotice({ tone: "success", message: `“${payload.name}” updated.` });
      }
      setCategoryDraft(null);
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  }

  async function saveBrand() {
    if (!brandDraft) return;
    setBusy(true);
    setNotice(null);
    try {
      const payload = { name: brandDraft.name.trim() };
      if (brandDraft.mode === "create") {
        await staffApi.createBrand(payload);
        setNotice({ tone: "success", message: `“${payload.name}” created.` });
      } else {
        await staffApi.updateBrand(brandDraft.id, payload);
        setNotice({ tone: "success", message: `“${payload.name}” updated.` });
      }
      setBrandDraft(null);
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  }

  async function runDelete() {
    if (!deleteTarget) return;
    const { kind, item } = deleteTarget;
    setBusy(true);
    setNotice(null);
    try {
      if (kind === "category") await staffApi.deleteCategory(item.id);
      else await staffApi.deleteBrand(item.id);
      setNotice({ tone: "success", message: `“${item.name}” deleted.` });
      setDeleteTarget(null);
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  }

  const loading = categories === null || brands === null;

  return (
    <div>
      <div>
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Categories & brands
        </h1>
        <p className="mt-1 text-sm text-sand-600 dark:text-sand-400">
          The marketplace taxonomy — categories power browse navigation and
          brands label products. Every change is audit-logged; categories
          with products or subcategories cannot be deleted.
        </p>
      </div>

      {notice && (
        <div className="mt-4">
          <Alert tone={notice.tone}>{notice.message}</Alert>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <Alert tone="danger" title="Could not load the taxonomy">
            {error}
          </Alert>
        </div>
      )}

      {loading && !error && (
        <div className="mt-6 space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      )}

      {!loading && (
        <>
          <section className="mt-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
                Categories
              </h2>
              {canManage && (
                <Button
                  size="sm"
                  onClick={() =>
                    setCategoryDraft({
                      mode: "create",
                      id: null,
                      name: "",
                      parentId: "",
                      description: "",
                      position: 0,
                      isActive: true,
                    })
                  }
                >
                  New category
                </Button>
              )}
            </div>

            {categories.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  compact
                  icon={TagIcon}
                  title="No categories yet"
                  description="Categories power customer navigation — create the first one."
                />
              </div>
            ) : (
              <div className="mt-4">
                <Table>
                  <THead>
                    <TR>
                      <TH>Name</TH>
                      <TH>Parent</TH>
                      <TH>Slug</TH>
                      <TH>Products</TH>
                      <TH>Active</TH>
                      <TH className="text-right">Actions</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {categories.map((category) => (
                      <TR key={category.id}>
                        <TD>
                          <p className="font-medium text-sand-900 dark:text-sand-100">
                            {category.name}
                          </p>
                          {category.description && (
                            <p className="mt-0.5 max-w-64 text-xs text-sand-500 dark:text-sand-400">
                              {category.description}
                            </p>
                          )}
                        </TD>
                        <TD>{parentName(category.parentId)}</TD>
                        <TD className="text-xs">{category.slug}</TD>
                        <TD className="tabular-nums">{category.productCount}</TD>
                        <TD>
                          <Badge
                            tone={category.isActive ? "success" : "neutral"}
                            size="sm"
                          >
                            {category.isActive ? "Active" : "Hidden"}
                          </Badge>
                        </TD>
                        <TD>
                          <div className="flex justify-end gap-2">
                            {canManage && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    setCategoryDraft({
                                      mode: "edit",
                                      id: category.id,
                                      name: category.name,
                                      parentId: category.parentId ?? "",
                                      description: category.description,
                                      position: category.position,
                                      isActive: category.isActive,
                                    })
                                  }
                                >
                                  Edit
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    setDeleteTarget({
                                      kind: "category",
                                      item: category,
                                    })
                                  }
                                >
                                  Delete
                                </Button>
                              </>
                            )}
                          </div>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </section>

          <section className="mt-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
                Brands
              </h2>
              {canManage && (
                <Button
                  size="sm"
                  onClick={() =>
                    setBrandDraft({ mode: "create", id: null, name: "" })
                  }
                >
                  New brand
                </Button>
              )}
            </div>

            {brands.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  compact
                  icon={TagIcon}
                  title="No brands yet"
                  description="Brands label products across stores — add the first one."
                />
              </div>
            ) : (
              <div className="mt-4">
                <Table>
                  <THead>
                    <TR>
                      <TH>Name</TH>
                      <TH>Slug</TH>
                      <TH>Products</TH>
                      <TH className="text-right">Actions</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {brands.map((brand) => (
                      <TR key={brand.id}>
                        <TD>
                          <p className="font-medium text-sand-900 dark:text-sand-100">
                            {brand.name}
                          </p>
                        </TD>
                        <TD className="text-xs">{brand.slug}</TD>
                        <TD className="tabular-nums">{brand.productCount}</TD>
                        <TD>
                          <div className="flex justify-end gap-2">
                            {canManage && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    setBrandDraft({
                                      mode: "edit",
                                      id: brand.id,
                                      name: brand.name,
                                    })
                                  }
                                >
                                  Edit
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    setDeleteTarget({ kind: "brand", item: brand })
                                  }
                                >
                                  Delete
                                </Button>
                              </>
                            )}
                          </div>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </section>
        </>
      )}

      <Modal
        open={Boolean(categoryDraft)}
        onClose={() => setCategoryDraft(null)}
        title={categoryDraft?.mode === "create" ? "New category" : "Edit category"}
        description="Slugs are generated from the name and stay stable once created. A category cannot be moved under its own descendant — the server refuses it."
        footer={
          <>
            <Button variant="ghost" onClick={() => setCategoryDraft(null)}>
              Cancel
            </Button>
            <Button
              type="submit"
              form="category-form"
              loading={busy}
              disabled={!categoryDraft?.name.trim()}
            >
              {categoryDraft?.mode === "create" ? "Create category" : "Save changes"}
            </Button>
          </>
        }
      >
        {categoryDraft && (
          <form
            id="category-form"
            onSubmit={(event) => {
              event.preventDefault();
              saveCategory();
            }}
          >
            <div className="space-y-4">
              <Input
                label="Name"
                value={categoryDraft.name}
                maxLength={96}
                onChange={(event) =>
                  setCategoryDraft({ ...categoryDraft, name: event.target.value })
                }
              />
              <Select
                label="Parent"
                value={
                  categoryDraft.parentId === ""
                    ? ""
                    : String(categoryDraft.parentId)
                }
                onChange={(event) =>
                  setCategoryDraft({
                    ...categoryDraft,
                    parentId: event.target.value,
                  })
                }
              >
                <option value="">None (top level)</option>
                {categories
                  .filter((item) => item.id !== categoryDraft.id)
                  .map((item) => (
                    <option key={item.id} value={String(item.id)}>
                      {item.name}
                    </option>
                  ))}
              </Select>
              <Textarea
                label="Description (optional)"
                rows={2}
                maxLength={500}
                value={categoryDraft.description}
                onChange={(event) =>
                  setCategoryDraft({
                    ...categoryDraft,
                    description: event.target.value,
                  })
                }
              />
              <Input
                label="Position"
                type="number"
                min={0}
                value={categoryDraft.position}
                onChange={(event) =>
                  setCategoryDraft({
                    ...categoryDraft,
                    position: event.target.value,
                  })
                }
                hint="Lower numbers show first in navigation."
              />
              <Switch
                checked={categoryDraft.isActive}
                onChange={(value) =>
                  setCategoryDraft({ ...categoryDraft, isActive: value })
                }
                label="Active"
                description="Hidden categories stay out of the storefront navigation."
              />
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={Boolean(brandDraft)}
        onClose={() => setBrandDraft(null)}
        title={brandDraft?.mode === "create" ? "New brand" : "Edit brand"}
        description="Brand names are unique and the slug is generated automatically."
        footer={
          <>
            <Button variant="ghost" onClick={() => setBrandDraft(null)}>
              Cancel
            </Button>
            <Button
              type="submit"
              form="brand-form"
              loading={busy}
              disabled={!brandDraft?.name.trim()}
            >
              {brandDraft?.mode === "create" ? "Create brand" : "Save changes"}
            </Button>
          </>
        }
      >
        {brandDraft && (
          <form
            id="brand-form"
            onSubmit={(event) => {
              event.preventDefault();
              saveBrand();
            }}
          >
            <Input
              label="Name"
              value={brandDraft.name}
              maxLength={96}
              onChange={(event) =>
                setBrandDraft({ ...brandDraft, name: event.target.value })
              }
            />
          </form>
        )}
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title={
          deleteTarget?.kind === "category" ? "Delete category" : "Delete brand"
        }
        description={
          deleteTarget
            ? deleteTarget.kind === "category"
              ? `“${deleteTarget.item.name}” is removed permanently. Categories with products or subcategories are refused server-side.`
              : `“${deleteTarget.item.name}” is removed; products carrying it keep working without the label.`
            : ""
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              type="submit"
              form="taxonomy-delete-form"
              loading={busy}
            >
              Delete
            </Button>
          </>
        }
      >
        <form
          id="taxonomy-delete-form"
          onSubmit={(event) => {
            event.preventDefault();
            runDelete();
          }}
        >
          <p className="text-sm text-sand-600 dark:text-sand-400">
            This action is audit-logged — the audit viewer keeps the record.
          </p>
        </form>
      </Modal>
    </div>
  );
}