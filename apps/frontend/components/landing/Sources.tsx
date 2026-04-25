import { Globe, Globe2, FileText, BookOpen } from "lucide-react";
import { getTranslations } from "next-intl/server";

/**
 * Sources section for the landing page.
 * Spec: landing-page/09-sources-section
 *
 * Server component — displays four academic database source cards.
 * No external logos for v1 — plain text names only.
 */
export async function Sources() {
  const t = await getTranslations();

  const sources = [
    {
      icon: Globe,
      name: "OpenAlex",
      descKey: "landing.sources.openalex.desc" as const,
    },
    {
      icon: Globe2,
      name: "SciELO",
      descKey: "landing.sources.scielo.desc" as const,
    },
    {
      icon: FileText,
      name: "arXiv",
      descKey: "landing.sources.arxiv.desc" as const,
    },
    {
      icon: BookOpen,
      name: "OpenLibrary",
      descKey: "landing.sources.openlibrary.desc" as const,
    },
  ] as const;

  return (
    <section className="py-16 sm:py-20">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section heading */}
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {t("landing.sources.title" as Parameters<typeof t>[0])}
          </h2>
          <p className="mt-4 text-muted">
            {t("landing.sources.subtitle" as Parameters<typeof t>[0])}
          </p>
        </div>

        {/*
         * Source cards:
         *   mobile  → 1 column (stacked)
         *   tablet  → 2-column grid
         *   desktop → 4-column row
         */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {sources.map(({ icon: Icon, name, descKey }) => (
            <div
              key={name}
              className="rounded-lg border border-border bg-surface p-4"
            >
              <Icon className="mb-3 h-6 w-6 text-muted" aria-hidden="true" />
              <h3 className="mb-1 font-semibold text-foreground">{name}</h3>
              <p className="text-sm text-muted">{t(descKey)}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
