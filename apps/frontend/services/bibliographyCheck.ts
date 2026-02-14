import { API_ENDPOINTS, ENDPOINT_ACTION_TYPES, MIME_TYPES } from "@/lib/constants";
import { BibliographyCheckRequestPayload } from "@/lib/validation/bibliographyCheck";

export const bibliographyCheckService = async (request: BibliographyCheckRequestPayload) => {
  const checkResponse = await fetch(API_ENDPOINTS.BIBLIOGRAPHY_CHECK, {
    method: ENDPOINT_ACTION_TYPES.POST,
    headers: { "content-type": MIME_TYPES.JSON },
    body: JSON.stringify(request),
  });
  return checkResponse;
};
