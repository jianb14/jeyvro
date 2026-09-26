/**
 * Store settings (Phase 12.7) — /seller/settings.
 *
 * Reuses the Phase 4 StoreSettingsPanel (profile / policies / shipping) —
 * one implementation for both surfaces. Store status is read-only API
 * truth: transitions are staff-only and audit-logged (marketplace-sellers
 * rule 3), which the copy states plainly.
 */
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { StoreSettingsPanel } from "../../features/seller/StoreSettingsPanel";

export function SellerStoreSettings() {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Store settings
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Profile, policies, and shipping — saved values go live on your
          storefront immediately.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Profile &amp; policies</CardTitle>
          <CardDescription>
            Return and shipping policies are shown on every product page from
            your store.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <StoreSettingsPanel />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Store status</CardTitle>
          <CardDescription>
            Pending stores stay hidden from shoppers until staff approve them;
            suspended stores keep their data but disappear from the storefront.
            Status changes are staff actions and are audit-logged — sellers
            never self-approve.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
