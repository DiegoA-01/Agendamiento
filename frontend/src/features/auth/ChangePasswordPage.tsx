import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../../shared/api/client";
import { applyServerErrors, describeError } from "../../shared/api/errors";
import type { Me } from "../../shared/api/types";
import { Button, Notice, TextField } from "../../shared/ui/primitives";
import { changePasswordSchema, type ChangePasswordValues } from "../platform/schemas";
import { AuthLayout } from "./AuthLayout";
import { ME_KEY, homePathFor, useMe } from "./useMe";

export function ChangePasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const me = useMe();
  const [message, setMessage] = useState<string | null>(null);

  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "", repeat_password: "" },
  });
  const { errors } = form.formState;

  const change = useMutation({
    mutationFn: (values: ChangePasswordValues) =>
      api<Me>("/api/v1/auth/password-change/", {
        method: "POST",
        body: { current_password: values.current_password, new_password: values.new_password },
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(ME_KEY, updated);
      navigate(homePathFor(updated), { replace: true });
    },
    onError: (error) => {
      setMessage(null);
      if (error instanceof ApiError && error.code === "invalid_current_password") {
        form.setError("current_password", { type: "server", message: describeError(t, error) });
      } else if (!applyServerErrors(error, form.setError, ["new_password"])) {
        setMessage(describeError(t, error));
      }
    },
  });

  return (
    <AuthLayout title={t("auth.changeTitle")}>
      {me.data?.must_change_password && (
        <Notice tone="warning">{t("auth.changeForcedIntro")}</Notice>
      )}
      {message && <Notice tone="danger">{message}</Notice>}
      <form
        onSubmit={form.handleSubmit((values) => change.mutate(values))}
        noValidate
        className="flex flex-col gap-4"
      >
        <TextField
          label={t("auth.currentPassword")}
          type="password"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...form.register("current_password")}
        />
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
        <Button type="submit" disabled={change.isPending}>
          {t("auth.changeSubmit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
