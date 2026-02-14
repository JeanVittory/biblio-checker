import "server-only";

import { getSupabaseAdminClient } from "@/lib/supabaseAdmin";

export async function cleanupUploadedFile(bucket: string, path: string) {
  try {
    const supabase = getSupabaseAdminClient();
    await supabase.storage.from(bucket).remove([path]);
  } catch {
    // Best-effort cleanup; intentionally ignore errors.
  }
}
