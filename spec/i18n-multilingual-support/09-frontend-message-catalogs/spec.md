# Step 09 — Frontend Message Catalogs (ES / PT / EN)

## Scope

- Create `apps/frontend/messages/{es,pt,en}.json` with a namespaced, exhaustive catalog of every hardcoded string currently rendered by the frontend, covering UI chrome, result enums, and error messages.
- Ensure all three catalogs have identical key shapes (same nested namespaces, same placeholder tokens).
- Use this as the reference for Step 10's component migration.

**Out of scope:** Using the catalogs in components (Step 10). The worker-side catalog (Steps 06–07).

## Context

The goal is a complete, stable key tree that component authors can rely on. A *missing* key in the catalog during Step 10 is harder to spot than one that is present but subtly misnamed, so this step should be done thoroughly before any component code is changed.

Enumerate hardcoded strings by grepping (examples of current state):

- `apps/frontend/app/page.tsx` — `"Biblio Checker"`, `"Upload Your Bibliography"`, `"Upload a PDF or DOCX file."`, footer copy.
- `apps/frontend/components/file-dropzone.tsx` — `"Drop your file here"`, `"PDF or DOCX, up to 10 MB"`, `"Remove"`, validation error messages at lines 28, 30.
- `apps/frontend/components/upload-status.tsx` — `"Uploading {fileName}..."`, `"File uploaded successfully."`.
- `apps/frontend/components/recent-analyses/RecentAnalyses.tsx` — `"Recent Analyses"`, `"File"`, `"Submitted"`, `"Actions"`.
- `apps/frontend/components/recent-analyses/StatusBadge.tsx` — `"Queued"`, `"Running"`, `"Succeeded"`, `"Failed"`, `"Expired"`.
- `apps/frontend/components/recent-analyses/ExpandedDetail.tsx` — `"Verificada"`, `"Prob. verificada"`, `"Ambigua"`, `"No encontrada"`, `"Sospechosa"`, `"Error"`, `"Texto original"`, `"Campos normalizados"`, `"Autores"`, `"Anio"`, `"Revista/Editorial"`, `"Editorial"`, `"DOI"`, `"arXiv ID"`, `"ISSN"`, `"Volumen"`, `"Numero"`, `"Paginas"`, `"Razon de la decision"`, `"Candidatos encontrados"`, `"Referencia"`, `"Candidato"`, `"No se encontraron candidatos en ninguna fuente."`, `"Waiting to be processed..."`, `"Stage: "`, `"Analysis Result"`, `"References detected"`, `"References analyzed"`, `"Reference Details"`.
- `apps/frontend/components/recent-analyses/StorageErrorBanner.tsx` — `"Storage full..."`, `"Unable to load job history..."`.
- `apps/frontend/lib/constants.ts` — `ERROR_MESSAGES`, `UPLOAD_MESSAGES`.
- `apps/frontend/components/recent-analyses/JobRow.tsx` — tooltips, action labels.

Re-scan during implementation and add any string not listed — this spec provides the namespace tree, but the *final* catalog is populated by grep.

## Requirements

### 1. Directory Structure

```
apps/frontend/messages/
  en.json
  es.json
  pt.json
```

English is the "spec language" for key naming — write `en.json` first, then translate to `es.json` and `pt.json`. Keep all three files in sync key-for-key.

### 2. Canonical Namespace Tree

This is the required shape for all three files. Every language file must declare every key. Missing keys trigger the fallback chain (Step 08 Section 5) but break the TypeScript type. Keep them in sync.

