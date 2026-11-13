import { useTranslation } from "react-i18next";

/** Marca de la plataforma: la "A" en verde metalizado y el nombre. Va dentro de `.platform`. */
export function BrandMark({ size = "md" }: { size?: "md" | "lg" }) {
  const { t } = useTranslation();
  const box = size === "lg" ? "size-12 text-xl" : "size-10 text-lg";
  return (
    <span className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className={`metal flex ${box} items-center justify-center rounded-xl font-bold`}
      >
        A
      </span>
      <span className={`${size === "lg" ? "text-2xl" : "text-xl"} font-bold tracking-tight`}>
        {t("app.name")}
      </span>
    </span>
  );
}
