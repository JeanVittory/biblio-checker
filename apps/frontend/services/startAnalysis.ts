import { BACKEND_ROUTES, ENDPOINT_ACTION_TYPES, MIME_TYPES } from "@/lib/constants";
import { BibliographyCheckFullPayload } from "@/lib/validation/bibliographyCheck";

export const startAnalysisService = async (
  backendUrl: string,
  request: BibliographyCheckFullPayload
) => {
  const checkResponse = await fetch(`${backendUrl}${BACKEND_ROUTES.ANALYSIS_START}`, {
    method: ENDPOINT_ACTION_TYPES.POST,
    headers: { "content-type": MIME_TYPES.JSON },
    body: JSON.stringify(request),
  });
  return checkResponse;
};
