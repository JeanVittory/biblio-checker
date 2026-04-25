import { AlertTriangle, Bot, BookX } from "lucide-react";
import { getTranslations } from "next-intl/server";

/**
 * Problem section for the landing page.
 * Spec: landing-page/05-problem-section
 *
 * Server component — displays three fact cards explaining the bibliographic
 * deep fake problem.
 */
export async function ProblemSection() {
  const t = await getTranslations();

  const facts = [
    {
      icon: Bot,
      titleKey: "landing.problem.fact1.title" as const,
      descKey: "landing.problem.fact1.desc" as const,
      iconClass: "text-amber-500",
    },
    {
      icon: AlertTriangle,
      titleKey: "landing.problem.fact2.title" as const,
      descKey: "landing.problem.fact2.desc" as const,
      iconClass: "text-amber-500",
    },
    {
      icon: BookX,
      titleKey: "landing.problem.fact3.title" as const,
      descKey: "landing.problem.fact3.desc" as const,
      iconClass: "text-red-500",
    },
  ] as const;

  return (
    <section className="py-16 sm:py-20">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section heading */}
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {t("landing.problem.title" as Parameters<typeof t>[0])}
          </h2>
          <p className="mt-4 text-muted">
            {t("landing.problem.subtitle" as Parameters<typeof t>[0])}
          </p>
        </div>

        {/* Three fact cards — 3-column grid on desktop, stacked on mobile */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {facts.map(({ icon: Icon, titleKey, descKey, iconClass }) => (
            <div
              key={titleKey}
              className="rounded-lg border border-border bg-surface p-6"
            >
              <Icon
                className={`mb-4 h-8 w-8 ${iconClass}`}
                aria-hidden="true"
              />
              <h3 className="mb-2 text-lg font-semibold text-foreground">
                {t(titleKey)}
              </h3>
              <p className="text-sm leading-relaxed text-muted">
                {t(descKey)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
