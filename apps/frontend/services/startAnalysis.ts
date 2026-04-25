import { BACKEND_ROUTES, ENDPOINT_ACTION_TYPES, MIME_TYPES } from "@/lib/constants";
import { BibliographyCheckFullPayload } from "@/lib/schemas/bibliographyCheck";

export const startAnalysisService = async (
  backendUrl: string,
  request: BibliographyCheckFullPayload & { locale?: string },
  acceptLanguage?: string
) => {
  const headers: Record<string, string> = { "content-type": MIME_TYPES.JSON };
  if (acceptLanguage) {
    headers["accept-language"] = acceptLanguage;
  }
  const checkResponse = await fetch(`${backendUrl}${BACKEND_ROUTES.ANALYSIS_START}`, {
    method: ENDPOINT_ACTION_TYPES.POST,
    headers,
    body: JSON.stringify(request),
  });
  return checkResponse;
};
