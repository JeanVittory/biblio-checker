import { API_ROUTES, ENDPOINT_ACTION_TYPES, MIME_TYPES } from "@/lib/constants";
import { BibliographyCheckBasePayload } from "@/lib/validation/bibliographyCheck";

export const startAnalysisGatewayService = async (
  request: BibliographyCheckBasePayload
) => {
  const response = await fetch(API_ROUTES.ANALYSIS_START_GATEWAY, {
    method: ENDPOINT_ACTION_TYPES.POST,
    headers: { "content-type": MIME_TYPES.JSON },
    body: JSON.stringify(request),
  });
  return response;
};
