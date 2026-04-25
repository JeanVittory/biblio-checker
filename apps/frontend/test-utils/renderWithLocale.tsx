import { render, type RenderOptions } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import en from "@/messages/en.json";
import es from "@/messages/es.json";
import pt from "@/messages/pt.json";
import type { Locale } from "@/i18n/config";

const CATALOGS = { en, es, pt } as const;

export function renderWithLocale(
  ui: ReactNode,
  locale: Locale = "es",
  options?: Omit<RenderOptions, "wrapper">
) {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGS[locale]}>
      {ui}
    </NextIntlClientProvider>,
    options
  );
}