```jsonc
{
  "common": {
    "app_name": "Biblio Checker",
    "submit": "Submit",
    "cancel": "Cancel",
    "remove": "Remove",
    "retry": "Retry",
    "close": "Close",
    "copy": "Copy",
    "loading": "Loading…",
    "language_label": "Language",
    "theme_label": "Theme"
  },

  "home": {
    "hero_title": "Upload Your Bibliography",
    "hero_subtitle": "Upload a PDF or DOCX file.",
    "footer_tagline": "Biblio Checker — Academic reference validation"
  },

  "upload": {
    "uploading": "Uploading {fileName}…",
    "upload_success": "File uploaded successfully.",
    "upload_another": "Upload another file"
  },

  "dropzone": {
    "prompt_primary": "Drop your file here",
    "prompt_secondary": "PDF or DOCX, up to 10 MB",
    "validation_file_too_large": "File exceeds the maximum size of 10 MB.",
    "validation_unsupported_format": "Only PDF and DOCX files are allowed."
  },

  "recent": {
    "title": "Recent Analyses",
    "empty_state": "No analyses yet. Upload a file to get started.",
    "columns": {
      "file": "File",
      "submitted": "Submitted",
      "status": "Status",
      "actions": "Actions"
    },
    "actions": {
      "view_details": "View details",
      "hide_details": "Hide details",
      "remove_job": "Remove job"
    }
  },

  "status": {
    "queued": "Queued",
    "running": "Running",
    "succeeded": "Succeeded",
    "failed": "Failed",
    "expired": "Expired",
    "waiting": "Waiting to be processed…",
    "stage_label": "Stage: {stage}"
  },

  "results": {
    "section": {
      "analysis_result": "Analysis Result",
      "reference_details": "Reference Details",
      "raw_text": "Original text",
      "normalized_fields": "Normalized fields",
      "decision_reason": "Decision reason",
      "candidates_found": "Candidates found ({count})",
      "reference": "Reference",
      "candidate": "Candidate"
    },
    "summary": {
      "detected": "References detected",
      "analyzed": "References analyzed"
    },
    "fields": {
      "authors": "Authors",
      "year": "Year",
      "venue": "Journal/Publisher",
      "publisher": "Publisher",
      "doi": "DOI",
      "arxiv_id": "arXiv ID",
      "issn": "ISSN",
      "volume": "Volume",
      "issue": "Issue",
      "pages": "Pages"
    },
    "classification": {
      "verified": "Verified",
      "likely_verified": "Likely verified",
      "ambiguous": "Ambiguous",
      "not_found": "Not found",
      "suspicious": "Suspicious",
      "processing_error": "Error"
    },
    "confidence_band": {
      "very_high": "Very high",
      "high": "High",
      "medium": "Medium",
      "low": "Low",
      "very_low": "Very low"
    },
    "reason_code": {
      "exact_doi_match": "Exact DOI match",
      "strong_metadata_match": "Strong metadata match",
      "weak_metadata_match": "Weak metadata match",
      "cross_source_conflict": "Cross-source conflict",
      "doi_conflict": "DOI conflict",
      "ambiguous_multi_candidate": "Multiple plausible candidates",
      "no_match_any_source": "No match in any source",
      "suspicious_patterns": "Suspicious patterns detected",
      "processing_error": "Processing error"
    },
    "match_type": {
      "doi_exact": "DOI (exact)",
      "title_fuzzy": "Title (fuzzy)",
      "identifier_exact": "Identifier (exact)",
      "issn_filter": "ISSN filter",
      "author_title": "Title + author"
    },
    "no_candidates": "No candidates found in any source."
  },

  "errors": {
    "storage_full": "Storage full. Please remove old jobs to continue.",
    "storage_corrupted": "Unable to load job history. Data may be corrupted.",
    "upload_failed": "Upload failed. Please try again.",
    "analysis_start_failed": "Could not start analysis. Please try again.",
    "status_fetch_failed": "Could not refresh job status.",
    "network_error": "Network error. Check your connection and retry.",
    "invalid_results_format": "Results format is invalid or unsupported."
  }
}
```

(Add any string you encountered during the grep that does not fit a namespace above — do not inline it in a component.)

### 3. Spanish Catalog

