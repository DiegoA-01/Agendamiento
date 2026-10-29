import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { fetchHealth } from "../shared/api/client";
import { LanguageSwitcher } from "../shared/ui/LanguageSwitcher";

export function HomePage() {
  const { t } = useTranslation();
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth });

  const status = health.isPending ? "loading" : health.isError ? "error" : "ok";

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col gap-6 p-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("app.name")}</h1>
        <LanguageSwitcher />
      </header>
      <p>{t("home.tagline")}</p>
      <section
        aria-live="polite"
        className="rounded-lg p-4"
        style={{ background: "var(--color-surface)" }}
      >
        <h2 className="font-medium">{t("health.title")}</h2>
        <p data-testid="health-status">{t(`health.${status}`)}</p>
      </section>
    </main>
  );
}
