import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  BedDouble,
  CalendarDays,
  LogOut,
  Brush,
  ChevronLeft,
  ChevronRight,
  Wrench,
} from "lucide-react";
import type { State, Reservation } from "./types";
import {
  Dialog,
  Field,
  Badge,
  addDays,
  dateLabel,
  money,
  overlaps,
} from "./ui";
function Stat({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
}) {
  return (
    <section className="stat">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <div className="stat-icon">{icon}</div>
    </section>
  );
}
function ReservationRows({
  records,
  select,
  currency,
}: {
  records: Reservation[];
  select: (id: number) => void;
  currency: string;
}) {
  return (
    <div className="reservation-rows">
      {records.length ? (
        records.map((r) => (
          <button
            key={r.id}
            className="reservation-row"
            onClick={() => select(r.id)}
          >
            <span className="guest-avatar">
              {r.guest
                .split(" ")
                .map((x) => x[0])
                .slice(0, 2)
                .join("")}
            </span>
            <span>
              <strong>{r.guest}</strong>
              <small>
                {r.units
                  .map(
                    (u) => u.room + (u.kind === "SHARED" ? ` · ${u.name}` : ""),
                  )
                  .join(", ")}
              </small>
            </span>
            <span className="row-end">
              <Badge status={r.status} />
              <small>{r.financial_review_required ? "Cuenta pendiente de revisión" : `${money(r.balance, currency)} pendiente`}</small>
            </span>
          </button>
        ))
      ) : (
        <div className="empty compact">Sin movimientos previstos.</div>
      )}
    </div>
  );
}
export function Reception({
  data,
  date,
  setDate,
  select,
  configure,
}: {
  data: State;
  date: string;
  setDate: (d: string) => void;
  select: (id: number) => void;
  configure: () => void;
}) {
  const active = data.reservations.filter((r) =>
      ["CONFIRMED", "IN_HOUSE"].includes(r.status),
    ),
    today = data.today;
  const units = data.units.filter(
    (u) => u.active && data.rooms.find((r) => r.id === u.room_id)?.active,
  );
  const occupancy = new Set(
    active
      .filter(
        (r) =>
          r.status === "IN_HOUSE" ||
          overlaps(r.start, r.end, today, addDays(today, 1)),
      )
      .flatMap((r) => r.units.map((u) => u.id)),
  ).size;
  return (
    <>
      <div className="stats">
        <Stat
          label="Ocupación de hoy"
          value={`${Math.round((100 * occupancy) / Math.max(1, units.length))}%`}
          detail="Por unidad reservable"
          icon={<BedDouble />}
        />
        <Stat
          label="Llegadas de hoy"
          value={String(
            active.filter((r) => r.start === today && r.status === "CONFIRMED")
              .length,
          )}
          detail="Reservas por recibir"
          icon={<CalendarDays />}
        />
        <Stat
          label="Salidas de hoy"
          value={String(
            active.filter((r) => r.end === today && r.status === "IN_HOUSE")
              .length,
          )}
          detail="Estadías por finalizar"
          icon={<LogOut />}
        />
        <Stat
          label="Limpieza pendiente"
          value={String(
            data.cleaning.filter((t) => t.status !== "DONE").length,
          )}
          detail="Unidades por preparar"
          icon={<Brush />}
        />
      </div>
      <section className="panel calendar-panel">
        <div className="panel-heading">
          <div>
            <h2>Mapa de ocupación</h2>
            <p>Habitaciones privadas y camas compartidas</p>
          </div>
          <div className="calendar-controls">
            <button
              className="icon-button"
              aria-label="Semana anterior"
              onClick={() => setDate(addDays(date, -7))}
            >
              <ChevronLeft size={18} />
            </button>
            <input
              aria-label="Fecha inicial del calendario"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value || today)}
            />
            <button
              className="icon-button"
              aria-label="Semana siguiente"
              onClick={() => setDate(addDays(date, 7))}
            >
              <ChevronRight size={18} />
            </button>
            <button className="button small" onClick={() => setDate(today)}>
              Hoy
            </button>
          </div>
        </div>
        <div className="calendar-scroll">
          <div
            className="calendar-grid"
            style={{ gridTemplateColumns: "220px repeat(7,minmax(115px,1fr))" }}
          >
            <div className="calendar-label header">Habitación / cama</div>
            {Array.from({ length: 7 }, (_, i) => {
              const d = addDays(date, i);
              return (
                <div
                  className={`day-head ${d === today ? "today" : ""}`}
                  key={d}
                >
                  <span>
                    {new Date(`${d}T12:00:00`).toLocaleDateString("es-AR", {
                      weekday: "short",
                    })}
                  </span>
                  <strong>{new Date(`${d}T12:00:00`).getDate()}</strong>
                  {i === 0 && (
                    <small>
                      {new Date(`${d}T12:00:00`).toLocaleDateString("es-AR", {
                        month: "short",
                      })}
                    </small>
                  )}
                </div>
              );
            })}
            {data.rooms
              .filter((r) => r.active)
              .map((room) => (
                <div
                  className="room-group"
                  key={room.id}
                  style={{ gridColumn: "1 / -1" }}
                >
                  <div className="room-title">
                    <BedDouble size={15} />
                    <strong>{room.name}</strong>
                    <span>
                      {room.kind === "SHARED"
                        ? `${room.capacity} camas`
                        : `Privada · ${room.capacity} plazas`}
                    </span>
                  </div>
                  {units
                    .filter((u) => u.room_id === room.id)
                    .map((unit) => (
                      <div
                        className="unit-row"
                        key={unit.id}
                        style={{
                          gridTemplateColumns:
                            "220px repeat(7,minmax(115px,1fr))",
                        }}
                      >
                        <div className="calendar-label unit-label">
                          <span>
                            {room.kind === "PRIVATE"
                              ? "Habitación completa"
                              : unit.name}
                          </span>
                          <span
                            className={`clean-dot ${unit.cleaning.toLowerCase()}`}
                            title={
                              unit.cleaning === "CLEAN"
                                ? "Lista para recibir"
                                : "Requiere limpieza"
                            }
                          />
                        </div>
                        {Array.from({ length: 7 }, (_, i) => {
                          const day = addDays(date, i);
                          const r = [...data.reservations]
                            .sort(
                              (a, b) =>
                                Number(b.status !== "CHECKED_OUT") -
                                Number(a.status !== "CHECKED_OUT"),
                            )
                            .find(
                              (r) =>
                                r.status !== "CANCELLED" &&
                                r.units.some((a) => a.id === unit.id) &&
                                (r.status === "IN_HOUSE"
                                  ? overlaps(
                                      r.start,
                                      r.end > today ? r.end : addDays(today, 1),
                                      day,
                                      addDays(day, 1),
                                    )
                                  : overlaps(
                                      r.start,
                                      r.status === "CHECKED_OUT"
                                        ? r.checkout_date || r.end
                                        : r.end,
                                      day,
                                      addDays(day, 1),
                                    )),
                            );
                          const m = data.maintenance.find(
                            (m) =>
                              m.status !== "DONE" &&
                              m.blocking &&
                              m.room_id === room.id &&
                              (!m.unit_id || m.unit_id === unit.id) &&
                              overlaps(m.start, m.end, day, addDays(day, 1)),
                          );
                          return (
                            <div
                              key={day}
                              className={`calendar-cell ${day === today ? "today" : ""}`}
                            >
                              {r ? (
                                <button
                                  className={`booking ${r.status.toLowerCase()}`}
                                  onClick={() => select(r.id)}
                                  title={`${r.guest} · ${dateLabel(r.start)} a ${dateLabel(r.end)}`}
                                >
                                  <span>{r.guest}</span>
                                  {r.start === day && (
                                    <small>
                                      {r.guests} huésped
                                      {r.guests > 1 ? "es" : ""}
                                    </small>
                                  )}
                                </button>
                              ) : m ? (
                                <span className="blocked">
                                  <Wrench size={14} />
                                  Bloqueada
                                </span>
                              ) : (
                                <span className="available-cell">—</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ))}
                </div>
              ))}
          </div>
          {!data.rooms.length && (
            <div className="empty">
              <h3>Creá las habitaciones de tu hotel</h3>
              <p>
                La disponibilidad aparecerá aquí cuando configures el
                inventario.
              </p>
              <button className="button" onClick={configure}>
                Configurar habitaciones
              </button>
            </div>
          )}
        </div>
        <div className="legend">
          <span>
            <i className="legend-swatch green" />
            Alojado
          </span>
          <span>
            <i className="legend-swatch blue" />
            Confirmada
          </span>
          <span>
            <i className="legend-swatch gray" />
            Finalizada
          </span>
          <span>
            <i className="legend-swatch stripe" />
            Mantenimiento
          </span>
          <small>El día de salida queda disponible para otra reserva.</small>
        </div>
      </section>
      <div className="daily-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Llegadas de hoy</h2>
            <span className="count">
              {active.filter((r) => r.start === today).length}
            </span>
          </div>
          <ReservationRows
            records={active.filter((r) => r.start === today)}
            select={select}
            currency={data.hotel.currency}
          />
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Salidas de hoy</h2>
            <span className="count">
              {active.filter((r) => r.end === today).length}
            </span>
          </div>
          <ReservationRows
            records={active.filter((r) => r.end === today)}
            select={select}
            currency={data.hotel.currency}
          />
        </section>
      </div>
    </>
  );
}
export function Reservations({
  data,
  select,
}: {
  data: State;
  select: (id: number) => void;
}) {
  return (
    <section className="panel">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Reserva / huésped</th>
              <th>Unidad</th>
              <th>Llegada</th>
              <th>Salida</th>
              <th>Estado</th>
              <th>Saldo</th>
            </tr>
          </thead>
          <tbody>
            {data.reservations.map((r) => (
              <tr key={r.id} onClick={() => select(r.id)}>
                <td>
                  <button className="text-button" onClick={() => select(r.id)}>
                    <strong>{r.guest}</strong>
                    <small>{r.code}</small>
                  </button>
                </td>
                <td>
                  {r.units
                    .map(
                      (u) =>
                        `${u.room}${u.kind === "SHARED" ? ` · ${u.name}` : ""}`,
                    )
                    .join(", ")}
                </td>
                <td>{dateLabel(r.start)}</td>
                <td>{dateLabel(r.end)}</td>
                <td>
                  <Badge status={r.status} />
                </td>
                <td>{r.financial_review_required ? <><strong>Cuenta pendiente de revisión</strong><small>Movimientos registrados: {money(r.balance, data.hotel.currency)}</small></> : money(r.balance, data.hotel.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data.reservations.length && (
          <div className="empty">
            Todavía no hay reservas. Creá la primera para comenzar.
          </div>
        )}
      </div>
    </section>
  );
}
export function NewReservation({
  data,
  busy,
  error,
  close,
  save,
}: {
  data: State;
  busy: boolean;
  error: string;
  close: () => void;
  save: (values: unknown) => Promise<boolean>;
}) {
  const [start, setStart] = useState(data.today),
    [end, setEnd] = useState(addDays(data.today, 1)),
    [ids, setIds] = useState<number[]>([]),
    [rates, setRates] = useState<Record<string, string>>({});
  const available = data.units.filter(
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
  );
  const total =
    ids.reduce(
      (n, id) =>
        n + Number(rates[id] ?? data.units.find((u) => u.id === id)?.rate ?? 0),
      0,
    ) *
    Math.max(
      0,
      Math.round(
        (new Date(`${end}T12:00:00`).getTime() -
          new Date(`${start}T12:00:00`).getTime()) /
          86400000,
      ),
    );
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    await save({
      ...f,
      start,
      end,
      guests: Number(f.guests),
      unit_ids: ids,
      rates,
    });
  }
  return (
    <Dialog title="Nueva reserva" onClose={close} wide>
      <form onSubmit={submit}>
        <div className="dialog-body">
          <div className="form-grid">
            <Field label="Huésped responsable">
              <input name="guest" required maxLength={120} autoFocus />
            </Field>
            <Field label="Cantidad de huéspedes">
              <input
                name="guests"
                type="number"
                min={1}
                max={40}
                defaultValue={1}
                required
              />
            </Field>
            <Field label="Llegada">
              <input
                type="date"
                required
                value={start}
                onChange={(e) => {
                  setStart(e.target.value);
                  setIds([]);
                }}
              />
            </Field>
            <Field label="Salida">
              <input
                type="date"
                required
                min={addDays(start || data.today, 1)}
                value={end}
                onChange={(e) => {
                  setEnd(e.target.value);
                  setIds([]);
                }}
              />
            </Field>
            <Field label="Teléfono o correo">
              <input name="contact" maxLength={120} />
            </Field>
            <Field label="Documento (opcional)">
              <input name="document" maxLength={80} />
            </Field>
          </div>
          <h3>Unidades disponibles</h3>
          <p className="muted">
            Elegí habitaciones o camas. La tarifa es por noche y por unidad.
          </p>
          <div className="unit-picker">
            {available.map((u) => {
              const room = data.rooms.find((r) => r.id === u.room_id)!;
              return (
                <div
                  className={`unit-choice ${ids.includes(u.id) ? "selected" : ""}`}
                  key={u.id}
                >
                  <label>
                    <input
                      type="checkbox"
                      checked={ids.includes(u.id)}
                      onChange={(e) =>
                        setIds(
                          e.target.checked
                            ? [...ids, u.id]
                            : ids.filter((id) => id !== u.id),
                        )
                      }
                    />
                    <span>
                      <strong>{room.name}</strong>
                      <small>
                        {room.kind === "SHARED"
                          ? u.name
                          : `Habitación completa · ${room.capacity} plazas`}
                      </small>
                    </span>
                  </label>
                  <input
                    aria-label={`Tarifa por noche de ${room.name} ${u.name}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={rates[u.id] ?? u.rate}
                    onChange={(e) =>
                      setRates({ ...rates, [u.id]: e.target.value })
                    }
                  />
                </div>
              );
            })}
            {!available.length && (
              <p className="empty compact">
                No hay unidades disponibles en esas fechas.
              </p>
            )}
          </div>
          <Field label="Notas de la estadía">
            <textarea name="notes" rows={2} />
          </Field>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
        </div>
        <div className="dialog-footer">
          <div>
            <small>Total de alojamiento</small>
            <strong>{money(total, data.hotel.currency)}</strong>
          </div>
          <button
            className="button primary"
            disabled={busy || !ids.length || end <= start}
          >
            {busy ? "Guardando…" : "Crear reserva"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
