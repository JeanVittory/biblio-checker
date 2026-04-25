# Step 06 — Export CSV

## Scope

This step specifies the CSV generation and download functionality for analysis results. It covers:
- CSV column specification
- Data formatting and escaping rules
- Download mechanism
- Testability requirements

This step does NOT cover:
- The UI button that triggers the download (see Step 08)
- PDF export (see Step 07)
- Server-side export or API endpoints
- Batch export of multiple jobs

## Context

CSV export enables users to download analysis results in a tabular format suitable for spreadsheets (Excel, Google Sheets, LibreOffice Calc). This is valuable for professors who want to archive results, perform additional analysis, or integrate with grading systems. The CSV is generated entirely in the browser from the `ResultsV1` data already present in the client.

## Requirements

### 1) Column Specification

The CSV MUST contain one header row followed by one data row per reference. The columns MUST be, in order:

| # | Column Header | Source Field | Description |
|---|---------------|-------------|-------------|
| 1 | `referenceId` | `reference.referenceId` | Unique reference identifier |
| 2 | `rawText` | `reference.rawText` | Original extracted text |
| 3 | `title` | `reference.normalized.title` | Normalized title (may be null) |
| 4 | `authors` | `reference.normalized.authors` | Authors joined by "; " (may be empty array) |
| 5 | `year` | `reference.normalized.year` | Publication year (may be null) |
| 6 | `classification` | `reference.classification` | Classification enum value |
| 7 | `confidenceScore` | `reference.confidenceScore` | Score 0.0-1.0 (empty string if null) |
| 8 | `confidenceBand` | `reference.confidenceBand` | Band enum value (empty string if null) |
| 9 | `reasonCode` | `reference.reasonCode` | Reason code enum value |
| 10 | `decisionReason` | `reference.decisionReason` | Human-readable explanation |
| 11 | `evidenceSources` | `reference.evidence[].source` | Sources joined by "; " (e.g., "openalex; arxiv") |
| 12 | `bestMatchDoi` | First evidence item's `matchedRecord.doi` | DOI of best match (empty string if none) |
| 13 | `bestMatchUrl` | First evidence item's `matchedRecord.url` | URL of best match (empty string if none) |

### 2) Escaping Rules (RFC 4180 + Formula Injection Defense)

The CSV MUST comply with RFC 4180:
- Fields containing commas, double quotes, or newlines MUST be enclosed in double quotes
- Double quotes within a field MUST be escaped by doubling them (`""`)
- The line separator MUST be CRLF (`\r\n`)
- The header row MUST use the exact column names specified above

Additionally, to prevent spreadsheet formula injection (CWE-1236):
- Any string field value whose first character is one of `=`, `+`, `-`, or `@` MUST be prefixed with a tab character (`\t`) before RFC 4180 quoting is applied
- This rule applies to all string columns: `rawText`, `title`, `authors`, `decisionReason`, and `evidenceSources`
- This prevents Excel/LibreOffice from evaluating cell content as formulas when users open the CSV

### 3) Encoding

The CSV MUST be encoded in UTF-8 with a BOM prefix (`\uFEFF`). The BOM ensures that Excel opens the file with correct encoding (without BOM, Excel defaults to ANSI on Windows and corrupts accented characters).

### 4) Null and Empty Handling

| Situation | Representation in CSV |
|-----------|----------------------|
| `null` field | Empty string (no content between commas) |
| Empty array (e.g., `authors = []`) | Empty string |
| Empty string field | Empty string |
| `confidenceScore` is null (processing_error) | Empty string |
| `evidence` is empty array | Empty string for both `evidenceSources` and `bestMatchDoi`/`bestMatchUrl` |

### 5) File Name

The downloaded file MUST be named `{originalFileName}-report.csv`, where `{originalFileName}` is the name of the uploaded document without its extension.

Example: if the uploaded file is `thesis_final.pdf`, the CSV is named `thesis_final-report.csv`.

The `{originalFileName}` value MUST be sanitized before use as the `download` attribute: it MUST NOT contain path separators (`/`, `\`), null bytes, or other characters invalid in file names. The existing `sanitizeFileName()` utility (or equivalent) SHOULD be reused for this purpose.

### 6) Download Mechanism

The download MUST be triggered client-side:
1. Build the CSV string in memory
2. Create a `Blob` with MIME type `text/csv;charset=utf-8`
3. Create a temporary anchor element with `href` set to `URL.createObjectURL(blob)`
4. Set the `download` attribute to the file name
5. Programmatically click the anchor
6. Revoke the object URL after download starts

No server roundtrip is involved.

### 7) Separation of Concerns

The implementation MUST separate the CSV string construction from the download trigger:
- A pure function that takes `ResultsV1` and returns a CSV string (testable, no DOM dependency)
- A download function that takes the CSV string and file name and triggers the browser download

This separation ensures the CSV generation logic is unit-testable.

### 8) Empty References

If `ResultsV1.references` is an empty array, the CSV MUST contain only the header row (no data rows). The file MUST still download successfully.

## Acceptance Criteria

- CSV contains the correct 13 columns in the specified order
- Header row matches the exact column names specified
- Each reference produces exactly one data row
- Fields with commas are properly quoted
- Fields with double quotes are properly escaped (`""`)
- Fields with newlines are properly quoted
- Null fields produce empty values (not the string "null")
- The file opens correctly in Excel (Windows) without encoding issues
- The file opens correctly in Google Sheets
- The file name follows the `{originalFileName}-report.csv` pattern
- An empty references array produces a header-only CSV that downloads successfully
- The CSV generation function is testable with unit tests (no DOM required)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `rawText` contains commas, quotes, and newlines | Field is quoted and inner quotes are doubled |
| `decisionReason` contains Unicode characters (Spanish accents) | UTF-8 encoding with BOM preserves characters |
| `authors` array has 20 entries | All joined by "; " in a single field |
| `evidence` is empty | `evidenceSources`, `bestMatchDoi`, `bestMatchUrl` are empty strings |
| 0 references | Header-only CSV downloads |
| Very long `rawText` (2000+ characters) | Full text included; no truncation |
| `originalFileName` contains special characters | File name preserves characters (browser handles this) |

## Integration Points

- Step 08 (Export Buttons Integration) calls the download function when user clicks CSV button
- Consumes `ResultsV1` type from `spec/results-contract-v1/`

## Dependencies

- None (standalone utility)
- Consumes `ResultsV1` shape from `spec/results-contract-v1/`
