# Step 09 — i18n Catalog

## Scope

This step specifies all i18n keys required by the Momento Wow feature set across EN, ES, and PT. It covers:
- Complete key catalog with exact key paths and values
- Key organization within the existing message structure
- Constraints on catalog synchronization

This step does NOT cover:
- The i18n infrastructure setup (already exists via next-intl)
- How components consume these keys (covered in Steps 03, 05, 08)
- Backend/worker i18n (no backend changes in this suite)

## Context

Biblio Checker uses `next-intl` with three message catalogs at `apps/frontend/messages/{en,es,pt}.json`. The catalogs use nested key structures (e.g., `results.classification.verified`). All three catalogs MUST have identical key sets — this is enforced by existing tests.

## Requirements

### 1) Authenticity Score Keys

The following keys MUST be added under `results.score`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `results.score.title` | Authenticity Score | Puntaje de autenticidad | Pontuação de autenticidade |
| `results.score.high` | High authenticity | Alta autenticidad | Alta autenticidade |
| `results.score.medium` | Needs review | Requiere revisión | Requer revisão |
| `results.score.low` | Low authenticity | Baja autenticidad | Baixa autenticidade |

### 2) Sample Document Keys

The following keys MUST be added under `dropzone`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `dropzone.trySample` | Try with an example | Probar con un ejemplo | Experimentar com um exemplo |
| `dropzone.sampleDescription` | See a sample analysis with real and fabricated references | Ve un análisis de muestra con referencias reales y fabricadas | Veja uma análise de exemplo com referências reais e fabricadas |
| `dropzone.sampleLoading` | Loading example... | Cargando ejemplo... | Carregando exemplo... |
| `dropzone.or` | or | o | ou |

### 3) Export Keys

The following keys MUST be added under `results.export`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `results.export.csv` | Export CSV | Exportar CSV | Exportar CSV |
| `results.export.pdf` | Export PDF | Exportar PDF | Exportar PDF |
| `results.export.generating` | Generating... | Generando... | Gerando... |
| `results.export.error` | Export failed. Please try again. | Error al exportar. Intente de nuevo. | Erro ao exportar. Tente novamente. |

### 4) PDF Report Keys

The following keys MUST be added under `results.pdf` for content rendered inside the PDF document:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `results.pdf.title` | Bibliographic Reference Analysis Report | Informe de análisis de referencias bibliográficas | Relatório de análise de referências bibliográficas |
| `results.pdf.summary` | Summary | Resumen | Resumo |
| `results.pdf.references` | Reference Details | Detalles de referencias | Detalhes das referências |
| `results.pdf.evidence` | Evidence | Evidencia | Evidência |
| `results.pdf.noEvidence` | No evidence found | Sin evidencia encontrada | Nenhuma evidência encontrada |
| `results.pdf.notAvailable` | N/A | N/D | N/D |
| `results.pdf.disclaimer` | This report was generated automatically. Results should be verified manually for critical decisions. | Este informe fue generado automáticamente. Los resultados deben verificarse manualmente para decisiones críticas. | Este relatório foi gerado automaticamente. Os resultados devem ser verificados manualmente para decisões críticas. |
| `results.pdf.page` | Page {current} of {total} | Página {current} de {total} | Página {current} de {total} |

### 5) Key Synchronization Constraint

All three catalogs (en.json, es.json, pt.json) MUST be updated atomically. Adding a key to one catalog without adding it to the others MUST cause existing i18n tests to fail.

### 6) Key Organization

New keys MUST follow the existing nesting conventions:
- `results.score.*` — new nested object under existing `results` key
- `results.export.*` — new nested object under existing `results` key
- `results.pdf.*` — new nested object under existing `results` key
- `dropzone.*` — added to existing `dropzone` object

No new top-level keys are introduced.

### 7) Placeholder Syntax

Keys that use placeholders MUST follow the ICU MessageFormat syntax used by next-intl:
- `{current}` and `{total}` in `results.pdf.page`

### 8) Character Requirements

- Spanish translations MUST include proper accents (á, é, í, ó, ú, ñ)
- Portuguese translations MUST include proper accents and cedilla (ã, õ, ç, é, ê)
- All strings MUST be valid UTF-8

## Acceptance Criteria

- All 20 keys are present in all three catalogs (en.json, es.json, pt.json)
- Key paths match the exact specification above
- All three catalogs have identical key sets (existing test passes)
- Spanish translations include proper accents
- Portuguese translations include proper accents and cedilla
- Placeholder syntax is correct for `results.pdf.page`
- No existing keys are modified or removed
- Keys are organized under the correct nested objects

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| A key is missing from one catalog | Existing i18n synchronization test fails |
| A key has the wrong placeholder syntax | next-intl throws a runtime warning |
| A translation is empty string | Acceptable but not recommended; use a dash or "N/A" if no translation exists |

## Integration Points

- Step 03 (Authenticity Score Component) — consumes `results.score.*` keys
- Step 05 (Sample Document Integration) — consumes `dropzone.trySample`, `dropzone.sampleDescription`, `dropzone.sampleLoading`, `dropzone.or`
- Step 07 (Export PDF) — consumes `results.pdf.*` keys
- Step 08 (Export Buttons Integration) — consumes `results.export.*` keys

## Dependencies

- None (cross-cutting step, should be done first)
