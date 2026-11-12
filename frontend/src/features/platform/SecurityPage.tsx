import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import { Button, Card, Notice, PageHeader, TextField } from "../../shared/ui/primitives";
import { RecoveryCodes } from "../auth/RecoveryCodes";
import { ME_KEY, useMe } from "../auth/useMe";

const LOW = 3;

/** Seguridad de la cuenta del Super Admin: cuántos códigos de recuperación quedan y cómo generar
 *  otros (pormejorar §2). Pide la contraseña y un código de la app aunque la sesión esté abierta. */
export function SecurityPage() {
  const { t } = useTranslation();
  const me = useMe().data;
  const queryClient = useQueryClient();
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");

  const regenerate = useMutation({
    mutationFn: () =>
      api<{ recovery_codes: string[] }>("/api/v1/auth/2fa/recovery-codes/", {
        method: "POST",
        body: { password, code },
      }),
    onSuccess: () => {
      setPassword("");
      setCode("");
    },
  });

  if (!me) return null;
  const left = me.recovery_codes_left;

  if (regenerate.isSuccess) {
    return (
      <>
        <PageHeader title={t("auth.recoveryTitle")} />
        <Card className="max-w-xl">
          <RecoveryCodes
            codes={regenerate.data.recovery_codes}
            email={me.user.email}
            onDone={() => {
              regenerate.reset();
              void queryClient.invalidateQueries({ queryKey: ME_KEY });
            }}
          />
        </Card>
      </>
    );
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    regenerate.mutate();
  }

  return (
    <>
      <PageHeader title={t("security.title")} description={t("security.intro")} />
      <div className="flex max-w-xl flex-col gap-4">
        {!me.two_factor_enabled ? (
          <Notice tone="warning">{t("security.twoFactorOff")}</Notice>
        ) : (
          <Notice tone={left <= LOW ? "warning" : "info"}>
            {left === 0 ? t("security.none") : t("security.left", { count: left })}
            {left > 0 && left <= LOW && ` ${t("security.low")}`}
          </Notice>
        )}
        {me.two_factor_enabled && (
          <Card>
            <form onSubmit={submit} noValidate className="flex flex-col gap-4">
              <h2 className="font-semibold text-slate-900">{t("security.regenerateTitle")}</h2>
              <p className="text-sm text-slate-700">{t("security.regenerateIntro")}</p>
              {regenerate.isError && (
                <Notice tone="danger">{describeError(t, regenerate.error)}</Notice>
              )}
              <TextField
                label={t("auth.password")}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <TextField
                label={t("auth.codeLabel")}
                hint={t("auth.codeHint")}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={7}
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
              <Button
                type="submit"
                disabled={regenerate.isPending || !password || code.trim().length < 6}
              >
                {t("security.regenerateSubmit")}
              </Button>
            </form>
          </Card>
        )}
      </div>
    </>
  );
}
