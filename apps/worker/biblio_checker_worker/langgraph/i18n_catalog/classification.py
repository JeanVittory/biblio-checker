"""Classification reason catalog — ES / PT / EN translations.

Each ``register()`` call covers all three locales so copy drift is visible in
code review. Spanish text is transcribed byte-for-byte from the original
f-strings in ``classification.py`` (before i18n refactor) to guarantee
ES output is byte-identical for ``locale='es'``.
"""

from __future__ import annotations

from biblio_checker_worker.langgraph.i18n import register

# ---------------------------------------------------------------------------
# Single-candidate match (used by Rule 5 and Rule 6 Branch B)
# ---------------------------------------------------------------------------

register(
    "class.match.single.with_title",
    {
        "es": "Coincidencia del {score} con '{title}' en {source}. {suffix}",
        "pt": "Correspondência de {score} com '{title}' em {source}. {suffix}",
        "en": "{score} match with '{title}' in {source}. {suffix}",
    },
)

register(
    "class.match.single.no_title",
    {
        "es": "Coincidencia del {score} en {source}. {suffix}",
        "pt": "Correspondência de {score} em {source}. {suffix}",
        "en": "{score} match in {source}. {suffix}",
    },
)

# ---------------------------------------------------------------------------
# Suffixes for single-candidate reasons
# ---------------------------------------------------------------------------

register(
    "class.strong_metadata.suffix",
    {
        "es": "Sin DOI ni identificador canónico para confirmar.",
        "pt": "Sem DOI nem identificador canônico para confirmar.",
        "en": "No DOI or canonical identifier to confirm.",
    },
)

register(
    "class.weak_metadata.suffix",
    {
        "es": "La similitud es insuficiente para confirmar.",
        "pt": "A similaridade é insuficiente para confirmar.",
        "en": "The similarity is insufficient to confirm.",
    },
)

# ---------------------------------------------------------------------------
# Rule 1: Exact DOI match
# ---------------------------------------------------------------------------

register(
    "class.doi_match.single.with_title_and_year",
    {
        "es": "El DOI {doi} coincide con '{title}' ({year}) en {source}.",
        "pt": "O DOI {doi} corresponde a '{title}' ({year}) em {source}.",
        "en": "DOI {doi} matches '{title}' ({year}) in {source}.",
    },
)

register(
    "class.doi_match.single.with_title_no_year",
    {
        "es": "El DOI {doi} coincide con '{title}' en {source}.",
        "pt": "O DOI {doi} corresponde a '{title}' em {source}.",
        "en": "DOI {doi} matches '{title}' in {source}.",
    },
)

register(
    "class.doi_match.single.no_title_with_year",
    {
        "es": "El DOI {doi} coincide con un registro ({year}) en {source}.",
        "pt": "O DOI {doi} corresponde a um registro ({year}) em {source}.",
        "en": "DOI {doi} matches a record ({year}) in {source}.",
    },
)

register(
    "class.doi_match.single.no_title",
    {
        "es": "El DOI {doi} coincide con un registro en {source}.",
        "pt": "O DOI {doi} corresponde a um registro em {source}.",
        "en": "DOI {doi} matches a record in {source}.",
    },
)

# ---------------------------------------------------------------------------
# Rule 2: Exact arXiv identifier match
# ---------------------------------------------------------------------------

register(
    "class.arxiv_match.with_title_and_year",
    {
        "es": "El identificador arXiv {arxiv_id} coincide con '{title}' ({year}) en arXiv.",  # noqa: E501
        "pt": "O identificador arXiv {arxiv_id} corresponde a '{title}' ({year}) no arXiv.",  # noqa: E501
        "en": "arXiv identifier {arxiv_id} matches '{title}' ({year}) in arXiv.",
    },
)

register(
    "class.arxiv_match.with_title_no_year",
    {
        "es": "El identificador arXiv {arxiv_id} coincide con '{title}' en arXiv.",
        "pt": "O identificador arXiv {arxiv_id} corresponde a '{title}' no arXiv.",
        "en": "arXiv identifier {arxiv_id} matches '{title}' in arXiv.",
    },
)

register(
    "class.arxiv_match.no_title_with_year",
    {
        "es": "El identificador arXiv {arxiv_id} coincide con un registro ({year}) en arXiv.",  # noqa: E501
        "pt": "O identificador arXiv {arxiv_id} corresponde a um registro ({year}) no arXiv.",  # noqa: E501
        "en": "arXiv identifier {arxiv_id} matches a record ({year}) in arXiv.",
    },
)

