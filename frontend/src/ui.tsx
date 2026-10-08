import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
export function Dialog({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    d?.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={wide ? "dialog wide" : "dialog"}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      aria-labelledby="dialog-title"
    >
      <header>
        <h2 id="dialog-title">{title}</h2>
        <button className="icon-button" aria-label="Cerrar" onClick={onClose}>
          <X size={20} />
        </button>
      </header>
      {children}
    </dialog>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function Badge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    CONFIRMED: "Confirmada",
    IN_HOUSE: "Alojado",
    CHECKED_OUT: "Finalizada",
    CANCELLED: "Cancelada",
    CLEAN: "Lista",
    DIRTY: "Pendiente",
    CLEANING: "En limpieza",
    PENDING: "Pendiente",
    IN_PROGRESS: "En curso",
    DONE: "Lista",
    OPEN: "Pendiente",
  };
  return (
    <span className={`badge ${status.toLowerCase()}`}>
      {labels[status] || status}
    </span>
  );
}
export const addDays = (date: string, n: number) => {
  const d = new Date(`${date}T12:00:00`);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const dateLabel = (date: string) =>
  new Date(`${date}T12:00:00`).toLocaleDateString("es-AR", {
    day: "numeric",
    month: "short",
  });
export const overlaps = (a: string, b: string, c: string, d: string) =>
  a < d && b > c;
export const money = (value: string | number, currency = "ARS") =>
  new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
