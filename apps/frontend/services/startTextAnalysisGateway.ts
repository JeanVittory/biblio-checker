import { MIME_TYPES } from "@/lib/constants";
import type { TextReferenceCheckPayload } from "@/lib/schemas/bibliographyCheck";

/**
 * Client-side thin wrapper that POSTs a text-reference payload to the
 * Next.js gateway route.  Returns the raw Response so the caller can
 * parse JSON and inspect `ok` as it sees fit.
 *
 * Mirrors startAnalysisGatewayService — same return contract.
 *
 * Spec: spec/single-reference-text-check/06-input-component/spec.md § 8
 */
export async function startTextAnalysisGatewayService(
  payload: TextReferenceCheckPayload
): Promise<Response> {
  return fetch("/api/analysis-text-gateway", {
    method: "POST",
    headers: { "Content-Type": MIME_TYPES.JSON },
    body: JSON.stringify(payload),
  });
}
