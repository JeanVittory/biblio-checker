import { API_ENDPOINTS, ENDPOINT_ACTION_TYPES, MIME_TYPES } from "@/lib/constants";
import { SignedUploadInitResponse } from "@/types/signedUpload";

export const signedUploadService = async (file: File) => {
  const initResponse = await fetch(API_ENDPOINTS.SIGNED_UPLOAD, {
    method: ENDPOINT_ACTION_TYPES.POST,
    headers: { "content-type": MIME_TYPES.JSON },
    body: JSON.stringify({ fileName: file.name, contentType: file.type }),
  });
  return (await initResponse.json()) as SignedUploadInitResponse;
};
