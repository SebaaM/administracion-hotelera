import { api } from "./api";
import type { State } from "./types";
import { overlaps } from "./ui";
type Tool = {
  name: string;
  title: string;
  description: string;
  inputSchema: object;
  annotations: { readOnlyHint: boolean; untrustedContentHint: boolean };
  execute: (input: unknown) => unknown | Promise<unknown>;
};
type Context = {
  registerTool: (
    tool: Tool,
    options: { signal: AbortSignal },
  ) => void | Promise<void>;
};
export function registerPmsTools(openReservation: () => void) {
  const context = (document as Document & { modelContext?: Context })
    .modelContext;
  if (!context?.registerTool) return () => {};
  const lifecycle = new AbortController();
  const tools: Tool[] = [
    {
      name: "get_hotel_availability",
      title: "Consultar disponibilidad",
      description:
        "Consulta habitaciones y camas disponibles para un período. No devuelve datos de huéspedes ni modifica reservas.",
      inputSchema: {
        type: "object",
        properties: {
          start: { type: "string", format: "date" },
          end: { type: "string", format: "date" },
        },
        required: ["start", "end"],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) {
        const p = input as { start?: unknown; end?: unknown };
        if (
          !p ||
          typeof p.start !== "string" ||
          typeof p.end !== "string" ||
          !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(p.start) ||
          !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(p.end) ||
          p.end <= p.start ||
          Number.isNaN(Date.parse(p.start)) ||
          Number.isNaN(Date.parse(p.end))
        )
          throw new Error(
            "El período debe tener fechas válidas y una salida posterior a la llegada.",
          );
        const start = p.start,
          end = p.end,
          data = await api<State>("state/");
        return {
          start,
          end,
          units: data.units
            .filter(
              (u) =>
                u.active &&
                data.rooms.find((r) => r.id === u.room_id)?.active &&
                !data.reservations.some(
                  (r) =>
                    ["CONFIRMED", "IN_HOUSE"].includes(r.status) &&
                    r.units.some((a) => a.id === u.id) &&
                    (overlaps(r.start, r.end, start, end) ||
                      (r.status === "IN_HOUSE" &&
                        start <= data.today &&
                        end > data.today)),
                ) &&
                !data.maintenance.some(
                  (m) =>
                    m.status !== "DONE" &&
                    m.blocking &&
                    m.room_id === u.room_id &&
                    (!m.unit_id || m.unit_id === u.id) &&
                    overlaps(m.start, m.end, start, end),
                ),
            )
            .map((u) => ({
              id: u.id,
              room: data.rooms.find((r) => r.id === u.room_id)?.name,
              unit: u.name,
              nightly_rate: u.rate,
              currency: data.hotel.currency,
            })),
        };
      },
    },
    {
      name: "open_reservation_form",
      title: "Abrir formulario de reserva",
      description:
        "Abre el formulario visible para preparar una reserva. No crea ni guarda ninguna reserva.",
      inputSchema: {
        type: "object",
        properties: {},
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      execute(input) {
        if (!input || typeof input !== "object" || Object.keys(input).length)
          throw new Error("Esta herramienta no recibe parámetros.");
        openReservation();
        return { opened: true, saved: false };
      },
    },
  ];
  for (const tool of tools) {
    try {
      void Promise.resolve(
        context.registerTool(tool, { signal: lifecycle.signal }),
      ).catch(() => {});
    } catch {
      /* Ordinary browsers retain the full interface. */
    }
  }
  return () => lifecycle.abort();
}
