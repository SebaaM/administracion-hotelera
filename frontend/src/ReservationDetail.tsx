import { useState } from "react";
import type { FormEvent } from "react";
import { Wallet, Plus, Pencil } from "lucide-react";
import type { Reservation, State, Perform } from "./types";
import { api } from "./api";
import { Dialog, Field, Badge, dateLabel, money } from "./ui";
import { PrintButton } from "./Operations";
export function ReservationDetail({
  record,
  data,
  busy,
  perform,
  error,
  close,
}: {
  record: Reservation;
  data: State;
  busy: boolean;
  perform: Perform;
  error: string;
  close: () => void;
}) {
  const [entry, setEntry] = useState<"CHARGE" | "PAYMENT" | null>(null),
    [edit, setEdit] = useState<Reservation | null>(null),
    [confirmation, setConfirmation] = useState<"checkout" | "cancel" | null>(
      null,
    );
  async function confirmTransition() {
    if (!confirmation) return;
    if (
      await perform(
        () => api(`reservations/${record.id}/${confirmation}/`, "POST"),
        confirmation === "checkout"
          ? "Check-out registrado; limpieza pendiente"
          : "Reserva cancelada",
      )
    )
      setConfirmation(null);
  }
  async function submitEntry(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (
      await perform(
        () =>
          api(`reservations/${record.id}/ledger/`, "POST", {
            ...f,
            kind: entry,
          }),
        "Movimiento registrado",
      )
    )
      setEntry(null);
  }
  async function submitGuest(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!edit) return;
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (
      await perform(
        () =>
          api(`reservations/${record.id}/`, "PATCH", {
            ...f,
            expected_updated_at: edit.updated_at,
          }),
        "Datos de la reserva actualizados",
      )
    )
      setEdit(null);
  }
  return (
    <Dialog title={`${record.code} · ${record.guest}`} onClose={close} wide>
      <div className="dialog-body">
        <div className="detail-top">
          <Badge status={record.status} />
          <span>
            {dateLabel(record.start)} — {dateLabel(record.end)}
          </span>
        </div>
        <p>{record.units.map((u) => `${u.room} · ${u.name}`).join(", ")}</p>
        <div className="guest-data">
          <span>
            {record.guests} huésped{record.guests > 1 ? "es" : ""}
          </span>
          {record.contact && <span>{record.contact}</span>}
          {record.document && <span>Documento: {record.document}</span>}
          <button
            className="text-button"
            onClick={() => setEdit(edit ? null : record)}
          >
            <Pencil size={14} />
            Editar datos
          </button>
        </div>
        {record.notes && <p className="reservation-note">{record.notes}</p>}
        {edit && (
          <form className="inline-form" onSubmit={submitGuest}>
            <div className="form-grid">
              <Field label="Huésped">
                <input
                  name="guest"
                  defaultValue={edit.guest}
                  required
                  maxLength={120}
                />
              </Field>
              <Field label="Contacto">
                <input
                  name="contact"
                  defaultValue={edit.contact}
                  maxLength={120}
                />
              </Field>
              <Field label="Documento">
                <input
                  name="document"
                  defaultValue={edit.document}
                  maxLength={80}
                />
              </Field>
              <Field label="Notas">
                <textarea name="notes" defaultValue={edit.notes} rows={2} />
              </Field>
            </div>
            <button className="button primary" disabled={busy}>
              Guardar datos
            </button>
          </form>
        )}
        <div className="detail-totals">
          <div>
            <small>Total de cargos</small>
            <strong>{money(record.total, data.hotel.currency)}</strong>
          </div>
          <div>
            <small>Cobrado</small>
            <strong>{money(record.paid, data.hotel.currency)}</strong>
          </div>
          <div>
            <small>Saldo pendiente</small>
            <strong>{money(record.balance, data.hotel.currency)}</strong>
          </div>
        </div>
        <div className="actions operational-actions">
          {record.status === "CONFIRMED" && (
            <>
              <button
                className="button primary"
                disabled={busy}
                onClick={() =>
                  void perform(
                    () => api(`reservations/${record.id}/checkin/`, "POST"),
                    "Check-in registrado",
                  )
                }
              >
                Registrar check-in
              </button>
              <button
                className="button danger"
                disabled={busy}
                onClick={() => {
                  setConfirmation("cancel");
                  setEntry(null);
                }}
              >
                Cancelar reserva
              </button>
            </>
          )}
          {record.status === "IN_HOUSE" && (
            <button
              className="button primary"
              disabled={busy}
              onClick={() => {
                setConfirmation("checkout");
                setEntry(null);
              }}
            >
              Registrar check-out
            </button>
          )}
          {record.status !== "CANCELLED" && (
            <>
              <button
                className="button"
                disabled={busy}
                onClick={() => {
                  setEntry("CHARGE");
                  setEdit(null);
                  setConfirmation(null);
                }}
              >
                <Plus size={16} />
                Agregar cargo
              </button>
              <button
                className="button"
                disabled={busy || Number(record.balance) <= 0}
                onClick={() => {
                  setEntry("PAYMENT");
                  setEdit(null);
                  setConfirmation(null);
                }}
              >
                <Wallet size={16} />
                Registrar cobro
              </button>
            </>
          )}
        </div>
        {confirmation && (
          <section
            className="inline-form"
            aria-label="Confirmación de operación"
          >
            <h3>
              {confirmation === "checkout"
                ? "Confirmar la salida"
                : "Confirmar la cancelación"}
            </h3>
            <p>
              {confirmation === "checkout"
                ? `Saldo pendiente: ${money(record.balance, data.hotel.currency)}. Se liberarán las unidades y se generará una tarea de limpieza. El saldo se conserva en la cuenta.`
                : "Se cancelará la reserva y se liberarán sus unidades."}
            </p>
            <div className="actions">
              <button
                className="button primary"
                disabled={busy}
                onClick={() => void confirmTransition()}
              >
                {confirmation === "checkout"
                  ? "Confirmar check-out"
                  : "Confirmar cancelación"}
              </button>
              <button
                className="button"
                disabled={busy}
                onClick={() => setConfirmation(null)}
              >
                Volver
              </button>
            </div>
          </section>
        )}
        {entry && (
          <form className="inline-form" onSubmit={submitEntry}>
            <h3>{entry === "CHARGE" ? "Nuevo cargo" : "Nuevo cobro"}</h3>
            <div className="form-grid">
              <Field label="Concepto">
                <input
                  key={entry}
                  name="description"
                  required
                  maxLength={160}
                  defaultValue={entry === "PAYMENT" ? "Cobro de estadía" : ""}
                  autoFocus
                />
              </Field>
              <Field label="Importe">
                <input
                  name="amount"
                  type="number"
                  min="0.01"
                  step="0.01"
                  max={entry === "PAYMENT" ? record.balance : undefined}
                  required
                />
              </Field>
              {entry === "PAYMENT" && (
                <Field label="Medio de pago">
                  <select name="method" required>
                    <option value="CASH">Efectivo</option>
                    <option value="CARD">Tarjeta (registro manual)</option>
                    <option value="TRANSFER">Transferencia</option>
                    <option value="OTHER">Otro</option>
                  </select>
                </Field>
              )}
            </div>
            <div className="actions">
              <button className="button primary" disabled={busy}>
                Guardar movimiento
              </button>
              <button
                type="button"
                className="button"
                onClick={() => setEntry(null)}
              >
                Volver
              </button>
            </div>
          </form>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <section className="receipt">
          <header className="receipt-header">
            {data.hotel.logo && <img src={data.hotel.logo} alt="" />}
            <div>
              <h2>{data.hotel.name}</h2>
              <p>Comprobante interno de cuenta · CI-{record.code}</p>
            </div>
          </header>
          <div className="receipt-meta">
            <strong>{record.guest}</strong>
            <span>
              Estadía: {dateLabel(record.start)} — {dateLabel(record.end)}
            </span>
          </div>
          <h3 className="screen-only">Movimientos de la cuenta</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Concepto</th>
                  <th>Tipo / medio</th>
                  <th>Importe</th>
                </tr>
              </thead>
              <tbody>
                {record.ledger.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {new Date(item.created_at).toLocaleDateString("es-AR", {
                        timeZone: data.hotel.timezone,
                      })}
                    </td>
                    <td>{item.description}</td>
                    <td>
                      {item.kind === "CHARGE"
                        ? "Cargo"
                        : (
                            {
                              CASH: "Efectivo",
                              CARD: "Tarjeta",
                              TRANSFER: "Transferencia",
                              OTHER: "Otro",
                            } as Record<string, string>
                          )[item.method] || "Cobro"}
                    </td>
                    <td>{money(item.amount, data.hotel.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!record.ledger.length && (
              <p className="empty compact">Sin movimientos registrados.</p>
            )}
          </div>
          <div className="print-totals">
            <p>Total de cargos: {money(record.total, data.hotel.currency)}</p>
            <p>Cobrado: {money(record.paid, data.hotel.currency)}</p>
            <strong>Saldo: {money(record.balance, data.hotel.currency)}</strong>
          </div>
          <p className="receipt-disclaimer">
            Comprobante interno. No constituye una factura fiscal.
          </p>
        </section>
        <div className="actions">
          <PrintButton />
        </div>
      </div>
    </Dialog>
  );
}
