import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { SOCIAL_NETWORKS } from "../../shared/api/types";
import { Notice } from "../../shared/ui/primitives";
import { usePublicCompany } from "./api";

/** Portada mínima del negocio (spec §13): quién es, dónde está y el botón de reservar. */
export default function LandingPage() {
  const { t } = useTranslation();
  const company = usePublicCompany().data;
  if (!company) return null;
  const place = [company.address, company.city].filter(Boolean).join(", ");
  const networks = SOCIAL_NETWORKS.filter((key) => company.social_links[key]);

  return (
    <div className="flex flex-col items-center gap-6 py-6 text-center">
      {company.logo?.medium && (
        <img src={company.logo.medium} alt="" className="size-32 rounded-2xl object-cover shadow" />
      )}
      <div>
        <h1 className="text-3xl font-semibold">{company.name}</h1>
        {place && <p className="mt-2 opacity-80">{place}</p>}
        {company.phone && (
          <p className="mt-1">
            <a href={`tel:${company.phone}`} className="underline">
              {company.phone}
            </a>
          </p>
        )}
      </div>
      {company.booking_enabled ? (
        <Link
          to="/reservar"
          className="inline-flex min-h-14 items-center rounded-2xl bg-[var(--color-primary)] px-8 text-lg font-semibold text-[var(--color-background)] transition-transform focus-visible:outline-2 active:scale-[0.98]"
        >
          {t("booking.cta")}
        </Link>
      ) : (
        <Notice tone="warning">{t("booking.disabled")}</Notice>
      )}
      {networks.length > 0 && (
        <ul className="flex flex-wrap justify-center gap-3 text-sm">
          {networks.map((key) => (
            <li key={key}>
              <a
                href={company.social_links[key]}
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                {t(`catalog.company.networks.${key}`)}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
