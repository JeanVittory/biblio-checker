# Step 08 — i18n Catalog

## Scope

This step specifies the full set of i18n keys introduced by this feature, with translations for the three supported locales (Spanish, Portuguese, English). It covers:
- Tab labels
- Paste form labels, placeholders, validation hints, status messages
- Recent Analyses input-kind badges and tooltips

This step does NOT cover:
- Worker-side i18n catalogs (decisionReason, warnings) — handled by `i18n-multilingual-support` suite; no new keys required because text-mode results use the existing reasonCodes
- Existing keys (file flow, hero, footer, etc.) — unchanged

## Context

The project uses `next-intl` with message catalogs in `apps/frontend/messages/{es,en,pt}.json`. The keys for this feature SHOULD be grouped under a logical namespace following existing conventions (e.g., `paste.*`, `app.tabs.*`, `recent.*`). Spanish (`es`) is the source of truth and the default locale; Portuguese (`pt`) and English (`en`) MUST be translated by a fluent speaker or a high-quality translation service before merging.

## Requirements

### 1) New Keys

The following keys MUST be added to all three message catalogs.

#### Tabs (in `app.tabs.*`)

| Key | ES | PT | EN |
|-----|----|----|----|
| `app.tabs.upload` | Subir documento | Enviar documento | Upload document |
| `app.tabs.paste` | Pegar cita | Colar citação | Paste citation |
| `app.tabs.aria_label` | Modo de entrada | Modo de entrada | Input mode |

#### Paste Form (in `paste.*`)

| Key | ES | PT | EN |
|-----|----|----|----|
| `paste.label` | Pega tu cita bibliográfica | Cole sua citação bibliográfica | Paste your bibliographic citation |
| `paste.placeholder` | Ej.: García, M. (2023). Título del artículo. Revista de Estudios, 12(3), 45-67. https://doi.org/... | Ex.: García, M. (2023). Título do artigo. Revista de Estudos, 12(3), 45-67. https://doi.org/... | Ex.: García, M. (2023). Article title. Journal of Studies, 12(3), 45-67. https://doi.org/... |
| `paste.helper` | Pega una sola cita (entre 20 y 2000 caracteres). | Cole uma única citação (entre 20 e 2000 caracteres). | Paste a single citation (between 20 and 2000 characters). |
| `paste.counter` | {count} / 2000 | {count} / 2000 | {count} / 2000 |
| `paste.too_short` | La cita debe tener al menos 20 caracteres. | A citação deve ter pelo menos 20 caracteres. | The citation must be at least 20 characters long. |
| `paste.too_long` | La cita no puede superar los 2000 caracteres. | A citação não pode exceder 2000 caracteres. | The citation cannot exceed 2000 characters. |
| `paste.empty` | Pega una cita para verificarla. | Cole uma citação para verificar. | Paste a citation to verify it. |
| `paste.submit` | Verificar | Verificar | Verify |
| `paste.submitting` | Enviando para análisis… | Enviando para análise… | Sending for analysis… |
| `paste.success` | Cita enviada. La verás en Análisis Recientes. | Citação enviada. Você a verá em Análises Recentes. | Citation submitted. You'll see it in Recent Analyses. |
| `paste.submit_failed` | No pudimos enviar la cita. Verifica tu conexión e inténtalo de nuevo. | Não foi possível enviar a citação. Verifique sua conexão e tente novamente. | Could not submit the citation. Check your connection and try again. |
| `paste.backend_error` | El servidor rechazó la solicitud. {message} | O servidor rejeitou a solicitação. {message} | The server rejected the request. {message} |
| `paste.storage_full` | Tu navegador no tiene espacio para guardar la nueva entrada en Análisis Recientes. La cita se envió correctamente, pero borra entradas antiguas para verla. | Seu navegador não tem espaço para salvar a nova entrada em Análises Recentes. A citação foi enviada com sucesso, mas exclua entradas antigas para vê-la. | Your browser is out of space to save the new entry in Recent Analyses. The citation was submitted, but delete older entries to see it. |

#### Recent Analyses Badges (in `recent.badge.*`)

