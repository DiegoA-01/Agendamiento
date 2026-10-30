import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../shared/api/client";
import { applyServerErrors, describeError } from "../../shared/api/errors";
import { Button, Notice, TextField } from "../../shared/ui/primitives";
import {
  forgotSchema,
  resetPasswordSchema,
  type ForgotValues,
  type ResetPasswordValues,
} from "../platform/schemas";
import { AuthLayout } from "./AuthLayout";

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const form = useForm<ForgotValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: "" },
  });
  const send = useMutation({
    mutationFn: (values: ForgotValues) =>
      api<void>("/api/v1/auth/password-reset/", { method: "POST", body: values }),
  });

  return (
    <AuthLayout title={t("auth.forgotTitle")}>
      {send.isSuccess ? (
        <Notice tone="success">{t("auth.forgotSent")}</Notice>
      ) : (
        <>
          <p className="text-sm text-slate-600">{t("auth.forgotIntro")}</p>
          {send.isError && <Notice tone="danger">{describeError(t, send.error)}</Notice>}
          <form
            onSubmit={form.handleSubmit((values) => send.mutate(values))}
            noValidate
            className="flex flex-col gap-4"
          >
            <TextField
              label={t("auth.email")}
              type="email"
              autoComplete="username"
              error={form.formState.errors.email?.message}
              {...form.register("email")}
            />
            <Button type="submit" disabled={send.isPending}>
              {t("auth.sendLink")}
            </Button>
          </form>
        </>
      )}
      <Link to="/login" className="text-sm text-slate-700 underline">
        {t("auth.backToLogin")}
      </Link>
    </AuthLayout>
  );
}

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const [message, setMessage] = useState<string | null>(null);

  const form = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { new_password: "", repeat_password: "" },
  });
  const { errors } = form.formState;

  const reset = useMutation({
    mutationFn: (values: ResetPasswordValues) =>
      api<void>("/api/v1/auth/password-reset/confirm/", {
        method: "POST",
        body: { uid, token, new_password: values.new_password },
      }),
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, ["new_password"])) {
        setMessage(describeError(t, error));
      }
    },
  });

  return (
    <AuthLayout title={t("auth.resetTitle")}>
      {!uid || !token ? (
        <Notice tone="danger">{t("auth.resetMissingLink")}</Notice>
      ) : reset.isSuccess ? (
        <Notice tone="success">{t("auth.resetDone")}</Notice>
      ) : (
        <form
          onSubmit={form.handleSubmit((values) => reset.mutate(values))}
          noValidate
          className="flex flex-col gap-4"
        >
          {message && <Notice tone="danger">{message}</Notice>}
          <TextField
            label={t("auth.newPassword")}
            type="password"
            autoComplete="new-password"
            error={errors.new_password?.message}
            {...form.register("new_password")}
          />
          <TextField
            label={t("auth.repeatPassword")}
            type="password"
            autoComplete="new-password"
            error={errors.repeat_password?.message}
            {...form.register("repeat_password")}
          />
          <Button type="submit" disabled={reset.isPending}>
            {t("auth.resetSubmit")}
          </Button>
        </form>
      )}
      <Link to="/login" className="text-sm text-slate-700 underline">
        {t("auth.backToLogin")}
      </Link>
    </AuthLayout>
  );
}
