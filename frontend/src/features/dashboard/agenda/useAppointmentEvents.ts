import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { KEYS } from "../shared/api";

export function useAppointmentEvents() {
  const client = useQueryClient();
  const [live, setLive] = useState(false);
  useEffect(() => {
    const source = new EventSource("/api/v1/events/");
    source.onopen = () => {
      setLive(true);
      void client.invalidateQueries({ queryKey: KEYS.appointments });
    };
    source.onerror = () => setLive(false);
    const refresh = () => {
      void client.invalidateQueries({ queryKey: KEYS.appointments });
      void client.invalidateQueries({ queryKey: KEYS.slots });
    };
    const events = ["appointment.created", "appointment.updated", "appointment.cancelled"];
    events.forEach((event) => source.addEventListener(event, refresh));
    return () => {
      events.forEach((event) => source.removeEventListener(event, refresh));
      source.close();
    };
  }, [client]);
  return live;
}
