import { useId, useState, type ComponentProps, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { fieldMessage } from "../api/errors";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: "bg-slate-900 text-white hover:bg-slate-700 disabled:bg-slate-400",
  secondary:
    "border border-slate-300 bg-white text-slate-900 hover:bg-slate-50 disabled:opacity-50",
  danger: "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-300",
  ghost: "text-slate-700 hover:bg-slate-100 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ComponentProps<"button"> & { variant?: ButtonVariant }) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed ${BUTTON_STYLES[variant]} ${className}`}
      {...props}
    />
  );
}

interface FieldShellProps {
  label: string;
  error?: string;
  hint?: string;
  optional?: boolean;
}

const INPUT_STYLES =
  "min-h-10 w-full rounded-lg border bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:text-slate-500";

function FieldShell({
  label,
  error,
  hint,
  optional,
  id,
  children,
}: FieldShellProps & { id: string; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-slate-800">
        {label}
        {optional && (
          <span className="ml-1 font-normal text-slate-500">({t("common.optional")})</span>
        )}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-xs text-slate-600">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-red-700">
          {fieldMessage(t, error)}
        </p>
      )}
    </div>
  );
}

function describedBy(id: string, error?: string, hint?: string) {
  if (error) return `${id}-error`;
  return hint ? `${id}-hint` : undefined;
}

export function TextField({
  label,
  error,
  hint,
  optional,
  className = "",
  ...props
}: ComponentProps<"input"> & FieldShellProps) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} error={error} hint={hint} optional={optional}>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, error, hint)}
        className={`${INPUT_STYLES} ${error ? "border-red-600" : "border-slate-300"} ${className}`}
        {...props}
      />
    </FieldShell>
  );
}

export function SelectField({
  label,
  error,
  hint,
  optional,
  children,
  className = "",
  ...props
}: ComponentProps<"select"> & FieldShellProps) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} error={error} hint={hint} optional={optional}>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, error, hint)}
        className={`${INPUT_STYLES} ${error ? "border-red-600" : "border-slate-300"} ${className}`}
        {...props}
      >
        {children}
      </select>
    </FieldShell>
  );
}

export function CheckboxField({
  label,
  hint,
  ...props
}: Omit<ComponentProps<"input">, "type"> & { label: string; hint?: string }) {
  const id = useId();
  return (
    <div className="flex items-start gap-3">
      <input
        id={id}
        type="checkbox"
        aria-describedby={hint ? `${id}-hint` : undefined}
        className="mt-0.5 size-5 shrink-0 rounded border-slate-400"
        {...props}
      />
      <div className="flex flex-col">
        <label htmlFor={id} className="text-sm font-medium text-slate-800">
          {label}
        </label>
        {hint && (
          <p id={`${id}-hint`} className="text-xs text-slate-600">
            {hint}
          </p>
        )}
      </div>
    </div>
  );
}

export function Card({ className = "", ...props }: ComponentProps<"section">) {
  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}
      {...props}
    />
  );
}

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

const TONES: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-800",
  success: "bg-emerald-100 text-emerald-900",
  warning: "bg-amber-100 text-amber-900",
  danger: "bg-red-100 text-red-900",
  info: "bg-sky-100 text-sky-900",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function Notice({
  tone = "info",
  children,
  role,
}: {
  tone?: Tone;
  children: ReactNode;
  role?: "alert" | "status";
}) {
  return (
    <div
      role={role ?? (tone === "danger" ? "alert" : "status")}
      className={`rounded-lg px-4 py-3 text-sm ${TONES[tone]}`}
    >
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  actions,
  description,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        {description && <p className="mt-1 max-w-prose text-sm text-slate-600">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Loading() {
  const { t } = useTranslation();
  return (
    <p role="status" className="py-10 text-center text-sm text-slate-600">
      {t("common.loading")}
    </p>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <Card className="border-red-200 text-center">
      <p role="alert" className="text-sm font-medium text-red-800">
        {t("common.errorTitle")}: {message}
      </p>
      {onRetry && (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          {t("common.retry")}
        </Button>
      )}
    </Card>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 px-6 py-10 text-center text-sm text-slate-600">
      {children}
    </div>
  );
}

export function CopyButton({ value, label }: { value: string; label?: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Sin permiso de portapapeles: el valor sigue visible para copiarlo a mano.
    }
  }

  return (
    <Button variant="secondary" className="min-h-8 px-3 text-xs" onClick={() => void copy()}>
      <span aria-live="polite">{copied ? t("common.copied") : (label ?? t("common.copy"))}</span>
    </Button>
  );
}
