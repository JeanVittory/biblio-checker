import { getRequestConfig } from "next-intl/server";
import { detectLocale } from "./detect";
import type { AbstractIntlMessages } from "next-intl";

export default getRequestConfig(async () => {
  const locale = await detectLocale();
  const messages = (
    await import(`../messages/${locale}.json`)
  ).default as AbstractIntlMessages;

  return {
    locale,
    messages,
    // ICU formatting config — single global date format to keep diffs small.
    formats: {
      dateTime: {
        short: {
          day: "numeric",
          month: "short",
          year: "numeric",
        },
      },
    },
    // Prevent crashes on missing keys; log instead.
    onError(err) {
      if (process.env.NODE_ENV !== "production") {
        console.warn("[i18n]", err.code, err.message);
      }
    },
    getMessageFallback({ key, namespace }) {
      const path = [namespace, key].filter(Boolean).join(".");
      return process.env.NODE_ENV !== "production" ? `[i18n:${path}]` : "";
    },
  };
});
