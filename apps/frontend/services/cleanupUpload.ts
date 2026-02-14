import { API_ENDPOINTS, ENDPOINT_ACTION_TYPES, MIME_TYPES } from "@/lib/constants";

export const cleanupUploadService = async (bucket: string, path: string) => {
  return fetch(API_ENDPOINTS.CLEANUP_UPLOAD, {
    method: ENDPOINT_ACTION_TYPES.POST,
    headers: { "content-type": MIME_TYPES.JSON },
    body: JSON.stringify({ bucket, path }),
  });
};

