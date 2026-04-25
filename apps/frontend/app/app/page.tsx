import { FEATURE_FLAGS, getFeatureFlag } from "@/lib/featureFlags";
import { AppClient } from "./AppClient";

export default async function Page() {
  const uploadEnabled = await getFeatureFlag(FEATURE_FLAGS.UPLOAD_ENABLED);
  return <AppClient uploadEnabled={uploadEnabled} />;
}
