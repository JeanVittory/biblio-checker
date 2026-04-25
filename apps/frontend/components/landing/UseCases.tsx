import { GraduationCap, BookOpen, Building2 } from "lucide-react";
import { getTranslations } from "next-intl/server";

/**
 * Use Cases section for the landing page.
 * Spec: landing-page/08-use-cases
 *
 * Server component — displays three persona cards.
 * The institution card includes a "Coming soon" badge.
 */
export async function UseCases() {
  const t = await getTranslations();

  return (
    <section className="py-16 sm:py-20">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section heading */}
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {t("landing.useCases.title" as Parameters<typeof t>[0])}
          </h2>
        </div>

        {/* Three persona cards — 3-column grid on desktop, stacked on mobile */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* Persona 1 — Professors / Reviewers */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <GraduationCap
              className="mb-4 h-8 w-8 text-accent"
              aria-hidden="true"
            />
            <h3 className="mb-2 text-lg font-semibold text-foreground">
              {t("landing.useCases.professor.title" as Parameters<typeof t>[0])}
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              {t("landing.useCases.professor.desc" as Parameters<typeof t>[0])}
            </p>
          </div>

          {/* Persona 2 — Students / Researchers */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <BookOpen
              className="mb-4 h-8 w-8 text-accent"
              aria-hidden="true"
            />
            <h3 className="mb-2 text-lg font-semibold text-foreground">
              {t("landing.useCases.student.title" as Parameters<typeof t>[0])}
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              {t("landing.useCases.student.desc" as Parameters<typeof t>[0])}
            </p>
          </div>

          {/* Persona 3 — Institutions (coming soon) */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <Building2
              className="mb-4 h-8 w-8 text-accent"
              aria-hidden="true"
            />
            <div className="mb-2 flex items-center gap-2">
              <h3 className="text-lg font-semibold text-foreground">
                {t("landing.useCases.institution.title" as Parameters<typeof t>[0])}
              </h3>
              {/* "Coming soon" badge — visible text, not color-only */}
              <span className="rounded-full border border-border px-2 py-0.5 text-xs font-medium text-muted">
                {t("landing.useCases.comingSoon" as Parameters<typeof t>[0])}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-muted">
              {t("landing.useCases.institution.desc" as Parameters<typeof t>[0])}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
