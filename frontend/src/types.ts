export type Hotel = {
  name: string;
  subtitle: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  logo: string | null;
  cover: string | null;
  sections: Record<string, boolean>;
  currency: string;
};
export type User = { name: string; admin: boolean };
export type Room = {
  id: number;
  name: string;
  kind: "PRIVATE" | "SHARED";
  capacity: number;
  active: boolean;
  image: string | null;
};
export type Unit = {
  id: number;
  room_id: number;
  name: string;
  rate: string;
  cleaning: "CLEAN" | "DIRTY" | "CLEANING";
  active: boolean;
};
export type Entry = {
  id: number;
  kind: "CHARGE" | "PAYMENT";
  description: string;
  amount: string;
  method: string;
  created_at: string;
  user: string;
};
export type Reservation = {
  id: number;
  code: string;
  guest: string;
  contact: string;
  document: string;
  guests: number;
  start: string;
  end: string;
  notes: string;
  status: "CONFIRMED" | "IN_HOUSE" | "CHECKED_OUT" | "CANCELLED";
  updated_at: string;
  checkout_date: string | null;
  units: {
    id: number;
    name: string;
    room_id: number;
    room: string;
    kind: string;
    rate: string;
  }[];
  ledger: Entry[];
  total: string;
  paid: string;
  balance: string;
};
export type Cleaning = {
  id: number;
  unit_id: number;
  status: "PENDING" | "IN_PROGRESS" | "DONE";
  note: string;
  updated_at: string;
};
export type Maintenance = {
  id: number;
  room_id: number;
  unit_id: number | null;
  title: string;
  notes: string;
  start: string;
  end: string;
  blocking: boolean;
  status: "OPEN" | "IN_PROGRESS" | "DONE";
};
export type State = {
  hotel: Hotel;
  today: string;
  rooms: Room[];
  units: Unit[];
  reservations: Reservation[];
  cleaning: Cleaning[];
  maintenance: Maintenance[];
  server_time: string;
};
export type Page =
  | "overview"
  | "reservations"
  | "billing"
  | "cleaning"
  | "maintenance"
  | "settings";
export type Perform = (
  work: () => Promise<unknown>,
  message: string,
) => Promise<boolean>;