register(
    "class.arxiv_match.no_title",
    {
        "es": "El identificador arXiv {arxiv_id} coincide con un registro en arXiv.",
        "pt": "O identificador arXiv {arxiv_id} corresponde a um registro no arXiv.",
        "en": "arXiv identifier {arxiv_id} matches a record in arXiv.",
    },
)

# ---------------------------------------------------------------------------
# Rule 3: DOI conflict variants
# ---------------------------------------------------------------------------

register(
    "class.doi_conflict.both_titles_both_years",
    {
        "es": (
            "El DOI {doi} apunta a '{matched_title}'{matched_year_suffix} en {source},"
            " pero la referencia cita '{ref_title}'{ref_year_suffix}."
            " La discrepancia sugiere una referencia fabricada o un DOI incorrecto."
        ),
        "pt": (
            "O DOI {doi} aponta para '{matched_title}'{matched_year_suffix}"  # noqa: E501
            " em {source}, mas a referência cita '{ref_title}'{ref_year_suffix}."
            " A discrepância sugere uma referência fabricada ou um DOI incorreto."
        ),
        "en": (
            "DOI {doi} points to '{matched_title}'{matched_year_suffix} in {source},"
            " but the reference cites '{ref_title}'{ref_year_suffix}."
            " The discrepancy suggests a fabricated reference or an incorrect DOI."
        ),
    },
)

register(
    "class.doi_conflict.both_titles_both_years.no_snippets",
    {
        "es": (
            "El DOI {doi} apunta a un trabajo con"
            " título y año incompatibles en {source}."
            " La discrepancia sugiere una referencia fabricada o un DOI incorrecto."
        ),
        "pt": (
            "O DOI {doi} aponta para um trabalho com"
            " título e ano incompatíveis em {source}."
            " A discrepância sugere uma referência fabricada ou um DOI incorreto."
        ),
        "en": (
            "DOI {doi} points to a work with"
            " incompatible title and year in {source}."
            " The discrepancy suggests a fabricated reference or an incorrect DOI."
        ),
    },
)

register(
    "class.doi_conflict.title_only.both_snippets",
    {
        "es": (
            "El DOI {doi} apunta a '{matched_title}'"
            " en {source}, pero la referencia cita"
            " '{ref_title}'. El título no coincide,"
            " lo que puede indicar un DOI incorrecto."
        ),
        "pt": (
            "O DOI {doi} aponta para '{matched_title}'"
            " em {source}, mas a referência cita"
            " '{ref_title}'. O título não corresponde,"
            " o que pode indicar um DOI incorreto."
        ),
        "en": (
            "DOI {doi} points to '{matched_title}'"
            " in {source}, but the reference cites"
            " '{ref_title}'. The title does not match,"
            " which may indicate an incorrect DOI."
        ),
    },
)

register(
    "class.doi_conflict.title_only.no_snippets",
    {
        "es": (
            "El DOI {doi} apunta a un trabajo con"
            " título incompatible en {source}."
            " Puede indicar un DOI incorrecto."
        ),
        "pt": (
            "O DOI {doi} aponta para um trabalho com"
            " título incompatível em {source}."
            " Pode indicar um DOI incorreto."
        ),
        "en": (
            "DOI {doi} points to a work with"
            " incompatible title in {source}."
            " May indicate an incorrect DOI."
        ),
    },
)

register(
    "class.doi_conflict.year_only.both_years",
    {
        "es": (
            "El DOI {doi} apunta a un registro de"
            " {matched_year} en {source}, pero la"
            " referencia cita el año {ref_year}."
            " La discrepancia en el año puede"
            " indicar un DOI incorrecto."
        ),
        "pt": (
            "O DOI {doi} aponta para um registro de"
            " {matched_year} em {source}, mas a"
            " referência cita o ano {ref_year}."
            " A discrepância no ano pode"
            " indicar um DOI incorreto."
        ),
        "en": (
            "DOI {doi} points to a record from"
            " {matched_year} in {source}, but the"
            " reference cites year {ref_year}."
            " The year discrepancy may"
            " indicate an incorrect DOI."
        ),
    },
)

register(
    "class.doi_conflict.year_only.no_years",
    {
        "es": (
            "El DOI {doi} apunta a un trabajo con"
            " año incompatible en {source}."
            " Puede indicar un DOI incorrecto."
        ),
        "pt": (
            "O DOI {doi} aponta para um trabalho com"
            " ano incompatível em {source}."
            " Pode indicar um DOI incorreto."
        ),
        "en": (
            "DOI {doi} points to a work with"
            " incompatible year in {source}."
            " May indicate an incorrect DOI."
        ),
    },
)

