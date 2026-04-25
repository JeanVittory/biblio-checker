"""Warning message catalog — ES / PT / EN translations.

Each ``register()`` call covers all three locales so copy drift is visible in
code review. Only the ``message`` field of warning dicts goes through
``render()``; the ``code`` field is machine-readable and stays in English.
"""

from __future__ import annotations

from biblio_checker_worker.langgraph.i18n import register

register(
    "warn.references_truncated",
    {
        "es": (
            "Se detectaron {total} referencias pero solo se procesaron"
            " las primeras {limit}."
        ),
        "pt": (
            "Foram detectadas {total} referências, mas apenas"
            " as primeiras {limit} foram processadas."
        ),
        "en": (
            "{total} references were detected but only the first {limit}"
            " were processed."
        ),
    },
)

register(
    "warn.source_timeout_partial",
    {
        "es": "La fuente {source_name} no respondió correctamente: {reason}.",
        "pt": "A fonte {source_name} não respondeu corretamente: {reason}.",
        "en": "Source {source_name} did not respond correctly: {reason}.",
    },
)

register(
    "warn.reference_verification_failed",
    {
        "es": "No se pudo verificar la referencia: {reason}.",
        "pt": "Não foi possível verificar a referência: {reason}.",
        "en": "Could not verify the reference: {reason}.",
    },
)

register(
    "warn.empty_document",
    {
        "es": "El documento no contiene texto extraíble.",
        "pt": "O documento não contém texto extraível.",
        "en": "The document contains no extractable text.",
    },
)

register(
    "warn.invalid_doi_format",
    {
        "es": "El DOI '{doi}' no cumple el formato esperado y se descartó.",
        "pt": "O DOI '{doi}' não cumpre o formato esperado e foi descartado.",
        "en": "DOI '{doi}' does not match the expected format and was discarded.",
    },
)

register(
    "warn.invalid_arxiv_id_format",
    {
        "es": (
            "El identificador arXiv '{arxiv_id}' no cumple el"
            " formato esperado y se descartó."
        ),
        "pt": (
            "O identificador arXiv '{arxiv_id}' não cumpre o"
            " formato esperado e foi descartado."
        ),
        "en": (
            "arXiv identifier '{arxiv_id}' does not match the"
            " expected format and was discarded."
        ),
    },
)

register(
    "warn.invalid_issn_format",
    {
        "es": "El ISSN '{issn}' no cumple el formato esperado y se descartó.",
        "pt": "O ISSN '{issn}' não cumpre o formato esperado e foi descartado.",
        "en": "ISSN '{issn}' does not match the expected format and was discarded.",
    },
)

register(
    "warn.normalization_count_mismatch",
    {
        "es": (
            "El LLM devolvió {returned} entradas normalizadas;"
            " se esperaban {expected}."
            " Es posible que algunas referencias no hayan sido procesadas."
        ),
        "pt": (
            "O LLM retornou {returned} entradas normalizadas;"
            " esperavam-se {expected}."
            " Algumas referências podem não ter sido processadas."
        ),
        "en": (
            "LLM returned {returned} normalized entries;"
            " expected {expected}."
            " Some references may not have been processed."
        ),
    },
)

register(
    "warn.self_citation_suspected",
    {
        "es": ("La referencia podría ser una auto-cita no reconocida."),
        "pt": "A referência pode ser uma autocitação não reconhecida.",
        "en": "The reference may be an unacknowledged self-citation.",
    },
)

register(
    "warn.future_year",
    {
        "es": ("La referencia cita el año {year}, que es posterior al año actual."),
        "pt": ("A referência cita o ano {year}, que é posterior ao ano atual."),
        "en": ("The reference cites year {year}, which is after the current year."),
    },
)

register(
    "warn.suspicious_doi_pattern",
    {
        "es": "El DOI '{doi}' presenta un patrón atípico: {detail}.",
        "pt": "O DOI '{doi}' apresenta um padrão atípico: {detail}.",
        "en": "DOI '{doi}' shows an atypical pattern: {detail}.",
    },
)
