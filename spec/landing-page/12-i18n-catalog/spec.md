# Step 12 — i18n Catalog

## Scope

This step specifies all i18n keys required by the landing page across EN, ES, PT.

## Context

Biblio Checker uses next-intl with three message catalogs at `apps/frontend/messages/{en,es,pt}.json`. All three catalogs MUST have identical key sets (enforced by existing `_shape.test.ts`).

## Requirements

### 1) Hero Keys

Under `landing.hero`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.hero.eyebrow` | Academic integrity, verified | Integridad académica, verificada | Integridade acadêmica, verificada |
| `landing.hero.title` | Detect fabricated academic references | Detecta referencias académicas fabricadas | Detecte referências acadêmicas fabricadas |
| `landing.hero.subtitle` | AI-generated documents often contain plausible-looking but non-existent citations. Biblio Checker verifies each reference against trusted academic databases. | Los documentos generados por IA a menudo contienen citas que parecen reales pero no existen. Biblio Checker verifica cada referencia contra bases de datos académicas confiables. | Documentos gerados por IA frequentemente contêm citações plausíveis mas inexistentes. O Biblio Checker verifica cada referência em bancos de dados acadêmicos confiáveis. |
| `landing.hero.cta_primary` | Try now | Probar ahora | Experimentar agora |
| `landing.hero.cta_secondary` | See demo with example | Ver demo con ejemplo | Ver demo com exemplo |
| `landing.hero.socialProof` | Verified against OpenAlex, SciELO, arXiv | Verificado contra OpenAlex, SciELO, arXiv | Verificado contra OpenAlex, SciELO, arXiv |

### 2) Problem Section Keys

Under `landing.problem`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.problem.title` | The bibliographic deep fake problem | El problema de las referencias falsas | O problema das referências falsas |
| `landing.problem.subtitle` | Why this tool exists | Por qué existe esta herramienta | Por que esta ferramenta existe |
| `landing.problem.fact1.title` | AI fabricates plausible citations | La IA fabrica citas que parecen reales | A IA fabrica citações plausíveis |
| `landing.problem.fact1.desc` | Large language models routinely generate realistic-looking references to papers and authors that do not exist. | Los modelos de lenguaje generan constantemente referencias realistas a artículos y autores que no existen. | Modelos de linguagem geram rotineiramente referências realistas a artigos e autores que não existem. |
| `landing.problem.fact2.title` | Manual verification takes hours | La verificación manual toma horas | A verificação manual leva horas |
| `landing.problem.fact2.desc` | Checking dozens of references against multiple databases is slow and error-prone. Reviewers often skip it. | Verificar docenas de referencias contra múltiples bases de datos es lento y propenso a errores. Los revisores a menudo lo omiten. | Verificar dezenas de referências em múltiplos bancos de dados é lento e propenso a erros. Revisores frequentemente pulam esta etapa. |
| `landing.problem.fact3.title` | Fake citations slip through review | Las citas falsas pasan el filtro | Citações falsas passam pela revisão |
| `landing.problem.fact3.desc` | Undetected fabricated references compromise academic integrity and erode trust in published work. | Las referencias fabricadas no detectadas comprometen la integridad académica y erosionan la confianza. | Referências fabricadas não detectadas comprometem a integridade acadêmica e erodem a confiança. |

### 3) How It Works Keys

Under `landing.howItWorks`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.howItWorks.title` | How it works | Cómo funciona | Como funciona |
| `landing.howItWorks.step1.title` | Upload your document | Sube tu documento | Envie seu documento |
| `landing.howItWorks.step1.desc` | Drop a PDF or DOCX file with a bibliography. No account needed. | Arrastra un archivo PDF o DOCX con bibliografía. No necesitas cuenta. | Arraste um arquivo PDF ou DOCX com bibliografia. Sem necessidade de conta. |
| `landing.howItWorks.step2.title` | We verify each reference | Verificamos cada referencia | Verificamos cada referência |
| `landing.howItWorks.step2.desc` | Every citation is cross-checked against OpenAlex, SciELO, and arXiv in parallel. | Cada cita se verifica en paralelo contra OpenAlex, SciELO y arXiv. | Cada citação é verificada em paralelo contra OpenAlex, SciELO e arXiv. |
| `landing.howItWorks.step3.title` | See authenticity score + evidence | Ve el puntaje de autenticidad y la evidencia | Veja a pontuação de autenticidade e a evidência |
| `landing.howItWorks.step3.desc` | A clear 0-100 score with per-reference verdicts, evidence, and a shareable report. | Un puntaje claro de 0-100 con veredictos por referencia, evidencia y un informe compartible. | Uma pontuação clara de 0-100 com veredictos por referência, evidência e um relatório compartilhável. |

### 4) Demo Section Keys

Under `landing.demo`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.demo.title` | This is what you get | Esto es lo que obtienes | Isto é o que você recebe |
| `landing.demo.subtitle` | A real score from a document with mixed references | Un puntaje real de un documento con referencias mixtas | Uma pontuação real de um documento com referências mistas |
| `landing.demo.caption` | Example analysis | Análisis de ejemplo | Análise de exemplo |

