# Step 07 — Export PDF

## Scope

This step specifies the PDF report generation functionality for analysis results. It covers:
- PDF document structure and sections
- Content for each section
- Styling and color conventions
- Generation approach (client-side)

This step does NOT cover:
- The UI button that triggers the download (see Step 08)
- CSV export (see Step 06)
- Server-side PDF generation
- PDF viewer or in-browser preview

## Context

PDF export enables users to download a branded, printable report of their analysis results. This is the primary shareability mechanism: a professor can attach the report to a grade evaluation, a student can show it to their advisor, or a reviewer can archive it. The PDF is generated entirely in the browser from the `ResultsV1` data and the Authenticity Score (Step 02).

## Requirements

### 1) Generation Approach

The PDF MUST be generated client-side in the browser. No server endpoint or backend dependency is introduced for PDF generation.

The PDF generation library MUST:
- Be loaded via dynamic import (not in the initial bundle) to avoid impacting page load time
- Produce a valid PDF that can be opened by standard PDF readers (Adobe, Preview, Chrome)
- Be reviewed for known CVEs (`npm audit`) before adoption, with version pinned exactly in `package.json` (no `^` or `~` range)

**Library preference:** A React-compatible library (e.g., `@react-pdf/renderer`) is PREFERRED because it renders user-controlled strings as text nodes, not HTML, eliminating XSS risk. If the chosen React-based library is incompatible with React 19, `jspdf` + `jspdf-autotable` SHOULD be used as a fallback. In the non-React fallback path, all user-controlled string fields (`rawText`, `decisionReason`, `matchedRecord.title`, `matchedRecord.url`) MUST be treated as plain text only — no library method that interprets input as HTML markup (such as `jsPDF.html()` or `jsPDF.fromHTML()`) may be passed user-controlled data without prior HTML-entity encoding.

**Translated strings in the non-React path:** If the non-React fallback is used, the PDF generator function MUST receive pre-resolved translated strings as arguments (not call `useTranslations()` which requires React context). The caller (Export Buttons component) MUST resolve all i18n keys before invoking the generator.

### 2) Document Structure

The PDF MUST contain the following sections in order:

#### Section 1: Header
- Title: "Biblio Checker" (product name)
- Subtitle: "Bibliographic Reference Analysis Report"
- Date: generation date in the report's locale format
- File name: the original uploaded document name

#### Section 2: Authenticity Score
- Score number (0-100) prominently displayed
- Band label: "High authenticity", "Needs review", or "Low authenticity" (or locale equivalent)
- Score number MUST be colored according to the semaphore (green/amber/red)

#### Section 3: Summary
- Total references detected
- Total references analyzed
- Classification breakdown: count per classification, with classification label

#### Section 4: Reference Details
- One entry per reference, containing:
  - Reference ID
  - Classification label (colored text matching the semaphore convention from the UI)
  - Confidence score (0.0-1.0) and confidence band, if available
  - Raw extracted text (the original reference as found in the document)
  - Decision reason (human-readable explanation)
  - Evidence sources: for each evidence item, the source name and matched record DOI/URL (if available)

#### Section 5: Footer
- Pipeline name and version (from `ResultsV1.pipeline`)
- Schema version (from `ResultsV1.schemaVersion`)
- Disclaimer: "This report was generated automatically. Results should be verified manually for critical decisions."

### 3) Color Conventions

The PDF MUST use the following colors:

| Element | Color | Hex |
|---------|-------|-----|
| Score — high band | Green | #22c55e |
| Score — medium band | Amber | #f59e0b |
| Score — low band | Red | #ef4444 |
| Classification: verified | Green | #22c55e |
| Classification: likely_verified | Blue | #3b82f6 |
| Classification: ambiguous | Amber | #f59e0b |
| Classification: not_found | Red | #ef4444 |
| Classification: suspicious | Red (darker) | #dc2626 |
| Classification: processing_error | Gray | #6b7280 |
| Header/brand accent | Cyan | #00d9ff |

