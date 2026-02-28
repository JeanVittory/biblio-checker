import { createClient } from "@supabase/supabase-js";
import { supabaseEnvSchema } from "@/lib/schemas/env";

export function getSupabaseAdminClient() {
  const env = supabaseEnvSchema.parse(process.env);

  return createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false },
  });
}