| Key | ES | PT | EN |
|-----|----|----|----|
| `recent.badge.text` | Texto | Texto | Text |
| `recent.badge.text_tooltip` | Cita pegada como texto | Citação colada como texto | Citation pasted as text |
| `recent.badge.pdf` | PDF | PDF | PDF |
| `recent.badge.pdf_tooltip` | Documento PDF | Documento PDF | PDF document |
| `recent.badge.docx` | DOCX | DOCX | DOCX |
| `recent.badge.docx_tooltip` | Documento DOCX | Documento DOCX | DOCX document |
| `recent.badge.document` | Documento | Documento | Document |
| `recent.badge.document_tooltip` | Documento cargado | Documento carregado | Uploaded document |

### 2) Key Naming Conventions

- All keys are flat (dot-separated), consistent with existing message catalog style
- Reuse existing namespaces where they exist (`app.*`, `recent.*`); introduce `paste.*` as a new namespace
- All visible strings MUST come from the catalogs; no hardcoded user-facing text in the React components

### 3) Pluralization and Interpolation

- `paste.counter` uses the `{count}` placeholder (numeric)
- `paste.backend_error` uses the `{message}` placeholder (string from the gateway/backend)
- No plural forms required for v1

### 4) Tone and Voice

- Spanish: informal `tú` (matches existing app voice — verify with the existing catalog before finalizing)
- Portuguese: same register as Spanish (informal "você" / "tu" matching existing convention — verify against current catalog)
- English: friendly imperative ("Paste", "Verify", "Check")
- Error messages avoid blame and offer a corrective action when possible

### 5) Translation Quality Requirements

- Translations MUST NOT use machine-translated text without a fluent-speaker review
- "Citation" / "cita" / "citação" MUST be translated consistently across the catalog
- "Reference" is interchangeable with "citation" in this product; pick one term per locale and stick to it (current convention: `cita`/`citação`/`citation`)

### 6) Catalog File Locations

- Spanish: `apps/frontend/messages/es.json`
- Portuguese: `apps/frontend/messages/pt.json`
- English: `apps/frontend/messages/en.json`

The implementer MUST add the new keys to ALL THREE catalogs in the same PR. Missing-key fallback behavior is `next-intl`'s default (renders the key path); we MUST NOT rely on that.

### 7) No New Locales

This step does NOT add a new locale. The supported set remains `{es, pt, en}` per the existing `i18n-multilingual-support` suite.

### 8) Documentation

The new keys MUST be added to any existing developer-facing documentation that lists the i18n catalog (e.g., `apps/frontend/AGENTS.md` if it has an i18n section). If no such documentation exists, none is required.

## Acceptance Criteria

- All keys listed in § 1 are present in `es.json`, `pt.json`, and `en.json`
- No key is missing from any of the three files (catalogs are key-equivalent)
- Switching the locale via `<LanguageToggle>` updates all visible strings in the new feature
- No hardcoded English/Spanish/Portuguese strings appear in `single-reference-form.tsx` or the tab labels
- The `paste.counter` interpolates the live character count
- The `paste.backend_error` interpolates a backend message (when present)
- Translations have been reviewed by a fluent speaker (process check, not automated)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User switches locale while a submission is in flight | Status banner updates to the new locale on next render; no broken interpolation |
| Backend message contains characters that need escaping in the locale | Pass-through; the catalog uses `{message}` as-is, React handles XSS prevention |
| A locale catalog is missing a key (regression) | `next-intl` renders the key path; CI MUST catch this if the project has a key-completeness check; otherwise, manual review is required |
| Plural form needed in the future (e.g., counter "1 character" vs "2 characters") | Out of scope for v1; current counter format `{count} / 2000` sidesteps the issue |

## Integration Points

- Step 06 (Input Component) — consumes `paste.*`
- Step 07 (Tabs & Recent Analyses) — consumes `app.tabs.*`, `recent.badge.*`
- Existing `apps/frontend/messages/*.json` files

## Dependencies

- None (this step is cross-cutting and can be authored in parallel with Step 06/07)