### 4) Typography

- Title: bold, larger font size
- Section headings: bold, medium font size
- Body text: regular weight, readable font size (minimum 10pt equivalent)
- The PDF MUST use a standard font that does not require embedding (e.g., Helvetica)

### 5) Page Layout

- Page size: A4 (210mm × 297mm)
- Margins: sufficient for printing (minimum 15mm all sides)
- If content exceeds one page, it MUST flow to subsequent pages with:
  - Header repeated on each page (product name + file name)
  - Page numbers in the footer ("Page X of Y")

### 6) File Name

The downloaded PDF MUST be named `{originalFileName}-report.pdf`, where `{originalFileName}` is the name of the uploaded document without its extension.

The `{originalFileName}` value MUST be sanitized before use as the `download` attribute: it MUST NOT contain path separators (`/`, `\`), null bytes, or other characters invalid in file names. The existing `sanitizeFileName()` utility (or equivalent) SHOULD be reused for this purpose.

### 7) Locale Awareness

- The date in the header MUST be formatted according to the current locale
- Classification labels and band labels in the PDF MUST use the current language (EN/ES/PT)
- The disclaimer text MUST be in the current language

### 8) Handling of Null Values

| Field | When Null | PDF Representation |
|-------|-----------|-------------------|
| `confidenceScore` | processing_error | Display "N/A" instead of a number |
| `confidenceBand` | processing_error | Display "N/A" |
| `normalized.title` | Parsing failure | Display raw text only |
| `evidence` | Empty array | Display "No evidence found" |
| `matchedRecord.doi` | No DOI | Omit DOI line |
| `matchedRecord.url` | No URL | Omit URL line |

### 9) URL Scheme Validation

URLs from evidence items (`matchedRecord.url`) MUST only be rendered as hyperlinks in the PDF if they begin with `https://` or `http://`. Any URL with a different scheme (e.g., `javascript:`, `data:`, `ftp:`) MUST be rendered as plain text only, not as a clickable link. This prevents malicious URI schemes from being executable in PDF viewers.

### 9) Performance

PDF generation for a document with 30 references MUST complete in under 5 seconds on a modern browser. A loading indicator MUST be shown during generation (specified in Step 08).

## Acceptance Criteria

- PDF contains all 5 sections (header, score, summary, reference details, footer)
- Score is colored according to the correct band (green/amber/red)
- Each reference appears with its classification, confidence, raw text, and decision reason
- Evidence sources include DOIs/URLs when available
- PDF is a valid document openable by Adobe Reader, Chrome, and macOS Preview
- File name follows the `{originalFileName}-report.pdf` pattern
- Multi-page documents have page numbers and repeated header
- The PDF library is loaded via dynamic import (not in initial bundle)
- Generation completes in under 5 seconds for 30 references
- Date is formatted in the current locale
- Classification and band labels are in the current language

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| 0 references | PDF contains header, score (0), summary (0/0), empty reference section, footer |
| All references are processing_error | Score shows 0; confidence fields show "N/A" |
| Very long rawText (2000+ chars) | Text wraps within the page; no truncation |
| 50+ references | PDF flows to multiple pages with page numbers |
| Decision reason contains special characters | Characters render correctly (UTF-8 font) |
| User switches language to PT and exports | PDF labels are in Portuguese |
| PDF generation fails (library error) | Error is caught; user sees error message; no crash |

## Integration Points

- Step 02 (Authenticity Score Formula) — used to compute score for the PDF
- Step 08 (Export Buttons Integration) — triggers PDF generation and download
- Consumes `ResultsV1` type from `spec/results-contract-v1/`
- Uses i18n keys from Step 09 for labels and disclaimer

## Dependencies

- Step 02 (Authenticity Score Formula) — provides score computation
- Step 09 (i18n Catalog) — provides translated labels for PDF content
