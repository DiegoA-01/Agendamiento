import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import type { Me, TwoFactorConfirmed, TwoFactorSetup } from "../../shared/api/types";
import { isPlatformHost } from "../../shared/host";
import { Button, CopyButton, Notice, TextField } from "../../shared/ui/primitives";
import { loginSchema, type LoginValues } from "../platform/schemas";
import { AuthLayout } from "./AuthLayout";
import { RecoveryCodes } from "./RecoveryCodes";
import { ME_KEY, homePathFor } from "./useMe";

type Step = "credentials" | "code" | "setup";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("credentials");
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  // Al activar el 2FA se muestran los códigos de recuperación antes de entrar (pormejorar §2).
  const [issued, setIssued] = useState<TwoFactorConfirmed | null>(null);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", totp_code: "" },
  });
  const { errors } = form.formState;

  function finish(me: Me) {
    queryClient.setQueryData(ME_KEY, me);
    navigate(me.must_change_password ? "/cambiar-clave" : homePathFor(me), { replace: true });
  }

  const submit = useMutation({
    mutationFn: (values: LoginValues) => {
      const credentials = { email: values.email, password: values.password };
      if (step === "setup") {
        return api<TwoFactorConfirmed>("/api/v1/auth/2fa/confirm/", {
          method: "POST",
          body: { ...credentials, code: values.totp_code },
        });
      }
      return api<Me>("/api/v1/auth/login/", {
        method: "POST",
        body: { ...credentials, totp_code: values.totp_code },
      });
    },
    onSuccess: (me: Me | TwoFactorConfirmed) => {
      if ("recovery_codes" in me && me.recovery_codes.length > 0) setIssued(me);
      else finish(me);
    },
    onError: async (error, values) => {
      setMessage(null);
      if (error instanceof ApiError && error.code === "two_factor_required") {
        setStep("code");
        return;
      }
      if (error instanceof ApiError && error.code === "two_factor_setup_required") {
        try {
          const started = await api<TwoFactorSetup>("/api/v1/auth/2fa/setup/", {
            method: "POST",
            body: { email: values.email, password: values.password },
          });
          setSetup(started);
          setStep("setup");
        } catch (setupError) {
          setMessage(describeError(t, setupError));
        }
        return;
      }
      setMessage(describeError(t, error));
    },
  });

  function onSubmit(values: LoginValues) {
    if (step !== "credentials" && !values.totp_code.trim()) {
      form.setError("totp_code", { type: "required", message: "codeRequired" });
      return;
    }
    submit.mutate(values);
  }

  function backToCredentials() {
    setStep("credentials");
    setSetup(null);
    setMessage(null);
    form.setValue("totp_code", "");
    form.clearErrors();
  }

  const locked = step !== "credentials";
  const title =
    step === "setup"
      ? t("auth.setupTitle")
      : isPlatformHost()
        ? t("auth.adminLoginTitle")
        : t("auth.loginTitle");

  if (issued) {
    return (
      <AuthLayout title={t("auth.recoveryTitle")}>
        <RecoveryCodes
          codes={issued.recovery_codes}
          email={issued.user.email}
          onDone={() => finish(issued)}
        />
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title={title}>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        {message && <Notice tone="danger">{message}</Notice>}

        <TextField
          label={t("auth.email")}
          type="email"
          autoComplete="username"
          readOnly={locked}
          error={errors.email?.message}
          {...form.register("email")}
        />
        <TextField
          label={t("auth.password")}
          type="password"
          autoComplete="current-password"
          readOnly={locked}
          error={errors.password?.message}
          {...form.register("password")}
        />

        {step === "setup" && setup && (
          <div className="flex flex-col gap-3 rounded-lg bg-slate-50 p-4 text-sm">
            <p>{t("auth.setupIntro")}</p>
            <div className="flex flex-wrap items-center gap-3">
              <code
                aria-label={t("auth.secretLabel")}
                className="rounded bg-white px-3 py-2 font-mono text-base tracking-wider break-all"
              >
                {setup.secret}
              </code>
              <CopyButton value={setup.secret} />
            </div>
            <p>{t("auth.setupAfter")}</p>
          </div>
        )}

        {locked && (
          <TextField
            label={t("auth.codeLabel")}
            // Al entrar también vale un código de recuperación (letras y guion); al activar, no.
            hint={step === "code" ? t("auth.codeHintRecovery") : t("auth.codeHint")}
            inputMode={step === "code" ? "text" : "numeric"}
            autoCapitalize="none"
            autoComplete="one-time-code"
            maxLength={step === "code" ? 13 : 7}
            autoFocus
            error={errors.totp_code?.message}
            {...form.register("totp_code")}
          />
        )}

        <Button type="submit" disabled={submit.isPending}>
          {submit.isPending
            ? t("auth.signingIn")
            : step === "setup"
              ? t("auth.setupConfirm")
              : t("auth.signIn")}
        </Button>
        {locked && (
          <Button variant="ghost" onClick={backToCredentials}>
            {t("common.back")}
          </Button>
        )}
      </form>
      <Link to="/recuperar" className="text-sm text-slate-700 underline">
        {t("auth.forgot")}
      </Link>
    </AuthLayout>
  );
}
