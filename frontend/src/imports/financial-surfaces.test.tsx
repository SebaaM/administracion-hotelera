import {afterEach,it,expect,vi} from "vitest";
import {cleanup,fireEvent,render,screen,within} from "@testing-library/react";
import {Reception,Reservations} from "../Reception";
import {ReservationDetail} from "../ReservationDetail";
import type {State,Reservation} from "../types";
afterEach(()=>cleanup());
const record:Reservation={id:1,code:"R-00001",guest:"Persona ficticia",contact:"",document:"",guests:1,start:"2026-10-09",end:"2026-10-10",notes:"",import_notes:"",import_colors:[],financial_review_required:true,ledger_signature:"firma",status:"IN_HOUSE",updated_at:"2026-10-09T12:00:00Z",checkout_date:null,units:[{id:1,name:"a",room_id:1,room:"2",kind:"SHARED",rate:null}],ledger:[],total:"0",paid:"0",balance:"0"};
const data:State={hotel:{name:"Hotel ficticio",subtitle:"Prueba",primary_color:"#000000",secondary_color:"#FFFFFF",accent_color:"#123456",logo:null,cover:null,sections:{},currency:"ARS",timezone:"America/Argentina/Buenos_Aires"},today:"2026-10-09",cleaning:[],maintenance:[],server_time:"2026-10-09T12:00:00Z",rooms:[{id:1,name:"2",kind:"SHARED",active:true,capacity:1,image:null}],units:[{id:1,room_id:1,name:"a",active:true,cleaning:"CLEAN",rate:"100"}],reservations:[record]};
it("recepción no muestra una cuenta sin conciliar como saldo cero pendiente",()=>{
  render(<Reception data={data} date={data.today} setDate={vi.fn()} select={vi.fn()} configure={vi.fn()}/>);
  expect(screen.getByText("Cuenta pendiente de revisión")).toBeTruthy();
  expect(screen.queryByText(/\$.*pendiente/)).toBeNull();
});
it("el listado distingue una cuenta migrada pendiente de revisión",()=>{
  render(<Reservations data={data} select={vi.fn()}/>);
  expect(screen.getByText("Cuenta pendiente de revisión")).toBeTruthy();
});
it("confirmar salida aclara que el saldo registrado no es la cuenta final",()=>{
  Object.defineProperties(HTMLDialogElement.prototype,{
    showModal:{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute("open","");}},
    close:{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute("open");}},
  });
  render(<ReservationDetail record={record} data={data} busy={false} perform={vi.fn(async()=>true)} error="" close={vi.fn()}/>);
  fireEvent.click(screen.getByRole("button",{name:"Registrar check-out"}));
  const confirmation=screen.getByLabelText("Confirmación de operación");
  expect(within(confirmation).getByText(/Cuenta pendiente de revisión/)).toBeTruthy();
  expect(within(confirmation).getByText(/movimientos registrados/)).toBeTruthy();
  expect(within(confirmation).queryByText(/Saldo pendiente:/)).toBeNull();
});
