import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, CopyButton, Notice } from "../../shared/ui/primitives";
import { recoveryCodesText } from "./recoveryFile";

/** Muestra los códigos de recuperación una sola vez (pormejorar §2): se pueden copiar o
 *  descargar, y no se sigue hasta confirmar que se guardaron. */
export function RecoveryCodes({
  codes,
  email,
  onDone,
}: {
  codes: string[];
  email: string;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const [saved, setSaved] = useState(false);
  const text = recoveryCodesText(codes, {
    title: t("auth.recoveryFileTitle"),
    note: t("auth.recoveryFileNote"),
    email,
    issuedAt: new Date(),
  });

  function download() {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "agenda-codigos-recuperacion.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col gap-4">
      <Notice tone="warning">{t("auth.recoveryIntro")}</Notice>
      <ol
        aria-label={t("auth.recoveryListLabel")}
        className="grid grid-cols-2 gap-2 rounded-lg bg-slate-50 p-4 font-mono text-base tracking-wider"
      >
        {codes.map((code) => (
          <li key={code} className="text-center">
            {code}
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-2">
        <CopyButton value={codes.join("\n")} label={t("auth.recoveryCopy")} />
        <Button variant="secondary" className="min-h-8 px-3 text-xs" onClick={download}>
          {t("auth.recoveryDownload")}
        </Button>
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          className="mt-0.5 size-4"
          checked={saved}
          onChange={(event) => setSaved(event.target.checked)}
        />
        <span>{t("auth.recoverySaved")}</span>
      </label>
      <Button disabled={!saved} onClick={onDone}>
        {t("auth.recoveryContinue")}
      </Button>
    </div>
  );
}