### 5) Use Cases Keys

Under `landing.useCases`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.useCases.title` | Built for your workflow | Diseñado para tu flujo de trabajo | Feito para seu fluxo de trabalho |
| `landing.useCases.professor.title` | Professors and reviewers | Profesores y revisores | Professores e revisores |
| `landing.useCases.professor.desc` | Validate student bibliographies and peer submissions in seconds. Share a link with the author to discuss findings. | Valida bibliografías de alumnos y trabajos de revisión en segundos. Comparte un enlace con el autor para discutir los hallazgos. | Valide bibliografias de alunos e submissões de pares em segundos. Compartilhe um link com o autor para discutir os resultados. |
| `landing.useCases.student.title` | Students and researchers | Estudiantes e investigadores | Estudantes e pesquisadores |
| `landing.useCases.student.desc` | Self-check your citations before submission. Catch fabricated or misattributed references in your own draft. | Verifica tus citas antes de entregar. Detecta referencias fabricadas o mal atribuidas en tu borrador. | Verifique suas citações antes de enviar. Detecte referências fabricadas ou mal atribuídas no seu rascunho. |
| `landing.useCases.institution.title` | Institutions | Instituciones | Instituições |
| `landing.useCases.institution.desc` | LMS integrations and batch processing for academic departments. API access for automated workflows. | Integraciones con LMS y procesamiento por lotes para departamentos académicos. Acceso a API para flujos automatizados. | Integrações com LMS e processamento em lote para departamentos acadêmicos. Acesso via API para fluxos automatizados. |
| `landing.useCases.comingSoon` | Coming soon | Próximamente | Em breve |

### 6) Sources Section Keys

Under `landing.sources`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.sources.title` | Verified against trusted sources | Verificado contra fuentes confiables | Verificado contra fontes confiáveis |
| `landing.sources.subtitle` | We cross-check your references in parallel against the leading open academic databases. | Verificamos tus referencias en paralelo contra las principales bases de datos académicas abiertas. | Verificamos suas referências em paralelo contra os principais bancos de dados acadêmicos abertos. |
| `landing.sources.openalex.desc` | Global academic index | Índice académico global | Índice acadêmico global |
| `landing.sources.scielo.desc` | Latin American journals | Revistas latinoamericanas | Revistas latino-americanas |
| `landing.sources.arxiv.desc` | Preprints across sciences | Preprints de ciencias | Preprints em ciências |
| `landing.sources.openlibrary.desc` | Books and publications | Libros y publicaciones | Livros e publicações |

### 7) Final CTA Keys

Under `landing.cta`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.cta.title` | Ready to verify your bibliography? | ¿Listo para verificar tu bibliografía? | Pronto para verificar sua bibliografia? |
| `landing.cta.subtitle` | No account needed. Results in under a minute. | No necesitas cuenta. Resultados en menos de un minuto. | Sem necessidade de conta. Resultados em menos de um minuto. |

### 8) Footer Keys

Under `landing.footer`:

| Key | EN | ES | PT |
|-----|----|----|-----|
| `landing.footer.product` | Product | Producto | Produto |
| `landing.footer.resources` | Resources | Recursos | Recursos |
| `landing.footer.home` | Home | Inicio | Início |
| `landing.footer.app` | App | Aplicación | Aplicativo |
| `landing.footer.github` | GitHub | GitHub | GitHub |
| `landing.footer.docs` | Documentation | Documentación | Documentação |
| `landing.footer.about` | About | Acerca de | Sobre |
| `landing.footer.copyright` | © 2026 Biblio Checker | © 2026 Biblio Checker | © 2026 Biblio Checker |

**Note:** The footer tagline is NOT a new key — it MUST reuse the existing `home.footer_tagline` key already present in all three catalogs. No new `landing.footer.tagline` key is introduced.

### 9) Key Synchronization

All three catalogs MUST be updated atomically. Adding a key to one without the others causes the existing `_shape.test.ts` to fail.

### 10) Character Requirements

- Spanish: proper accents (á, é, í, ó, ú, ñ)
- Portuguese: proper accents and cedilla (ã, õ, ç, é, ê)
- All strings MUST be valid UTF-8

## Acceptance Criteria

- All 38 keys present in all three catalogs
- Key paths match the specification
- All three catalogs have identical key sets (existing shape test passes)
- Spanish translations include proper accents
- Portuguese translations include proper accents and cedilla
- No existing keys are modified or removed

## Integration Points

- Step 03 (Marketing Layout) — consumes footer keys
- Step 04 (Hero Section) — consumes hero keys
- Step 05 (Problem Section) — consumes problem keys
- Step 06 (How It Works) — consumes howItWorks keys
- Step 07 (Demo Score) — consumes demo keys
- Step 08 (Use Cases) — consumes useCases keys
- Step 09 (Sources Section) — consumes sources keys
- Step 10 (Final CTA) — consumes cta keys

## Dependencies

- None (cross-cutting step, should be done first)
