import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import type { ModuleKey, ModulesInfo, TenantDetail } from "../../shared/api/types";
import { Button, Card, CheckboxField, ErrorBox, Loading, Notice } from "../../shared/ui/primitives";
import { useTenantModules } from "./api";

export function ModulesTab({ tenant }: { tenant: TenantDetail }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const modules = useTenantModules(tenant.id);
  // Lo que el usuario cambió y aún no guardó. null = mostrar lo que tiene el servidor.
  const [draft, setDraft] = useState<Set<ModuleKey> | null>(null);
  const [saved, setSaved] = useState(false);

  const save = useMutation({
    mutationFn: (selected: Set<ModuleKey>) => {
      const all = modules.data?.available ?? [];
      const body = Object.fromEntries(all.map((key) => [key, selected.has(key)]));
      return api<ModulesInfo>(`/api/v1/tenants/${tenant.id}/modules/`, {
        method: "PUT",
        body: { modules: body },
      });
    },
    onSuccess: (info) => {
      queryClient.setQueryData(["tenant", tenant.id, "modules"], info);
      queryClient.setQueryData(["tenant", tenant.id], { ...tenant, modules: info.enabled });
      setDraft(null);
      setSaved(true);
    },
  });

  if (modules.isPending) return <Loading />;
  if (modules.isError) {
    return (
      <ErrorBox message={describeError(t, modules.error)} onRetry={() => void modules.refetch()} />
    );
  }

  const current = draft ?? new Set(modules.data.enabled);

  function toggle(key: ModuleKey, enabled: boolean) {
    const next = new Set(current);
    if (enabled) next.add(key);
    else next.delete(key);
    setDraft(next);
    setSaved(false);
  }

  return (
    <Card className="flex max-w-xl flex-col gap-4">
      <p className="text-sm text-slate-600">{t("modulesTab.intro")}</p>
      {saved && <Notice tone="success">{t("common.saved")}</Notice>}
      {save.isError && <Notice tone="danger">{describeError(t, save.error)}</Notice>}
      <fieldset className="flex flex-col gap-3">
        <legend className="sr-only">{t("tenants.detail.modules")}</legend>
        {modules.data.available.map((key) => (
          <CheckboxField
            key={key}
            label={t(`modules.${key}`)}
            checked={current.has(key)}
            onChange={(event) => toggle(key, event.target.checked)}
          />
        ))}
      </fieldset>
      <div>
        <Button onClick={() => save.mutate(current)} disabled={save.isPending || draft === null}>
          {save.isPending ? t("common.saving") : t("common.save")}
        </Button>
      </div>
    </Card>
  );
}
