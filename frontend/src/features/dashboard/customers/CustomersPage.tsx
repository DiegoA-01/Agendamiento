import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../../shared/api/client";
import { describeError } from "../../../shared/api/errors";
import type { CustomerRecord } from "../../../shared/api/types";
import {
  Button,
  Card,
  EmptyState,
  ErrorBox,
  Loading,
  Notice,
  PageHeader,
  TextField,
} from "../../../shared/ui/primitives";
import { useMe } from "../../auth/useMe";
import { KEYS } from "../shared/api";
import { useCustomers, useDebounced } from "../appointments/api";
import { CustomerForm } from "./CustomerForm";

export default function CustomersPage() {
  const { t } = useTranslation();
  const role = useMe().data?.role;
  const permitted = role === "owner" || role === "admin" || role === "receptionist";
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const customers = useCustomers(useDebounced(search), permitted);
  const [editor, setEditor] = useState<CustomerRecord | "new" | null>(null);
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/customers/${id}/`, { method: "DELETE" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: KEYS.customers });
      setEditor(null);
    },
  });
  if (!permitted) return <Notice tone="danger">{t("errors.permission_denied")}</Notice>;
  const list = customers.data?.pages.flatMap((p) => p.results) ?? [];
  return (
    <div className="min-w-0 space-y-5">
      <PageHeader
        title={t("dashboard.nav.customers")}
        description={t("agenda.customersIntro")}
        actions={<Button onClick={() => setEditor("new")}>{t("agenda.newCustomer")}</Button>}
      />
      <TextField
        label={t("agenda.customerSearch")}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {editor && (
        <Card>
          <h2 className="mb-4 text-lg font-semibold">
            {t(editor === "new" ? "agenda.newCustomer" : "agenda.editCustomer")}
          </h2>
          <CustomerForm
            key={editor === "new" ? "new" : editor.id}
            customer={editor === "new" ? undefined : editor}
            onDone={() => setEditor(null)}
          />
        </Card>
      )}
      {customers.isPending && <Loading />}
      {customers.isError && (
        <ErrorBox
          message={describeError(t, customers.error)}
          onRetry={() => void customers.refetch()}
        />
      )}
      {remove.isError && <Notice tone="danger">{describeError(t, remove.error)}</Notice>}
      {customers.isSuccess && !list.length && <EmptyState>{t("agenda.emptyCustomers")}</EmptyState>}
      <div className="grid gap-3 lg:grid-cols-2">
        {list.map((customer) => (
          <Card key={customer.id} className="min-w-0 space-y-3 break-words">
            <h2 className="font-semibold">{customer.full_name}</h2>
            <dl className="space-y-1 text-sm">
              <div>
                <dt className="inline text-slate-600">{t("agenda.phone")}: </dt>
                <dd className="inline">{customer.phone}</dd>
              </div>
              <div>
                <dt className="inline text-slate-600">{t("agenda.email")}: </dt>
                <dd className="inline">{customer.email || t("agenda.noEmail")}</dd>
              </div>
              <div>
                <dt className="inline text-slate-600">{t("agenda.appointmentCount")}: </dt>
                <dd className="inline">{customer.appointments_count}</dd>
              </div>
            </dl>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="secondary" onClick={() => setEditor(customer)}>
                {t("agenda.editCustomer")}
              </Button>
              <Button
                variant="ghost"
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm(t("agenda.deleteCustomer", { name: customer.full_name })))
                    remove.mutate(customer.id);
                }}
              >
                {t("common.delete")}
              </Button>
              <Link
                className="rounded px-2 py-2 text-sm font-medium underline focus-visible:outline-2"
                to={`/citas?customer_id=${encodeURIComponent(customer.id)}`}
              >
                {t("agenda.viewAppointments")}
              </Link>
            </div>
          </Card>
        ))}
      </div>
      {customers.hasNextPage && (
        <Button
          variant="secondary"
          disabled={customers.isFetchingNextPage}
          onClick={() => void customers.fetchNextPage()}
        >
          {t(customers.isFetchingNextPage ? "common.loading" : "common.loadMore")}
        </Button>
      )}
    </div>
  );
}
