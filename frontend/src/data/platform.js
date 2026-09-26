/**
 * Public platform info (Phase 13.6) — the marketplace's name and support
 * contact for storefront chrome. Anonymous by design: the public subset of
 * PlatformSettings never carries money or switches (PROJECT_CONTEXT §6
 * v1.13), and every shape is mapped here so components render API truth.
 */
import { request } from "../lib/api";

const PLATFORM = "/api/v1/platform";

export function mapPlatformInfo(info) {
  return {
    platformName: info.platform_name ?? "Jeyvro",
    supportEmail: info.support_email ?? "",
  };
}

export async function fetchPlatformInfo() {
  return mapPlatformInfo(await request(PLATFORM, "/public/"));
}
