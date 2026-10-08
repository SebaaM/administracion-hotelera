import { useState } from "react";
import type { FormEvent } from "react";
import { Brush, Wrench, Plus, Printer, Wallet } from "lucide-react";
import type { State, Perform } from "./types";
import { api } from "./api";
import { Dialog, Field, Badge, addDays, dateLabel, money } from "./ui";

export function Billing({
  data,
  select,
}: {
  data: State;
  select: (id: number) => void;
}) {
  const records = data.reservations.filter((r) => r.status !== "CANCELLED");
  return (
    <>
      <div className="billing-summary">
        <Wallet />
        <div>
          <span>Saldo pendiente total</span>
          <strong>
            {money(
              records.reduce((sum, r) => sum + Number(r.balance), 0),
              data.hotel.currency,
            )}
          </strong>
        </div>
        <p>Cargos, anticipos y cobros de las estadías.</p>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Cuentas de huéspedes</h2>
          <span className="muted">Comprobantes internos</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Huésped</th>
                <th>Estado</th>
                <th>Cargos</th>
                <th>Cobrado</th>
                <th>Pendiente</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.guest}</strong>
                    <small className="block muted">{r.code}</small>
                  </td>
                  <td>
                    <Badge status={r.status} />
                  </td>
                  <td>{money(r.total, data.hotel.currency)}</td>
                  <td>{money(r.paid, data.hotel.currency)}</td>
                  <td>
                    <strong>{money(r.balance, data.hotel.currency)}</strong>
                  </td>
                  <td>
                    <button
                      className="button small"
                      onClick={() => select(r.id)}
                    >
                      Ver cuenta
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!records.length && (
            <div className="empty">
              Las cuentas aparecerán al crear reservas.
            </div>
          )}
        </div>
      </section>
    </>
  );
}