Copy the structure verbatim and replace values with the current Spanish copy where it already exists in the codebase (e.g. `"Verificada"`, `"Texto original"`, `"Razon de la decision"` → fix to proper `"Razón de la decisión"` with accent).

**Accent-correction opportunity:** current strings like `"Anio"`, `"Razon de la decision"`, `"Numero"`, `"Paginas"`, `"Volumen"` should gain their correct diacritics (`"Año"`, `"Razón de la decisión"`, `"Número"`, `"Páginas"`). The catalog is the right place to get this right once.

Example `es.json` excerpts:

```jsonc
{
  "common": {
    "app_name": "Biblio Checker",
    "submit": "Enviar",
    "cancel": "Cancelar",
    "remove": "Eliminar",
    "retry": "Reintentar",
    "close": "Cerrar",
    "copy": "Copiar",
    "loading": "Cargando…",
    "language_label": "Idioma",
    "theme_label": "Tema"
  },
  "home": {
    "hero_title": "Sube tu bibliografía",
    "hero_subtitle": "Carga un archivo PDF o DOCX.",
    "footer_tagline": "Biblio Checker — Validación de referencias académicas"
  },
  "dropzone": {
    "prompt_primary": "Suelta tu archivo aquí",
    "prompt_secondary": "PDF o DOCX, hasta 10 MB",
    "validation_file_too_large": "El archivo excede el tamaño máximo de 10 MB.",
    "validation_unsupported_format": "Solo se aceptan archivos PDF y DOCX."
  },
  "status": {
    "queued": "En cola",
    "running": "En ejecución",
    "succeeded": "Completado",
    "failed": "Fallido",
    "expired": "Expirado",
    "waiting": "Esperando para ser procesado…",
    "stage_label": "Etapa: {stage}"
  },
  "results": {
    "classification": {
      "verified": "Verificada",
      "likely_verified": "Prob. verificada",
      "ambiguous": "Ambigua",
      "not_found": "No encontrada",
      "suspicious": "Sospechosa",
      "processing_error": "Error"
    },
    "fields": {
      "authors": "Autores",
      "year": "Año",
      "venue": "Revista/Editorial",
      "publisher": "Editorial",
      "issn": "ISSN",
      "volume": "Volumen",
      "issue": "Número",
      "pages": "Páginas"
    },
    "section": {
      "raw_text": "Texto original",
      "normalized_fields": "Campos normalizados",
      "decision_reason": "Razón de la decisión",
      "candidates_found": "Candidatos encontrados ({count})",
      "reference": "Referencia",
      "candidate": "Candidato"
    },
    "no_candidates": "No se encontraron candidatos en ninguna fuente."
  }
  /* ... complete the rest ... */
}
```

### 4. Portuguese Catalog

Follow the same structure. Reference translations (illustrative — a human reviewer should confirm BR vs. PT-PT conventions; default to neutral Portuguese where possible):

```jsonc
{
  "common": {
    "app_name": "Biblio Checker",
    "submit": "Enviar",
    "cancel": "Cancelar",
    "remove": "Remover",
    "retry": "Tentar novamente",
    "close": "Fechar",
    "copy": "Copiar",
    "loading": "Carregando…",
    "language_label": "Idioma",
    "theme_label": "Tema"
  },
  "home": {
    "hero_title": "Envie sua bibliografia",
    "hero_subtitle": "Envie um arquivo PDF ou DOCX.",
    "footer_tagline": "Biblio Checker — Validação de referências acadêmicas"
  },
  "dropzone": {
    "prompt_primary": "Solte seu arquivo aqui",
    "prompt_secondary": "PDF ou DOCX, até 10 MB",
    "validation_file_too_large": "O arquivo excede o tamanho máximo de 10 MB.",
    "validation_unsupported_format": "Apenas arquivos PDF e DOCX são permitidos."
  },
  "status": {
    "queued": "Na fila",
    "running": "Em execução",
    "succeeded": "Concluído",
    "failed": "Falhou",
    "expired": "Expirado",
    "waiting": "Aguardando processamento…",
    "stage_label": "Etapa: {stage}"
  },
  "results": {
    "classification": {
      "verified": "Verificada",
      "likely_verified": "Prov. verificada",
      "ambiguous": "Ambígua",
      "not_found": "Não encontrada",
      "suspicious": "Suspeita",
      "processing_error": "Erro"
    },
    "fields": {
      "authors": "Autores",
      "year": "Ano",
      "venue": "Revista/Editora",
      "publisher": "Editora",
      "issn": "ISSN",
      "volume": "Volume",
      "issue": "Número",
      "pages": "Páginas"
    },
    "no_candidates": "Nenhum candidato encontrado em nenhuma fonte."
  }
  /* ... complete the rest ... */
}
```

