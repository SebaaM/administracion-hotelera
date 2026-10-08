import { useState } from "react";
import type { FormEvent } from "react";
import { Plus, Building2, Image, Save } from "lucide-react";
import type { State, Perform, Room, Unit } from "./types";
import { api } from "./api";
import { Dialog, Field, Badge, money } from "./ui";
export function contrastText(color: string) {
  const rgb = color
    .match(/[a-f\d]{2}/gi)
    ?.map((c) => parseInt(c, 16) / 255) || [0, 0, 0];
  const linear = rgb.map((v) =>
    v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4,
  );
  const l = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  return l > 0.179 ? "#172c34" : "#ffffff";
}
export function Configuration({
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
  const [tab, setTab] = useState<"brand" | "rooms">("brand"),
    [newRoom, setNewRoom] = useState(false),
    [editRoom, setEditRoom] = useState<Room | null>(null),
    [editUnit, setEditUnit] = useState<Unit | null>(null);
  const [primary, setPrimary] = useState(data.hotel.primary_color),
    [secondary, setSecondary] = useState(data.hotel.secondary_color),
    [accent, setAccent] = useState(data.hotel.accent_color),
    [kind, setKind] = useState("PRIVATE");
  async function saveBrand(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const sections: Record<string, boolean> = {};
    for (const p of ["reservations", "billing", "cleaning", "maintenance"]) {
      sections[p] = f.get(`section_${p}`) === "on";
      f.delete(`section_${p}`);
    }
    f.set("sections", JSON.stringify(sections));
    f.set("primary_color", primary);
    f.set("secondary_color", secondary);
    f.set("accent_color", accent);
    for (const key of ["logo", "cover"]) {
      const file = f.get(key);
      if (file instanceof File && !file.size) f.delete(key);
      if (f.get(`remove_${key}`) === "on") f.set(key, "");
      f.delete(`remove_${key}`);
    }
    await perform(
      () => api("settings/", "PATCH", f),
      "Identidad y secciones guardadas",
    );
  }
  async function createRoom(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (
      await perform(
        () =>
          api("rooms/", "POST", {
            ...f,
            capacity: Number(f.capacity || f.beds),
            beds: Number(f.beds || 1),
            rate: f.rate,
            kind,
          }),
        "Habitación creada",
      )
    )
      setNewRoom(false);
  }
  async function changeRoom(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editRoom) return;
    const f = new FormData(e.currentTarget);
    const image = f.get("image");
    if (image instanceof File && !image.size) f.delete("image");
    f.set("active", f.get("active") === "on" ? "true" : "false");
    if (
      await perform(
        () => api(`rooms/${editRoom.id}/`, "PATCH", f),
        "Habitación actualizada",
      )
    )
      setEditRoom(null);
  }
  async function changeUnit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editUnit) return;
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (
      await perform(
        () =>
          api(`units/${editUnit.id}/`, "PATCH", {
            name: f.name,
            rate: f.rate,
            active: f.active === "on",
          }),
        "Unidad actualizada",
      )
    )
      setEditUnit(null);
  }
  return (
    <>
      <div
        className="settings-tabs"
        role="tablist"
        aria-label="Configuración del hotel"
      >
        <button
          role="tab"
          aria-selected={tab === "brand"}
          className={tab === "brand" ? "active" : ""}
          onClick={() => setTab("brand")}
        >
          Marca y secciones
        </button>
        <button
          role="tab"
          aria-selected={tab === "rooms"}
          className={tab === "rooms" ? "active" : ""}
          onClick={() => setTab("rooms")}
        >
          Habitaciones y camas
        </button>
      </div>
      {tab === "brand" ? (
        <form onSubmit={saveBrand}>
          <div className="settings-grid">
            <section className="panel settings-panel">
              <h2>Identidad del establecimiento</h2>
              <p className="muted">
                Una misma aplicación, con la marca de cada hotel.
              </p>
              <Field label="Nombre del hotel o hostel">
                <input
                  name="name"
                  defaultValue={data.hotel.name}
                  maxLength={100}
                  required
                />
              </Field>
              <Field label="Texto breve del encabezado">
                <input
                  name="subtitle"
                  defaultValue={data.hotel.subtitle}
                  maxLength={120}
                />
              </Field>
              <div className="brand-uploads">
                {(["logo", "cover"] as const).map((key) => (
                  <div className="upload-box" key={key}>
                    {data.hotel[key] ? (
                      <img
                        src={data.hotel[key]!}
                        alt={
                          key === "logo"
                            ? "Logo actual"
                            : "Imagen de acceso actual"
                        }
                      />
                    ) : (
                      <Image size={26} />
                    )}
                    <Field
                      label={
                        key === "logo"
                          ? "Logo del hotel"
                          : "Imagen de la pantalla de acceso"
                      }
                    >
                      <input
                        name={key}
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                      />
                    </Field>
                    <small>PNG, JPG o WebP · hasta 5 MB</small>
                    {data.hotel[key] && (
                      <label className="checkbox-field">
                        <input type="checkbox" name={`remove_${key}`} />
                        Quitar imagen actual
                      </label>
                    )}
                  </div>
                ))}
              </div>
            </section>
            <div>
              <section className="panel settings-panel">
                <h2>Tres colores base</h2>
                <p className="muted">
                  Los estados de operación conservan colores consistentes.
                </p>
                <div className="color-fields">
                  {[
                    { label: "Principal", value: primary, set: setPrimary },
                    {
                      label: "Secundario",
                      value: secondary,
                      set: setSecondary,
                    },
                    { label: "Acento", value: accent, set: setAccent },
                  ].map((c) => (
                    <Field key={c.label} label={c.label}>
                      <div className="color-input">
                        <input
                          type="color"
                          value={c.value}
                          onChange={(e) => c.set(e.target.value)}
                          aria-label={`Color ${c.label.toLowerCase()}`}
                        />
                        <span>{c.value.toUpperCase()}</span>
                      </div>
                    </Field>
                  ))}
                </div>
                <div
                  className="brand-preview"
                  style={{
                    background: primary,
                    color: contrastText(primary),
                    borderLeft: `5px solid ${accent}`,
                  }}
                >
                  <Building2 size={22} />
                  <strong>{data.hotel.name}</strong>
                  <span
                    style={{
                      background: secondary,
                      color: contrastText(secondary),
                    }}
                  >
                    Nueva reserva
                  </span>
                </div>
              </section>
              <section className="panel settings-panel sections-panel">
                <h2>Secciones visibles</h2>
                <p className="muted">
                  Ocultar una sección modifica la navegación, no los permisos ni
                  los datos.
                </p>
                {[
                  { key: "reservations", label: "Reservas" },
                  { key: "billing", label: "Cargos y cobros" },
                  { key: "cleaning", label: "Limpieza" },
                  { key: "maintenance", label: "Mantenimiento" },
                ].map((p) => (
                  <label className="section-toggle" key={p.key}>
                    <span>{p.label}</span>
                    <input
                      type="checkbox"
                      name={`section_${p.key}`}
                      defaultChecked={data.hotel.sections[p.key] !== false}
                    />
                  </label>
                ))}
              </section>
            </div>
          </div>
          <div className="settings-save">
            <button className="button primary" disabled={busy}>
              <Save size={18} />
              {busy ? "Guardando…" : "Guardar configuración"}
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="section-toolbar">
            <p className="muted">
              Las habitaciones privadas se venden completas; los dormitorios,
              por cama.
            </p>
            <button
              className="button primary"
              disabled={busy}
              onClick={() => {
                setKind("PRIVATE");
                setNewRoom(true);
              }}
            >
              <Plus size={18} />
              Nueva habitación
            </button>
          </div>
          <div className="inventory-grid">
            {data.rooms.map((room) => (
              <section
                className={`panel inventory-card ${!room.active ? "inactive" : ""}`}
                key={room.id}
              >
                {room.image && (
                  <img
                    className="room-image"
                    src={room.image}
                    alt={room.name}
                  />
                )}
                <header>
                  <div>
                    <h2>{room.name}</h2>
                    <p>
                      {room.kind === "PRIVATE"
                        ? `Privada · ${room.capacity} plazas`
                        : `Compartida · ${data.units.filter((u) => u.room_id === room.id && u.active).length} camas activas`}
                      {!room.active ? " · Desactivada" : ""}
                    </p>
                  </div>
                  <button
                    className="button small"
                    onClick={() => setEditRoom(room)}
                  >
                    Editar
                  </button>
                </header>
                {data.units
                  .filter((u) => u.room_id === room.id)
                  .map((unit) => (
                    <div className="inventory-unit" key={unit.id}>
                      <div>
                        <strong>{unit.name}</strong>
                        <small>
                          {money(unit.rate, data.hotel.currency)} / noche
                          {!unit.active ? " · Desactivada" : ""}
                        </small>
                      </div>
                      <Badge status={unit.cleaning} />
                      <button
                        className="button small"
                        onClick={() => setEditUnit(unit)}
                      >
                        Editar unidad
                      </button>
                    </div>
                  ))}
                {room.kind === "SHARED" && (
                  <button
                    className="button small add-bed"
                    disabled={busy}
                    onClick={() => {
                      const label = prompt("Nombre de la nueva cama");
                      if (label)
                        void perform(
                          () =>
                            api(`rooms/${room.id}/units/`, "POST", {
                              name: label,
                              rate: "0.00",
                            }),
                          "Cama creada; configurá su tarifa",
                        );
                    }}
                  >
                    <Plus size={15} />
                    Agregar cama
                  </button>
                )}
              </section>
            ))}
          </div>
          {!data.rooms.length && (
            <section className="panel empty">
              <Building2 />
              <h2>Configurá el inventario del hotel</h2>
              <p>
                Creá habitaciones privadas o dormitorios compartidos para
                empezar.
              </p>
            </section>
          )}
        </>
      )}
      {newRoom && (
        <Dialog title="Nueva habitación" onClose={() => setNewRoom(false)}>
          <form onSubmit={createRoom}>
            <div className="dialog-body">
              <Field label="Nombre o número">
                <input name="name" required maxLength={60} autoFocus />
              </Field>
              <Field label="Tipo de habitación">
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="PRIVATE">Privada · venta completa</option>
                  <option value="SHARED">Compartida · venta por cama</option>
                </select>
              </Field>
              <Field
                label={
                  kind === "PRIVATE"
                    ? "Capacidad de huéspedes"
                    : "Cantidad de camas"
                }
              >
                <input
                  key={kind}
                  name={kind === "PRIVATE" ? "capacity" : "beds"}
                  type="number"
                  min={1}
                  max={40}
                  defaultValue={kind === "PRIVATE" ? 2 : 4}
                  required
                />
              </Field>
              <Field
                label={
                  kind === "PRIVATE"
                    ? "Tarifa por habitación y noche"
                    : "Tarifa por cama y noche"
                }
              >
                <input
                  name="rate"
                  type="number"
                  min={0}
                  step="0.01"
                  defaultValue={0}
                  required
                />
              </Field>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
            </div>
            <div className="dialog-footer">
              <button className="button primary" disabled={busy}>
                Crear habitación
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {editRoom && (
        <Dialog
          title={`Editar ${editRoom.name}`}
          onClose={() => setEditRoom(null)}
        >
          <form onSubmit={changeRoom}>
            <div className="dialog-body">
              <Field label="Nombre">
                <input
                  name="name"
                  defaultValue={editRoom.name}
                  required
                  maxLength={60}
                />
              </Field>
              <Field label="Imagen de la habitación">
                <input
                  name="image"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                />
              </Field>
              <label className="checkbox-field">
                <input
                  name="active"
                  type="checkbox"
                  defaultChecked={editRoom.active}
                />
                Habitación activa
              </label>
              <p className="muted">
                La desactivación se permite cuando no existen reservas activas.
              </p>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
            </div>
            <div className="dialog-footer">
              <button className="button primary" disabled={busy}>
                Guardar habitación
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {editUnit && (
        <Dialog
          title="Editar unidad reservable"
          onClose={() => setEditUnit(null)}
        >
          <form onSubmit={changeUnit}>
            <div className="dialog-body">
              <Field label="Nombre">
                <input
                  name="name"
                  defaultValue={editUnit.name}
                  required
                  maxLength={60}
                />
              </Field>
              <Field label="Tarifa por noche">
                <input
                  name="rate"
                  type="number"
                  min={0}
                  step="0.01"
                  defaultValue={editUnit.rate}
                  required
                />
              </Field>
              <label className="checkbox-field">
                <input
                  name="active"
                  type="checkbox"
                  defaultChecked={editUnit.active}
                />
                Unidad activa
              </label>
              <p className="muted">
                Los cambios de tarifa se aplican a nuevas reservas.
              </p>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
            </div>
            <div className="dialog-footer">
              <button className="button primary" disabled={busy}>
                Guardar unidad
              </button>
            </div>
          </form>
        </Dialog>
      )}
    </>
  );
}
