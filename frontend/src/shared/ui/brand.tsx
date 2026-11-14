import { useTranslation } from "react-i18next";

/** Marca de la plataforma: la "A" en verde metalizado y el nombre. Va dentro de `.platform`. */
export function BrandMark({ size = "md", name }: { size?: "md" | "lg"; name?: string }) {
  const { t } = useTranslation();
  const label = name?.trim() || t("app.name");
  const box = size === "lg" ? "size-12 text-xl" : "size-10 text-lg";
  return (
    <span className="flex min-w-0 items-center gap-3">
      <span
        aria-hidden="true"
        className={`metal flex ${box} shrink-0 items-center justify-center rounded-xl font-bold`}
      >
        {label.charAt(0).toUpperCase()}
      </span>
      <span
        className={`${size === "lg" ? "text-2xl" : "text-xl"} truncate font-bold tracking-tight`}
      >
        {label}
      </span>
    </span>
  );
}
