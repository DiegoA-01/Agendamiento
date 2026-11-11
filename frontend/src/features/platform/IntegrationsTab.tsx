import { useTranslation } from "react-i18next";
import { describeError } from "../../shared/api/errors";
import { formatDateTime } from "../../shared/format";
import { Badge, Card, ErrorBox, Loading, Notice } from "../../shared/ui/primitives";
import { useTenantIntegrations } from "./api";

/** Configuración y actividad de notificaciones por negocio (S11). */
export function IntegrationsTab({ tenantId }: { tenantId: string }) {
  const { t, i18n } = useTranslation();
  const integrations = useTenantIntegrations(tenantId);
  if (integrations.isPending) return <Loading />;
  if (integrations.isError) {
    return (
      <ErrorBox
        message={describeError(t, integrations.error)}
        onRetry={() => void integrations.refetch()}
      />
    );
  }
  const data = integrations.data;
  return (
    <div className="min-w-0 space-y-4">
      <p className="text-sm text-slate-600">
        {t("tenants.integrations.window", { days: data.window_days })}
      </p>
      <div className="grid min-w-0 gap-3 lg:grid-cols-2">
        {data.channels.map((channel) => (
          <Card key={channel.channel} className="min-w-0 space-y-3">
            <h2 className="font-semibold">{t(`tenants.integrations.${channel.channel}`)}</h2>
            {channel.channel === "whatsapp" ? (
              <>
                <p className="text-sm">
                  {t("tenants.integrations.planEnabled")}:{" "}
                  <Badge tone={data.whatsapp_enabled ? "success" : "neutral"}>
                    {t(`tenants.integrations.${data.whatsapp_enabled ? "yes" : "no"}`)}
                  </Badge>
                </p>
                <p className="text-sm">
                  {t("tenants.integrations.provider")}:{" "}
                  {t(`tenants.integrations.providers.${data.whatsapp_provider}`)}
                </p>
                <p className="text-sm">
                  {t("tenants.integrations.configured")}:{" "}
                  {t(`tenants.integrations.${data.whatsapp_configured ? "yes" : "no"}`)}
                </p>
                {data.whatsapp_provider === "cloud_api" && !data.whatsapp_configured && (
                  <Notice tone="warning">{t("tenants.integrations.missingConfig")}</Notice>
                )}
              </>
            ) : (
              <>
                <p className="text-sm break-words">
                  {t("tenants.integrations.emailBackend")}: {data.email_backend}
                </p>
                {(data.email_backend === "console" || data.email_backend === "locmem") && (
                  <Notice>{t("tenants.integrations.emailSimulated")}</Notice>
                )}
              </>
            )}
            <dl className="grid grid-cols-3 gap-3">
              {(["sent", "failed", "queued"] as const).map((status) => (
                <div key={status} className="min-w-0">
                  <dt className="text-sm text-slate-600">{t(`tenants.integrations.${status}`)}</dt>
                  <dd className="text-xl font-semibold break-words tabular-nums">
                    {channel[status].toLocaleString(i18n.language)}
                  </dd>
                </div>
              ))}
            </dl>
            <p className="text-sm">
              {t("tenants.integrations.lastSent")}:{" "}
              {channel.last_sent_at
                ? formatDateTime(channel.last_sent_at, i18n.language)
                : t("tenants.integrations.never")}
            </p>
          </Card>
        ))}
      </div>
      <Card className="min-w-0">
        <h2 className="mb-3 font-semibold">{t("tenants.integrations.failures")}</h2>
        {data.recent_failures.length === 0 ? (
          <p className="text-sm text-slate-600">{t("tenants.integrations.empty")}</p>
        ) : (
          <div
            className="max-w-full overflow-x-auto"
            role="region"
            aria-label={t("tenants.integrations.failures")}
            tabIndex={0}
          >
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  {["date", "kind", "channel", "recipient", "attempts", "error"].map((column) => (
                    <th key={column} scope="col" className="px-3 py-2">
                      {t(`tenants.integrations.${column}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.recent_failures.map((failure, index) => (
                  <tr key={index} className="border-t border-slate-200 align-top">
                    <td className="px-3 py-2 whitespace-nowrap">
                      {formatDateTime(failure.created_at, i18n.language)}
                    </td>
                    <td className="px-3 py-2">{t(`tenants.integrations.kinds.${failure.kind}`)}</td>
                    <td className="px-3 py-2">{t(`tenants.integrations.${failure.channel}`)}</td>
                    <td className="px-3 py-2">{failure.to}</td>
                    <td className="px-3 py-2">{failure.attempts.toLocaleString(i18n.language)}</td>
                    <td className="min-w-48 px-3 py-2 break-all">{failure.error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