export function CleaningPage({
  data,
  busy,
  perform,
  error,
}: {
  data: State;
  busy: boolean;
  perform: Perform;
  error: string;
}) {
  const [create, setCreate] = useState(false);
  const pending = data.cleaning.filter((t) => t.status !== "DONE");
  const free = data.units.filter(
    (u) =>
      u.active &&
      data.rooms.find((r) => r.id === u.room_id)?.active &&
      !pending.some((t) => t.unit_id === u.id) &&
      !data.reservations.some(
        (r) => r.status === "IN_HOUSE" && r.units.some((a) => a.id === u.id),
      ),
  );
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = Object.fromEntries(new FormData(e.currentTarget));
    if (
      await perform(
        () =>
          api("cleaning/", "POST", { ...form, unit_id: Number(form.unit_id) }),
        "Tarea de limpieza creada",
      )
    )
      setCreate(false);
  }
  const target = (unitId: number) => {
    const unit = data.units.find((u) => u.id === unitId);
    const room = data.rooms.find((r) => r.id === unit?.room_id);
    return {
      name: room?.name || "Habitación",
      detail: room?.kind === "SHARED" ? unit?.name : "Habitación completa",
    };
  };
  return (
    <>
      <div className="section-toolbar">
        <p className="muted">
          El check-out genera automáticamente la limpieza de las unidades
          liberadas.
        </p>
        <button
          className="button primary"
          disabled={busy || !free.length}
          onClick={() => setCreate(true)}
        >
          <Plus size={18} />
          Nueva tarea
        </button>
      </div>
      <div className="kanban">
        {(["PENDING", "IN_PROGRESS", "DONE"] as const).map((status) => (
          <section className="kanban-column" key={status}>
            <header>
              <h2>
                {status === "PENDING"
                  ? "Por limpiar"
                  : status === "IN_PROGRESS"
                    ? "En limpieza"
                    : "Listas"}
              </h2>
              <span className="count">
                {data.cleaning.filter((t) => t.status === status).length}
              </span>
            </header>
            {data.cleaning
              .filter((t) => t.status === status)
              .map((task) => (
                <article className="task-card" key={task.id}>
                  <div className="task-icon">
                    <Brush size={18} />
                  </div>
                  <h3>{target(task.unit_id).name}</h3>
                  <p className="unit-name">{target(task.unit_id).detail}</p>
                  {task.note && <p>{task.note}</p>}
                  <Badge status={task.status} />
                  {status !== "DONE" && (
                    <button
                      className="button full"
                      disabled={busy}
                      onClick={() =>
                        void perform(
                          () =>
                            api(`cleaning/${task.id}/`, "POST", {
                              status:
                                status === "PENDING" ? "IN_PROGRESS" : "DONE",
                            }),
                          status === "PENDING"
                            ? "Limpieza iniciada"
                            : "Unidad lista para recibir",
                        )
                      }
                    >
                      {status === "PENDING"
                        ? "Comenzar limpieza"
                        : "Marcar como lista"}
                    </button>
                  )}
                </article>
              ))}
            {!data.cleaning.some((t) => t.status === status) && (
              <p className="empty compact">Sin tareas.</p>
            )}
          </section>
        ))}
      </div>
      {create && (
        <Dialog
          title="Nueva tarea de limpieza"
          onClose={() => setCreate(false)}
        >
          <form onSubmit={submit}>
            <div className="dialog-body">
              <Field label="Unidad">
                <select name="unit_id" required>
                  {free.map((u) => (
                    <option key={u.id} value={u.id}>
                      {target(u.id).name} · {target(u.id).detail}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Indicaciones">
                <textarea name="note" maxLength={200} rows={3} />
              </Field>
              {error && <p className="form-error">{error}</p>}
            </div>
            <div className="dialog-footer">
              <button className="button primary" disabled={busy}>
                Crear tarea
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}

export function MaintenancePage({
  data,
  busy,
  perform,
  error,
}: {
  data: State;
  busy: boolean;
  perform: Perform;
  error: string;
}) {
  const [create, setCreate] = useState(false),
    [room, setRoom] = useState(
      String(data.rooms.find((r) => r.active)?.id || ""),
    );
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    const values = {
      ...f,
      room: Number(room),
      unit: f.unit ? Number(f.unit) : null,
      blocking: f.blocking === "on",
    };
    if (
      await perform(
        () => api("maintenance/", "POST", values),
        "Incidencia registrada",
      )
    )
      setCreate(false);
  }
  return (
    <>
      <div className="section-toolbar">
        <p className="muted">
          Bloqueá una cama o una habitación completa mientras se realizan los
          trabajos.
        </p>
        <button
          className="button primary"
          disabled={busy || !data.rooms.some((r) => r.active)}
          onClick={() => setCreate(true)}
        >
          <Plus size={18} />
          Nueva incidencia
        </button>
      </div>
      <div className="maintenance-grid">
        {data.maintenance.map((m) => (
          <article className="panel maintenance-card" key={m.id}>
            <div className="task-top">
              <Wrench size={22} />
              <Badge status={m.status} />
            </div>
            <h2>{m.title}</h2>
            <p className="unit-name">
              {data.rooms.find((r) => r.id === m.room_id)?.name} ·{" "}
              {m.unit_id
                ? data.units.find((u) => u.id === m.unit_id)?.name
                : "Toda la habitación"}
            </p>
            <p>{m.notes || "Sin observaciones adicionales."}</p>
            <div className="maintenance-period">
              {dateLabel(m.start)} — {dateLabel(m.end)}
              <span>
                {m.blocking && m.status !== "DONE"
                  ? "Disponibilidad bloqueada"
                  : "Sin bloqueo activo"}
              </span>
            </div>
            {m.status !== "DONE" && (
              <button
                className="button full"
                disabled={busy}
                onClick={() =>
                  void perform(
                    () =>
                      api(`maintenance/${m.id}/`, "POST", {
                        status: m.status === "OPEN" ? "IN_PROGRESS" : "DONE",
                      }),
                    m.status === "OPEN"
                      ? "Trabajo iniciado"
                      : "Incidencia resuelta; bloqueo liberado",
                  )
                }
              >
                {m.status === "OPEN"
                  ? "Comenzar trabajo"
                  : "Resolver incidencia"}
              </button>
            )}
          </article>
        ))}
      </div>
      {!data.maintenance.length && (
        <section className="panel empty">
          <Wrench />
          <h2>Sin incidencias registradas</h2>
          <p>Los trabajos de mantenimiento aparecerán aquí.</p>
        </section>
      )}
      {create && (
        <Dialog title="Nueva incidencia" onClose={() => setCreate(false)}>
          <form onSubmit={submit}>
            <div className="dialog-body">
              <Field label="Trabajo a realizar">
                <input name="title" required maxLength={160} autoFocus />
              </Field>
              <Field label="Habitación">
                <select
                  value={room}
                  onChange={(e) => setRoom(e.target.value)}
                  required
                >
                  {data.rooms
                    .filter((r) => r.active)
                    .map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                </select>
              </Field>
              <Field label="Alcance">
                <select name="unit" key={room}>
                  <option value="">Toda la habitación</option>
                  {data.units
                    .filter((u) => u.room_id === Number(room) && u.active)
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name}
                      </option>
                    ))}
                </select>
              </Field>
              <div className="form-grid">
                <Field label="Inicio">
                  <input
                    name="start"
                    type="date"
                    defaultValue={data.today}
                    required
                  />
                </Field>
                <Field label="Fin (día disponible)">
                  <input
                    name="end"
                    type="date"
                    defaultValue={addDays(data.today, 1)}
                    required
                  />
                </Field>
              </div>
              <label className="checkbox-field">
                <input name="blocking" type="checkbox" defaultChecked />
                Bloquear reservas durante el período
              </label>
              <Field label="Observaciones">
                <textarea name="notes" rows={3} />
              </Field>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
            </div>
            <div className="dialog-footer">
              <button className="button primary" disabled={busy}>
                Registrar incidencia
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}

export function PrintButton() {
  return (
    <button className="button" type="button" onClick={() => window.print()}>
      <Printer size={18} />
      Imprimir comprobante interno
    </button>
  );
}
