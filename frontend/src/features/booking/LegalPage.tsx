import { useTranslation } from "react-i18next";
import { EmptyState } from "../../shared/ui/primitives";
import { usePublicCompany } from "./api";

export type LegalKey = "terms" | "privacy" | "cookies";

const FIELD = { terms: "terms_html", privacy: "privacy_html", cookies: "cookies_html" } as const;

/** Texto legal del negocio. El HTML ya viene limpio del servidor (`company/sanitize.py`: solo
 *  formato básico y enlaces seguros), por eso se puede insertar tal cual. */
export default function LegalPage({ page }: { page: LegalKey }) {
  const { t } = useTranslation();
  const company = usePublicCompany().data;
  if (!company) return null;
  const html = company[FIELD[page]];

  return (
    <article className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t(`booking.pages.${page}.title`)}</h1>
      {html.trim() ? (
        <div
          className="legal-text flex flex-col gap-3 leading-relaxed [&_a]:underline [&_h2]:text-xl [&_h2]:font-semibold [&_h3]:text-lg [&_h3]:font-semibold [&_ol]:list-decimal [&_ol]:pl-6 [&_ul]:list-disc [&_ul]:pl-6"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : (
        <EmptyState>{t("booking.legalEmpty", { name: company.name })}</EmptyState>
      )}
    </article>
  );
}
