import { SAMPLE_DOCUMENT_PATH } from "@/lib/constants";

/**
 * First 5 bytes of a valid PDF file (the PDF magic number).
 * Used to validate the fetched file content before handing it to the upload flow.
 */
const PDF_MAGIC = "%PDF-";

/**
 * Fetches the sample reference PDF from the public directory, validates its
 * Content-Type header and PDF magic bytes, and returns a File object ready
 * for the upload flow.
 *
 * Security: the fetch target is the hardcoded SAMPLE_DOCUMENT_PATH constant
 * and MUST NOT be derived from any user input or query parameter.
 *
 * @throws {Error} if the fetch fails, the Content-Type is not application/pdf,
 *                 or the file does not start with the PDF magic bytes.
 */
export async function fetchSampleDocument(): Promise<File> {
  const response = await fetch(SAMPLE_DOCUMENT_PATH);

  if (!response.ok) {
    throw new Error(`Fetch failed with status ${response.status}`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/pdf")) {
    throw new Error(`Unexpected content-type: ${contentType}`);
  }

  const blob = await response.blob();
  const arrayBuffer = await blob.slice(0, 5).arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);
  const magic = String.fromCharCode(...bytes);

  if (magic !== PDF_MAGIC) {
    throw new Error("File does not start with PDF magic bytes.");
  }

  return new File([blob], "sample-references.pdf", {
    type: "application/pdf",
  });
}
