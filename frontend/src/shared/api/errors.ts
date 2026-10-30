import type { TFunction } from "i18next";
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { ApiError } from "./client";

/** Texto para mostrar al usuario según el `code` estable de la API (nunca según `detail`). */
export function describeError(t: TFunction, error: unknown): string {
  if (error instanceof ApiError) {
    const key = `errors.${error.code}`;
    return t(key, { defaultValue: t("errors.unknown") });
  }
  return t("errors.unknown");
}

/** Mensaje de un campo: los de Zod son claves de i18n; los del servidor, texto ya escrito. */
export function fieldMessage(t: TFunction, message: string | undefined): string | undefined {
  if (!message) return undefined;
  for (const namespace of ["errors", "common", "auth"]) {
    const key = `${namespace}.${message}`;
    if (t(key, { defaultValue: "" })) return t(key);
  }
  return message;
}

/** Marca en el formulario los campos que el servidor rechazó. Devuelve true si marcó alguno. */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  allowed: readonly string[],
): boolean {
  if (!(error instanceof ApiError)) return false;
  let marked = false;
  for (const [field, messages] of Object.entries(error.fields)) {
    if (allowed.includes(field)) {
      setError(field as Path<T>, { type: "server", message: messages.join(" ") });
      marked = true;
    }
  }
  return marked;
}
