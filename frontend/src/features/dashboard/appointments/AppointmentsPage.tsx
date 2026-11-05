import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Button,
  Card,
  CheckboxField,
  EmptyState,
  ErrorBox,
  Loading,
  PageHeader,
  SelectField,
  TextField,
} from "../../../shared/ui/primitives";
import { describeError } from "../../../shared/api/errors";
import { useMe } from "../../auth/useMe";
import { dateFilters, defaultRange } from "../agenda/calendar";
import { useProfessionals, useServices } from "../shared/api";
import { useCan } from "../shared/useCan";
import { AppointmentForm } from "./AppointmentForm";
import { AppointmentDetail, AppointmentSummary } from "./AppointmentDetail";
import { useAppointments } from "./api";
import { STATUSES } from "./transitions";
import type { AppointmentStatus } from "../../../shared/api/types";

export default function AppointmentsPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const zone = useMe().data?.tenant?.timezone ?? "America/Bogota";
  const [range, setRange] = useState(() => defaultRange(zone));
  const [professional, setProfessional] = useState("");
  const [statuses, setStatuses] = useState<AppointmentStatus[]>([]);
  const [customer, setCustomer] = useState(params.get("customer_id") ?? "");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const canCreate = useCan("appointments", "create");
  const professionals = useProfessionals();
  const services = useServices();
  const appointments = useAppointments({
    ...dateFilters(range.from, range.to),
    professional_id: professional,
    customer_id: customer,
    status: statuses,
  });
  const failed = appointments.isError
    ? appointments
    : professionals.isError
      ? professionals
      : services.isError
        ? services
        : null;
  const list = appointments.data?.pages.flatMap((p) => p.results) ?? [];
  return (
    <div className="min-w-0 space-y-5">
      <PageHeader
        title={t("dashboard.nav.appointments")}
        description={t("agenda.appointmentsIntro")}
        actions={
          canCreate && (
            <Button onClick={() => setCreating(true)}>{t("agenda.newAppointment")}</Button>
          )
        }
      />
      {creating && (
        <Card>
          <AppointmentForm onDone={() => setCreating(false)} />
        </Card>
      )}
      <Card className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <TextField
          label={t("agenda.from")}
          type="date"
          value={range.from}
          onChange={(e) => {
            if (e.target.value) setRange({ ...range, from: e.target.value });
          }}
        />
        <TextField
          label={t("agenda.to")}
          type="date"
          min={range.from}
          value={range.to}
          onChange={(e) => {
            if (e.target.value) setRange({ ...range, to: e.target.value });
          }}
        />
        <SelectField
          label={t("agenda.professional")}
          value={professional}
          onChange={(e) => setProfessional(e.target.value)}
        >
          <option value="">{t("common.all")}</option>
          {professionals.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.display_name}
            </option>
          ))}
        </SelectField>
        {/* Se llega con `?customer_id=` desde /clientes: se muestra como filtro quitable. */}
        {customer && (
          <div className="flex flex-wrap items-end gap-2">
            <p className="text-sm font-medium">
              {t("agenda.customerFilter", {
                name:
                  list.find((a) => a.customer.id === customer)?.customer.full_name ??
                  t("agenda.selectedCustomer"),
              })}
            </p>
            <Button
              variant="ghost"
              onClick={() => {
                setCustomer("");
                setParams((current) => {
                  current.delete("customer_id");
                  return current;
                });
              }}
            >
              {t("agenda.clearCustomer")}
            </Button>
          </div>
        )}
        <fieldset className="flex flex-wrap gap-3 sm:col-span-2 lg:col-span-4">
          <legend className="mb-2 text-sm font-medium">{t("agenda.state")}</legend>
          {STATUSES.map((status) => (
            <CheckboxField
              key={status}
              label={t(`agenda.status.${status}`)}
              checked={statuses.includes(status)}
              onChange={(e) =>
                setStatuses(
                  e.target.checked ? [...statuses, status] : statuses.filter((s) => s !== status),
                )
              }
            />
          ))}
        </fieldset>
      </Card>
      {selected && <AppointmentDetail id={selected} onClose={() => setSelected(null)} />}
      {(appointments.isPending || professionals.isPending || services.isPending) && <Loading />}
      {failed && (
        <ErrorBox message={describeError(t, failed.error)} onRetry={() => void failed.refetch()} />
      )}
      {appointments.isSuccess && !list.length && (
        <EmptyState>{t("agenda.emptyAppointments")}</EmptyState>
      )}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {list.map((appointment) => (
          <button
            className="min-w-0 rounded-xl border border-slate-200 bg-white p-4 text-slate-900 shadow-sm hover:border-sky-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
            key={appointment.id}
            onClick={() => setSelected(appointment.id)}
          >
            <AppointmentSummary appointment={appointment} />
          </button>
        ))}
      </div>
      {appointments.hasNextPage && (
        <Button
          variant="secondary"
          disabled={appointments.isFetchingNextPage}
          onClick={() => void appointments.fetchNextPage()}
        >
          {t(appointments.isFetchingNextPage ? "common.loading" : "common.loadMore")}
        </Button>
      )}
    </div>
  );
}
