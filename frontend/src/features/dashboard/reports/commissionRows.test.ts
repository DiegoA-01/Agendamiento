import { describe, expect, it } from "vitest";
import type { CommissionEntry } from "./api";
import { commissionRows } from "./commissionRows";

let id = 0;
function entry(over: Partial<CommissionEntry>): CommissionEntry {
  id += 1;
  return {
    id: String(id),
    kind: "entry",
    appointment_id: "a1",
    appointment_start_at: "2026-11-17T12:15:00-05:00",
    professional_id: "andres",
    professional_name: "Andrés",
    service_id: "s",
    service_name: "Corte",
    base_amount: "0.00",
    pct: "40.00",
    commission_amount: "0.00",
    business_amount: "0.00",
    adjusts_id: null,
    reason: "",
    created_at: "2026-11-17T13:00:00-05:00",
    ...over,
  };
}

describe("comisiones por cita", () => {
  it("una cita con varios servicios es una sola fila con el total y su porcentaje", () => {
    const rows = commissionRows([
      entry({
        service_name: "Depilación",
        base_amount: "10000.00",
        commission_amount: "4000.00",
        business_amount: "6000.00",
      }),
      entry({
        service_name: "Corte clásico",
        base_amount: "30000.00",
        commission_amount: "12000.00",
        business_amount: "18000.00",
      }),
      entry({
        service_name: "Barba",
        base_amount: "25000.00",
        commission_amount: "10000.00",
        business_amount: "15000.00",
      }),
      entry({
        appointment_id: "a2",
        service_name: "Corte clásico",
        base_amount: "30000.00",
        commission_amount: "12000.00",
        business_amount: "18000.00",
      }),
    ]);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      services: ["Depilación", "Corte clásico", "Barba"],
      base: "65000.00",
      commission: "26000.00",
      business: "39000.00",
      pct: "40.00",
      adjustment: "0.00",
    });
  });

  it("los ajustes se suman a su cita y el porcentaje pasa a ser el efectivo", () => {
    const rows = commissionRows([
      entry({
        service_name: "Barba",
        base_amount: "25000.00",
        commission_amount: "10000.00",
        business_amount: "15000.00",
      }),
      entry({
        kind: "adjustment",
        service_name: "Barba",
        base_amount: "0.00",
        pct: "48.00",
        commission_amount: "2000.00",
        business_amount: "-2000.00",
        reason: "Prueba",
      }),
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      services: ["Barba"],
      base: "25000.00",
      commission: "12000.00",
      business: "13000.00",
      pct: "48.00",
      adjustment: "2000.00",
      reasons: ["Prueba"],
    });
  });
});
