# Step 08 — i18n Catalog

## Scope

This step specifies all i18n keys required by the Share Link feature across EN, ES, and PT.

This step does NOT cover:
- The i18n infrastructure setup (already exists via next-intl)
- How components consume these keys (covered in Steps 06, 07)

## Context

Biblio Checker uses `next-intl` with three message catalogs at `apps/frontend/messages/{en,es,pt}.json`. All three catalogs MUST have identical key sets.

## Requirements

### 1) Share Button Keys

Add under `results.share`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `results.share.button` | Share | Compartir | Compartilhar |
| `results.share.copied` | Link copied! | Enlace copiado! | Link copiado! |
| `results.share.ready` | Link ready | Enlace listo | Link pronto |
| `results.share.error` | Could not generate link | No se pudo generar el enlace | Não foi possível gerar o link |
| `results.share.generating` | Generating... | Generando... | Gerando... |

### 2) Share Page Keys

Add under `sharePage`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `sharePage.title` | Shared Analysis Report | Informe de análisis compartido | Relatório de análise compartilhado |
| `sharePage.notFound` | This shared analysis was not found or has expired | Este análisis compartido no fue encontrado o ha expirado | Esta análise compartilhada não foi encontrada ou expirou |
| `sharePage.resultError` | Results could not be loaded | No se pudieron cargar los resultados | Os resultados não puderam ser carregados |
| `sharePage.tryBiblio` | Try Biblio Checker | Prueba Biblio Checker | Experimente o Biblio Checker |
| `sharePage.poweredBy` | Powered by Biblio Checker | Desarrollado por Biblio Checker | Desenvolvido por Biblio Checker |
| `sharePage.expiresOn` | This link expires on {date} | Este enlace expira el {date} | Este link expira em {date} |
| `sharePage.loading` | Loading shared analysis... | Cargando análisis compartido... | Carregando análise compartilhada... |

### 3) Key Synchronization

All three catalogs MUST be updated atomically. Existing i18n shape tests enforce identical key sets.

### 4) Placeholder Syntax

`sharePage.expiresOn` uses ICU MessageFormat placeholder `{date}`. The `date` value is a formatted date string resolved by the component before passing to `t()`.

### 5) Character Requirements

- Spanish: proper accents (á, é, í, ó, ú, ñ)
- Portuguese: proper accents and cedilla (ã, õ, ç, é, ê)

## Acceptance Criteria

- All 12 keys are present in all three catalogs
- Key paths match the specification
- All three catalogs have identical key sets (existing test passes)
- Placeholder syntax is correct for `sharePage.expiresOn`
- No existing keys are modified or removed

## Integration Points

- Step 06 (Share Page) — consumes `sharePage.*` keys
- Step 07 (Share Button) — consumes `results.share.*` keys

## Dependencies

- None (cross-cutting step, should be done first)