### 5. Key Shape Invariant

All three files must produce the **exact same** nested key set. Enforce this with a lightweight unit test (see Acceptance Criteria).

Placeholder names must also match across files (`{fileName}`, `{count}`, `{stage}`, `{fileSizeMB}` where used) — a catalog where `es.json` uses `{filename}` and `en.json` uses `{fileName}` will break at call sites. Use camelCase consistently.

### 6. No Copy Concatenation

Do not split phrases into multiple keys and concatenate in components (`t("stage")` + `":"` + `stage`). Interpolation is the only assembly mechanism: `t("status.stage_label", { stage })`.

### 7. Plural Forms

Where the current UI uses `({evidence.length})` style inline counts, use ICU plural in the catalog:

```jsonc
{
  "results": {
    "section": {
      "candidates_found": "{count, plural, =0 {No candidates} one {# candidate} other {# candidates}}"
    }
  }
}
```

Only introduce plurals for strings where the count appears in copy *around the number* (e.g. "1 candidate" vs. "2 candidates"). When the number stands alone or with a separator (e.g. header + count), simple interpolation is enough.

## Acceptance Criteria

- [ ] `apps/frontend/messages/{es,pt,en}.json` exist, are valid JSON, and have identical nested key shape.
- [ ] Every hardcoded user-facing string identified by a full grep of `apps/frontend/` (excluding tests) has a matching catalog key.
- [ ] Placeholder names are consistent across the three files (grep each file for `{[a-zA-Z_]+}` and compare).
- [ ] Accent corrections noted in Section 3 are applied in the Spanish file.
- [ ] `global.d.ts` picks up the catalog type for autocompletion in `useTranslations()`.
- [ ] Running `pnpm --filter frontend exec tsc --noEmit` succeeds.
- [ ] No component imports the catalog files directly — they are consumed only via `useTranslations()` / `getTranslations()`.

## Verification

- Add a throwaway Node script `scripts/verify-message-shape.mjs` (outside the production build) that loads all three files, walks the nested key set, and fails if any file is missing a key present in another. Run it in CI. Example (can be kept or dropped):

```javascript
// scripts/verify-message-shape.mjs
import en from "../apps/frontend/messages/en.json" with { type: "json" };
import es from "../apps/frontend/messages/es.json" with { type: "json" };
import pt from "../apps/frontend/messages/pt.json" with { type: "json" };

function keys(obj, prefix = "") {
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    return Object.entries(obj).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k));
  }
  return [prefix];
}

const all = { en: keys(en), es: keys(es), pt: keys(pt) };
const reference = new Set(all.en);
const diffs = [];
for (const [lang, list] of Object.entries(all)) {
  for (const k of list) if (!reference.has(k)) diffs.push(`${lang}: extra ${k}`);
  for (const k of reference) if (!list.includes(k)) diffs.push(`${lang}: missing ${k}`);
}
if (diffs.length) {
  console.error(diffs.join("\n"));
  process.exit(1);
}
```

## Dependencies

- **Depends on:** Step 08 (infrastructure).
- **Informs:** Step 10 (component migration reads from these catalogs).
