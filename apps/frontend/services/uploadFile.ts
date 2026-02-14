import { ENDPOINT_ACTION_TYPES } from "@/lib/constants";
import { SignedUploadInitResponse } from "@/types/signedUpload";

export const uploadFileService = async (file: File, initData: SignedUploadInitResponse) => {
  if (!initData.signedUrl) return;
  const uploadResponse = await fetch(initData.signedUrl, {
    method: ENDPOINT_ACTION_TYPES.PUT,
    headers: { "x-upsert": "false", "content-type": file.type },
    body: file,
  });
  return uploadResponse;
};
