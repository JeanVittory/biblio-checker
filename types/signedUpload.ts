export interface SignedUploadInitRequest {
  fileName: string;
  contentType: string;
}

export interface SignedUploadInitResponse {
  success: boolean;
  message: string;
  bucket?: string;
  requestId?: string;
  filePath?: string;
  signedUrl?: string;
  clientExpiresInSeconds?: number;
  clientExpiresAt?: string;
}

