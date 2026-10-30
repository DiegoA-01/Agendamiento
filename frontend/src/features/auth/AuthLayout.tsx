import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { Card } from "../../shared/ui/primitives";

/** Tarjeta centrada para login, recuperación y cambio de contraseña. */
export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center gap-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <span className="text-lg font-semibold text-slate-900">{t("app.name")}</span>
        <LanguageSwitcher />
      </div>
      <Card className="flex flex-col gap-5 p-6">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {children}
      </Card>
    </main>
  );
}
