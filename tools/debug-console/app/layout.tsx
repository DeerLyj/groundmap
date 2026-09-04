import "./globals.css";
import type { Metadata } from "next";
import { t } from "@/lib/i18n";
import { getServerLocale } from "@/lib/server-locale";
import { LocaleProvider } from "@/lib/i18n-client";

export function generateMetadata(): Metadata {
  const locale = getServerLocale();
  return {
    title: t("meta.title", locale),
    description: t("meta.description", locale),
  };
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = getServerLocale();
  return (
    <html lang={locale}>
      <body>
        <div className="grain" aria-hidden />
        <div className="scanlines" aria-hidden />
        <LocaleProvider initial={locale}>{children}</LocaleProvider>
      </body>
    </html>
  );
}