# ---------------------------------------------------------------------------
# Rule 4: Cross-source metadata conflict
# ---------------------------------------------------------------------------

register(
    "class.cross_source_conflict",
    {
        "es": (
            "Se encontraron coincidencias en {source_a} y {source_b},"
            " pero sus metadatos son contradictorios: {conflict_detail}."
        ),
        "pt": (
            "Foram encontradas correspondências em {source_a} e {source_b},"
            " mas seus metadatos são contraditórios: {conflict_detail}."
        ),
        "en": (
            "Matches were found in {source_a} and {source_b},"
            " but their metadata are contradictory: {conflict_detail}."
        ),
    },
)

# Conflict detail phrases (not standalone rendered — passed as {conflict_detail})
register(
    "class.cross_source_conflict.detail.years_and_dois",
    {
        "es": "los años y DOIs difieren",
        "pt": "os anos e DOIs diferem",
        "en": "years and DOIs differ",
    },
)

register(
    "class.cross_source_conflict.detail.years",
    {
        "es": "los años difieren ({year_a} vs {year_b})",
        "pt": "os anos diferem ({year_a} vs {year_b})",
        "en": "years differ ({year_a} vs {year_b})",
    },
)

register(
    "class.cross_source_conflict.detail.dois",
    {
        "es": "los DOIs difieren",
        "pt": "os DOIs diferem",
        "en": "DOIs differ",
    },
)

# ---------------------------------------------------------------------------
# Fallback placeholder for absent titles
# ---------------------------------------------------------------------------

register(
    "class.no_title_placeholder",
    {
        "es": "sin título",
        "pt": "sem título",
        "en": "no title",
    },
)

# ---------------------------------------------------------------------------
# Rule 6a: Multiple plausible candidates
# ---------------------------------------------------------------------------

register(
    "class.ambiguous_multi",
    {
        "es": (
            "Se encontraron {count} candidatos. Los mejores:"
            " '{title1}' ({score1}, {source1}) y"
            " '{title2}' ({score2}, {source2})."
            " Ninguno es concluyente."
        ),
        "pt": (
            "Foram encontrados {count} candidatos. Os melhores:"
            " '{title1}' ({score1}, {source1}) e"
            " '{title2}' ({score2}, {source2})."
            " Nenhum é conclusivo."
        ),
        "en": (
            "Found {count} candidates. Top matches:"
            " '{title1}' ({score1}, {source1}) and"
            " '{title2}' ({score2}, {source2})."
            " None is conclusive."
        ),
    },
)

# ---------------------------------------------------------------------------
# Rule 7: Insufficient metadata
# ---------------------------------------------------------------------------

register(
    "class.insufficient_metadata",
    {
        "es": (
            "La referencia no contiene metadatos suficientes"
            " (título, DOI o identificador)"
            " para realizar una búsqueda confiable."
        ),
        "pt": (
            "A referência não contém metadados suficientes"
            " (título, DOI ou identificador)"
            " para realizar uma busca confiável."
        ),
        "en": (
            "The reference does not contain sufficient metadata"
            " (title, DOI, or identifier)"
            " to perform a reliable search."
        ),
    },
)

# ---------------------------------------------------------------------------
# Rule 8: No match in any source
# ---------------------------------------------------------------------------

register(
    "class.not_found",
    {
        "es": (
            "No se encontraron coincidencias en ninguna fuente consultada"
            " (OpenAlex, SciELO, arXiv, Open Library)."
        ),
        "pt": (
            "Não foram encontradas correspondências em nenhuma fonte consultada"
            " (OpenAlex, SciELO, arXiv, Open Library)."
        ),
        "en": (
            "No matches were found in any consulted source"
            " (OpenAlex, SciELO, arXiv, Open Library)."
        ),
    },
)

# ---------------------------------------------------------------------------
# Rule 9: Source timeout, no candidates
# ---------------------------------------------------------------------------

register(
    "class.source_timeout_not_found",
    {
        "es": (
            "Algunas fuentes no respondieron a tiempo."
            " Los resultados pueden ser incompletos."
        ),
        "pt": (
            "Algumas fontes não responderam a tempo."
            " Os resultados podem estar incompletos."
        ),
        "en": ("Some sources did not respond in time. Results may be incomplete."),
    },
)

# ---------------------------------------------------------------------------
# Processing error fallback
# ---------------------------------------------------------------------------

register(
    "class.processing_error",
    {
        "es": "Ocurrió un error interno al procesar esta referencia.",
        "pt": "Ocorreu um erro interno ao processar esta referência.",
        "en": "An internal error occurred while processing this reference.",
    },
)
