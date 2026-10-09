import {afterEach,describe,expect,it,vi} from "vitest";
import {cleanup,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {ImportPage} from "./ImportPage";
import {ReviewStep} from "./ReviewStep";
import {AccountReview} from "./AccountReview";
import type {Draft,Decisions,Row} from "./types";
import type {Reservation,State} from "../types";
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
const data:State={hotel:{name:"Hotel ficticio",subtitle:"Prueba",primary_color:"#000000",secondary_color:"#FFFFFF",accent_color:"#123456",logo:null,cover:null,sections:{},currency:"ARS",timezone:"America/Argentina/Buenos_Aires"},today:"2026-10-09",cleaning:[],maintenance:[],server_time:"2026-10-09T12:00:00Z",rooms:[{id:1,name:"2",kind:"SHARED",active:true,capacity:1,image:null}],units:[{id:1,room_id:1,name:"a",active:true,cleaning:"CLEAN",rate:"100"}],reservations:[]};
const row:Row={key:"primero",selected:true,action:"REVIEW",errors:["Confirmá revisión"],reservation_id:null,before:null,snapshot:"",suggestions:[],candidate:{key:"primero",source_id:"origen",source_unit:"2-a",guest:"Persona ficticia",start:"2026-08-30",end:"2026-09-01",status:"CHECKED_OUT",unit_id:1,notes:[],notes_text:"",colors:[],references:[],warnings:[]}};
function draft():Draft{return {id:1,profile_id:1,filename:"ficticia.xlsx",revision:1,state:"DRAFT",created_at:"2026-10-09",configuration:{sheets:[{name:"AGO-26",year:2026,month:8,label_col:1,header_rows:[1],unit_rows:[2]}],mapping:{"2-a":1},mapping_confirmed:true},decisions:{},source_units:["2-a"],source_summary:{format:"xlsx",sheets:[{name:"AGO-26",notes:0,colors:{},warnings:[]}]},preview:{rows:[structuredClone(row)],pending_notes:[],summary:{REVIEW:1},can_apply:false}};}
describe("Asistente de migración",()=>{
  it("retoma un borrador y exige guardar la revisión y confirmar antes de aplicar",async()=>{
    let current=draft();let applied=0;
    vi.stubGlobal("fetch",vi.fn(async(url:string,options:RequestInit)=>{
      const method=options?.method||"GET";
      let result:unknown;
      if(url.endsWith("profiles/"))result=[{id:1,name:"Prueba",configuration:{}}];
      else if(url.endsWith("drafts/")&&method==="GET")result=[current];
      else if(url.endsWith("drafts/1/")&&method==="GET")result=current;
      else if(url.endsWith("drafts/")&&method==="POST"){
        expect(options.body).toBeInstanceOf(FormData);result=current;
      }else if(url.endsWith("drafts/1/")&&method==="PATCH"){
        const payload=JSON.parse(String(options.body));
        expect(payload.expected_revision).toBe(current.revision);
        current={...current,revision:current.revision+1,configuration:payload.configuration,decisions:payload.decisions};
        if(payload.decisions.rows?.primero?.reviewed)current.preview={...current.preview,can_apply:true,summary:{CREATE:1},rows:[{...row,action:"CREATE",errors:[]}]};
        result=current;
      }else if(url.endsWith("apply/")){
        applied++;current={...current,state:"APPLIED",batch:{id:1,actions:[{action:"CREATE",reservation_id:1}]}};result=current;
      }else throw new Error("Ruta inesperada: "+url);
      return new Response(JSON.stringify(result),{status:200});
    }));
    const onApplied=vi.fn(async()=>{});
    render(<ImportPage data={data} onApplied={onApplied}/>);
    await screen.findByRole("option",{name:"Prueba"});
    fireEvent.click(await screen.findByRole("button",{name:/Lote 1/}));
    await screen.findByText("1. Confirmar períodos y filas");
    fireEvent.click(screen.getByRole("button",{name:/Guardar y continuar/}));
    await screen.findByText("2. Vincular habitaciones y camas");
    fireEvent.click(screen.getByRole("button",{name:/Guardar y continuar/}));
    await screen.findByText("3. Revisar reservas y observaciones");
    fireEvent.click(screen.getByLabelText("Revisé fechas, estado y advertencias."));
    expect((screen.getByRole("button",{name:"Revisar aplicación"}) as HTMLButtonElement).disabled).toBe(true);
    expect(applied).toBe(0);
    fireEvent.click(screen.getByRole("button",{name:"Guardar revisión"}));
    await waitFor(()=>expect((screen.getByRole("button",{name:"Revisar aplicación"}) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button",{name:"Revisar aplicación"}));
    expect(applied).toBe(0);
    fireEvent.click(screen.getByRole("button",{name:"Confirmar importación"}));
    await screen.findByText("Importación aplicada");
    expect(applied).toBe(1);expect(onApplied).toHaveBeenCalledOnce();
  });
  it("permite quitar una unidad sin enviar el identificador cero",()=>{
    const onChange=vi.fn();const d=draft();
    render(<ReviewStep draft={d} data={data} decisions={{}} onChange={onChange}/>);
    fireEvent.change(screen.getByLabelText("Unidad · 2-a"),{target:{value:""}});
    expect(onChange.mock.calls[0][0].rows.primero.unit_id).toBeNull();
  });
  it("conserva la decisión del tramo cronológicamente primero al unir en orden inverso",()=>{
    const d=draft();const second={...structuredClone(row),key:"segundo",candidate:{...row.candidate,key:"segundo",start:"2026-09-01",end:"2026-09-03"}};
    d.preview.rows=[row,second];const onChange=vi.fn();
    const decisions:Decisions={rows:{primero:{reviewed:true},segundo:{reviewed:true}}};
    render(<ReviewStep draft={d} data={data} decisions={decisions} onChange={onChange}/>);
    fireEvent.change(screen.getByLabelText("Primer tramo"),{target:{value:"segundo"}});
    fireEvent.change(screen.getByLabelText("Segundo tramo"),{target:{value:"primero"}});
    fireEvent.click(screen.getByRole("button",{name:"Confirmar unión"}));
    expect(onChange.mock.calls[0][0].rows).toEqual({primero:{reviewed:true}});
  });
});
describe("Conciliación de cuentas",()=>{
  it("exige confirmar una cuenta vacía y envía la versión examinada",async()=>{
    const snapshot={id:7,ledger:[],updated_at:"version-examinada",ledger_signature:"firma-examinada"} as unknown as Reservation;
    const requests:unknown[]=[];
    vi.stubGlobal("fetch",vi.fn(async(_url:string,options:RequestInit)=>{
      requests.push(JSON.parse(String(options.body)));
      return new Response(JSON.stringify({detail:"La cuenta cambió. Volvé a revisarla."}),{status:400});
    }));
    const onClose=vi.fn();
    const perform=vi.fn(async(work:()=>Promise<unknown>)=>{try{await work();return true;}catch{return false;}});
    render(<AccountReview snapshot={snapshot} busy={false} perform={perform} onClose={onClose}/>);
    const button=screen.getByRole("button",{name:"Confirmar cuenta revisada"});
    expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(button);
    await waitFor(()=>expect(requests).toHaveLength(1));
    expect(requests[0]).toEqual({expected_updated_at:"version-examinada",ledger_signature:"firma-examinada",confirmed_zero:true});
    expect(onClose).not.toHaveBeenCalled();
  });
});
