"use client";

import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import type { Locale } from "@/i18n/config";

interface Props {
  locale: Locale;
  messages: AbstractIntlMessages;
  now?: Date;
  children: React.ReactNode;
}

export function LocaleProvider({ locale, messages, now, children }: Props) {
  return (
    <NextIntlClientProvider locale={locale} messages={messages} now={now} timeZone="America/Bogota">
      {children}
    </NextIntlClientProvider>
  );
}
