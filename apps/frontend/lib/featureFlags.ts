import { unstable_cache } from "next/cache";
import { getSupabaseAdminClient } from "@/lib/supabase/supabaseAdmin";
import logger from "@/lib/logger";

const log = logger.child({ module: "featureFlags" });

export const FEATURE_FLAGS = {
  UPLOAD_ENABLED: "upload_enabled",
} as const;

export type FeatureFlagKey = (typeof FEATURE_FLAGS)[keyof typeof FEATURE_FLAGS];

const FEATURE_FLAGS_CACHE_TAG = "feature-flags";
const FEATURE_FLAGS_CACHE_TTL_SECONDS = 60;

async function readFeatureFlag(key: string): Promise<boolean> {
  try {
    const supabase = getSupabaseAdminClient();
    const { data, error } = await supabase
      .from("feature_flags")
      .select("enabled")
      .eq("flag_key", key)
      .maybeSingle();

    if (error) {
      log.warn({ err: error, key }, "Failed to read feature flag — defaulting to false");
      return false;
    }

    return data?.enabled === true;
  } catch (err) {
    log.warn({ err, key }, "Feature flag lookup threw — defaulting to false");
    return false;
  }
}

export function getFeatureFlag(key: FeatureFlagKey): Promise<boolean> {
  const cached = unstable_cache(
    () => readFeatureFlag(key),
    [`feature-flag:${key}`],
    { revalidate: FEATURE_FLAGS_CACHE_TTL_SECONDS, tags: [FEATURE_FLAGS_CACHE_TAG] }
  );
  return cached();
}
