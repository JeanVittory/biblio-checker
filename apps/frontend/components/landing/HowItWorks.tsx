import { Upload, Search, BarChart3 } from "lucide-react";
import { getTranslations } from "next-intl/server";

/**
 * How It Works section for the landing page.
 * Spec: landing-page/06-how-it-works
 *
 * Server component — displays three numbered steps explaining the product
 * workflow: upload, verify, get score.
 */
export async function HowItWorks() {
  const t = await getTranslations();

  const steps = [
    {
      number: "1",
      icon: Upload,
      titleKey: "landing.howItWorks.step1.title" as const,
      descKey: "landing.howItWorks.step1.desc" as const,
    },
    {
      number: "2",
      icon: Search,
      titleKey: "landing.howItWorks.step2.title" as const,
      descKey: "landing.howItWorks.step2.desc" as const,
    },
    {
      number: "3",
      icon: BarChart3,
      titleKey: "landing.howItWorks.step3.title" as const,
      descKey: "landing.howItWorks.step3.desc" as const,
    },
  ] as const;

  return (
    <section className="py-16 sm:py-20">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section heading */}
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {t("landing.howItWorks.title" as Parameters<typeof t>[0])}
          </h2>
        </div>

        {/* Three steps — horizontal on desktop, stacked on mobile */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {steps.map(({ number, icon: Icon, titleKey, descKey }) => (
            <div key={number} className="flex flex-col items-center text-center">
              {/* Step number — visually distinct with brand gradient */}
              <span
                className="mb-4 text-5xl font-bold bg-clip-text text-transparent"
                style={{
                  backgroundImage:
                    "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
                }}
                aria-hidden="true"
              >
                {number}
              </span>

              {/* Icon */}
              <Icon className="mb-3 h-8 w-8 text-muted" aria-hidden="true" />

              {/* Step title */}
              <h3 className="mb-2 text-lg font-semibold text-foreground">
                {t(titleKey)}
              </h3>

              {/* Description */}
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
