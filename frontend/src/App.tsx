import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  BedDouble,
  CalendarDays,
  LayoutDashboard,
  Plus,
  Settings,
  Wallet,
  Brush,
  Wrench,
  LogOut,
  Check,
  Menu,
  RefreshCw,
  Building2,
  FileSpreadsheet,
} from "lucide-react";
import { api, ApiError } from "./api";
import type { Hotel, User, State, Page } from "./types";
import { Field } from "./ui";
import { Billing, CleaningPage, MaintenancePage } from "./Operations";
import { Configuration, contrastText } from "./Configuration";
import { ReservationDetail } from "./ReservationDetail";
import { Reception, Reservations, NewReservation } from "./Reception";
import { registerPmsTools } from "./webmcp";
import { flushSync } from "react-dom";
import "./App.css";
import { ImportPage } from "./imports/ImportPage";
const pageNames: Record<Page, string> = {
  overview: "Vista general",
  reservations: "Reservas",
  billing: "Cargos y cobros",
  cleaning: "Limpieza",
  maintenance: "Mantenimiento",
  settings: "Configuración",
  imports: "Importar reservas",
};
const icons = {
  overview: LayoutDashboard,
  reservations: CalendarDays,
  billing: Wallet,
  cleaning: Brush,
  maintenance: Wrench,
  settings: Settings,
  imports: FileSpreadsheet,
};
export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [hotel, setHotel] = useState<Hotel | null>(null),
    [data, setData] = useState<State | null>(null);
  const [ready, setReady] = useState(false),
    [page, setPage] = useState<Page>("overview"),
    [date, setDate] = useState(""),
    [modal, setModal] = useState<"reservation" | null>(null),
    [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [syncError, setSyncError] = useState(false),
    [nav, setNav] = useState(false);
  const load = useCallback(async () => {
    try {
      const s = await api<State>("state/");
      setData(s);
      setHotel(s.hotel);
      setDate((d) => d || s.today);
      setSyncError(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setUser(null);
        setData(null);
        setError("La sesión venció. Ingresá nuevamente.");
      } else setSyncError(true);
    }
  }, []);
  useEffect(() => {
    api<{ user: User | null; hotel: Hotel; today: string }>("session/")
      .then((s) => {
        setUser(s.user);
        setHotel(s.hotel);
        setDate(s.today);
      })
      .catch(() =>
        setError(
          "No se pudo conectar al servidor local. Comprobá que esté encendido.",
        ),
      )
      .finally(() => setReady(true));
  }, []);
  useEffect(() => {
    if (!user) return;
    void load();
    const id = setInterval(() => {
      if (!document.hidden) void load();
    }, 5000);
    const focus = () => void load();
    window.addEventListener("focus", focus);
    return () => {
      clearInterval(id);
      window.removeEventListener("focus", focus);
    };
  }, [user, load]);
  useEffect(() => {
    if (!hotel) return;
    const root = document.documentElement;
    root.style.setProperty("--primary", hotel.primary_color);
    root.style.setProperty("--secondary", hotel.secondary_color);
    root.style.setProperty("--accent", hotel.accent_color);
    root.style.setProperty("--on-primary", contrastText(hotel.primary_color));
    root.style.setProperty(
      "--on-secondary",
      contrastText(hotel.secondary_color),
    );
    root.style.setProperty(
      "--secondary-ink",
      contrastText(hotel.secondary_color) === "#ffffff"
        ? hotel.secondary_color
        : "#24444d",
    );
    document.title = `${hotel.name} · PMS`;
  }, [hotel]);
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(id);
  }, [notice]);
  useEffect(() => {
    if (!user || !data || syncError) return;
    return registerPmsTools(() =>
      flushSync(() => {
        setError("");
        setModal("reservation");
      }),
    );
  }, [user, Boolean(data), syncError]);
  async function perform(work: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError("");
    try {
      await work();
      await load();
      setNotice(message);
      setModal(null);
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function signin(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fields = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      setUser(await api<User>("login/", "POST", Object.fromEntries(fields)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!ready)
    return (
      <main className="connection">
        <RefreshCw className="spin" />
        Conectando con el hotel…
      </main>
    );
  if (!user)
    return (
      <main className="login">
        <section
          className="login-brand"
          style={
            hotel?.cover
              ? {
                  backgroundImage: `linear-gradient(90deg,#153a43e8,#153a43c7),url(${hotel.cover})`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                }
              : undefined
          }
        >
          <div className="brand-mark">N</div>
          <span>PMS LOCAL</span>
          <h1>
            Todo el hotel.
            <br />
            En un mismo lugar.
          </h1>
          <p>
            Recepción, camas y habitaciones.
            <br />
            Una operación conectada.
          </p>
          <div className="login-foot">
            <Building2 size={18} /> Acceso por la red del hotel
          </div>
        </section>
        <section className="login-card">
          {hotel?.logo ? (
            <img className="login-logo" src={hotel.logo} alt={hotel.name} />
          ) : (
            <BedDouble size={36} />
          )}
          <h2>{hotel?.name || "PMS local"}</h2>
          <p>Ingresá para comenzar tu turno.</p>
          <form onSubmit={signin}>
            <Field label="Usuario">
              <input
                name="username"
                autoComplete="username"
                required
                autoFocus
              />
            </Field>
            <Field label="Contraseña">
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
              />
            </Field>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button primary full" disabled={busy}>
              {busy ? "Ingresando…" : "Ingresar"}
            </button>
          </form>
          <small>Las cuentas se crean en la administración del hotel.</small>
        </section>
      </main>
    );
  const today = data?.today || date;
  const enabled = (p: Page) =>
    p === "overview" || p === "settings" || hotel?.sections[p] !== false;
  const currentPage = enabled(page) ? page : "overview";
  const reservation = data?.reservations.find((r) => r.id === selected);
  return (
    <div className="shell">
      <aside className={`sidebar ${nav ? "mobile-open" : ""}`}>
        <div className="brand">
          {hotel?.logo ? (
            <img src={hotel.logo} alt="" />
          ) : (
            <span className="brand-mark">N</span>
          )}
          <div>
            <strong>{hotel?.name}</strong>
            <span>PMS local</span>
          </div>
        </div>
        <div className="nav-label">OPERACIÓN</div>
        <nav>
          {(Object.keys(pageNames) as Page[])
            .filter(enabled)
            .filter((p) => !["settings", "imports"].includes(p) || user.admin)
            .map((p) => {
              const Icon = icons[p];
              return (
                <button
                  key={p}
                  className={p === currentPage ? "active" : ""}
                  onClick={() => {
                    setPage(p);
                    setNav(false);
                  }}
                >
                  <Icon size={20} />
                  {pageNames[p]}
                  {p === "cleaning" && data && (
                    <span className="nav-count">
                      {data.cleaning.filter((t) => t.status !== "DONE").length}
                    </span>
                  )}
                </button>
              );
            })}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-info">
            <span className={syncError ? "status-dot bad" : "status-dot"} />
            {syncError
              ? "Sin conexión al servidor"
              : "Servidor local conectado"}
          </div>
          <div className="user">
            <span className="avatar">
              {user.name.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <strong>{user.name}</strong>
              <small>
                {user.admin ? "Administración" : "Equipo del hotel"}
              </small>
            </div>
            <button
              className="icon-button"
              aria-label="Cerrar sesión"
              onClick={() =>
                void perform(async () => {
                  await api("logout/", "POST");
                  setUser(null);
                  setData(null);
                }, "Sesión cerrada")
              }
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-toggle"
              aria-label="Abrir menú"
              onClick={() => setNav(!nav)}
            >
              <Menu />
            </button>
            <span>Recepción</span>
            <span>/</span>
            <strong>{pageNames[currentPage]}</strong>
          </div>
          <span className="top-date">
            {new Date(`${today}T12:00:00`).toLocaleDateString("es-AR", {
              weekday: "long",
              day: "numeric",
              month: "long",
            })}
          </span>
        </header>
        <main className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                {hotel?.subtitle || "OPERACIÓN DIARIA"}
              </div>
              <h1>
                {currentPage === "overview"
                  ? "El hotel, de un vistazo"
                  : pageNames[currentPage]}
              </h1>
              <p>
                {currentPage === "overview"
                  ? "Disponibilidad y movimiento para organizar tu día."
                  : currentPage === "reservations"
                    ? "Cada estadía, desde la llegada hasta la salida."
                    : ""}
              </p>
            </div>
            {["overview", "reservations"].includes(currentPage) && (
              <button
                className="button primary"
                disabled={!data || syncError}
                onClick={() => {
                  setError("");
                  setModal("reservation");
                }}
              >
                <Plus size={18} />
                Nueva reserva
              </button>
            )}
          </div>
          {syncError && (
            <div className="banner error" role="alert">
              Sin conexión con el servidor. Los cambios están pausados hasta
              reconectar.
              <button className="button small" onClick={() => void load()}>
                Reintentar
              </button>
            </div>
          )}
          {error && !modal && (
            <div className="banner error" role="alert">
              {error}
              <button className="icon-button" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          {notice && (
            <div className="toast" role="status">
              <Check size={18} />
              {notice}
            </div>
          )}
          {!data ? (
            <div className="empty">
              <RefreshCw className="spin" />
              <h2>Cargando la operación del hotel…</h2>
            </div>
          ) : (
            <>
              {currentPage === "overview" && (
                <Reception
                  data={data}
                  date={date}
                  setDate={setDate}
                  select={setSelected}
                  configure={() => setPage("settings")}
                />
              )}
              {currentPage === "reservations" && (
                <Reservations data={data} select={setSelected} />
              )}
              {currentPage === "billing" && (
                <Billing data={data} select={setSelected} />
              )}
              {currentPage === "cleaning" && (
                <CleaningPage
                  data={data}
                  busy={busy || syncError}
                  perform={perform}
                  error={error}
                />
              )}
              {currentPage === "maintenance" && (
                <MaintenancePage
                  data={data}
                  busy={busy || syncError}
                  perform={perform}
                  error={error}
                />
              )}
              {currentPage === "imports" && user.admin && <ImportPage data={data} onApplied={load} />}
              {currentPage === "settings" && user.admin && (
                <Configuration
                  key={data.hotel.name}
                  data={data}
                  busy={busy || syncError}
                  perform={perform}
                  error={error}
                />
              )}
            </>
          )}
        </main>
        <footer className="workspace-footer">
          <span>Nido PMS · Operación local</span>
          <span>
            {data
              ? `Última lectura: ${new Date(data.server_time).toLocaleTimeString("es-AR", { timeZone: data.hotel.timezone, hourCycle: "h23" })}`
              : "Conectando…"}
          </span>
        </footer>
      </div>
      {modal === "reservation" && data && (
        <NewReservation
          data={data}
          busy={busy}
          error={error}
          close={() => {
            setModal(null);
            setError("");
          }}
          save={(values) =>
            perform(
              () => api("reservations/", "POST", values),
              "Reserva creada",
            )
          }
        />
      )}
      {reservation && data && (
        <ReservationDetail
          key={reservation.id}
          record={reservation}
          data={data}
          busy={busy || syncError}
          perform={perform}
          error={error}
          close={() => {
            setSelected(null);
            setError("");
          }}
        />
      )}
    </div>
  );
}
