import { useTranslation } from "react-i18next";
import { describeError } from "../../shared/api/errors";
import { formatDateTime } from "../../shared/format";
import { Card, ErrorBox, Loading } from "../../shared/ui/primitives";
import { useTenantUsage } from "./api";

/** Uso del sistema por negocio (S10): sirve para ver quién usa la plataforma y quién no. */
export function UsageTab({ tenantId }: { tenantId: string }) {
  const { t, i18n } = useTranslation();
  const usage = useTenantUsage(tenantId);
  if (usage.isPending) return <Loading />;
  if (usage.isError) {
    return (
      <ErrorBox message={describeError(t, usage.error)} onRetry={() => void usage.refetch()} />
    );
  }
  const data = usage.data;
  const number = (value: number) => value.toLocaleString(i18n.language);
  const items: [string, string][] = [
    [
      t("tenants.usage.appointmentsRecent", { days: data.window_days }),
      number(data.appointments_recent),
    ],
    [
      t("tenants.usage.webBookingsRecent", { days: data.window_days }),
      number(data.web_bookings_recent),
    ],
    [t("tenants.usage.completedRecent", { days: data.window_days }), number(data.completed_recent)],
    [t("tenants.usage.cancelledRecent", { days: data.window_days }), number(data.cancelled_recent)],
    [t("tenants.usage.appointmentsTotal"), number(data.appointments_total)],
    [t("tenants.usage.customersTotal"), number(data.customers_total)],
    [t("tenants.usage.usersActive"), number(data.users_active)],
    [
      t("tenants.usage.lastLogin"),
      data.last_login ? formatDateTime(data.last_login, i18n.language) : t("tenants.usage.never"),
    ],
  ];
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {items.map(([label, value]) => (
          <Card key={label} className="min-w-0 p-4">
            <dt className="text-sm text-slate-600">{label}</dt>
            <dd className="mt-1 text-xl font-semibold break-words tabular-nums">{value}</dd>
          </Card>
        ))}
      </dl>
      <p className="text-xs text-slate-500">
        {t("tenants.usage.note", { days: data.window_days })}
      </p>
    </div>
  );
}
