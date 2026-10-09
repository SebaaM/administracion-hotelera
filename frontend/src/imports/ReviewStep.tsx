import {useState} from "react";
import type {State} from "../types";
import type {Draft,Decisions,Decision,Row} from "./types";
import {Field} from "../ui";
const statuses={CONFIRMED:"Confirmada",IN_HOUSE:"Alojado",CHECKED_OUT:"Finalizada",CANCELLED:"Cancelada"};
const actions:Record<string,string>={CREATE:"Crear",UPDATE:"Actualizar",UNCHANGED:"Sin cambios",CONFLICT:"Conflicto",REVIEW:"Requiere revisión"};
export function ReviewStep({draft,data,decisions,onChange}:{draft:Draft;data:State;decisions:Decisions;onChange:(d:Decisions)=>void}){
  const [filter,setFilter]=useState("ALL");const [query,setQuery]=useState("");const [joinA,setJoinA]=useState("");const [joinB,setJoinB]=useState("");
  const rows=draft.preview.rows||[];
  function change(key:string,patch:Decision){onChange({...decisions,rows:{...decisions.rows,[key]:{...decisions.rows?.[key],...patch}}});}
  function selected(r:Row){return decisions.rows?.[r.key]?.selected??r.selected;}
  const visible=rows.filter(r=>(filter==="ALL"||r.action===filter)&&r.candidate.guest.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  return <section className="panel import-section">
    <h2>3. Revisar reservas y observaciones</h2>
    <p className="muted">Guardá la revisión para actualizar los conflictos y el resumen. Las cuentas importadas quedarán pendientes de conciliación.</p>
    <div className="import-toolbar"><input aria-label="Buscar huésped" placeholder="Buscar huésped…" value={query} onChange={e=>setQuery(e.target.value)}/><select aria-label="Filtrar acción" value={filter} onChange={e=>setFilter(e.target.value)}><option value="ALL">Todas las acciones</option>{Object.entries(actions).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></div>
    <div className="actions">
      <button className="button small" onClick={()=>onChange({...decisions,rows:Object.fromEntries(rows.map(r=>[r.key,{...decisions.rows?.[r.key],selected:false}]))})}>Excluir todas</button>
      <button className="button small" onClick={()=>onChange({...decisions,rows:{...decisions.rows,...Object.fromEntries(visible.map(r=>[r.key,{...decisions.rows?.[r.key],selected:true,reviewed:true,status:decisions.rows?.[r.key]?.status||r.candidate.status}]))}})}>Confirmar fechas y estado de las filas visibles</button>
    </div>
    <p className="muted">{visible.length} de {rows.length} filas · las ediciones pendientes todavía no se aplican al PMS.</p>
    <div className="import-rows">{visible.map(r=>{
      const c=r.candidate;const d=decisions.rows?.[r.key]||{};const chosen=selected(r);
      return <article className={`import-row ${chosen?"":"excluded"}`} key={r.key}>
        <header><label className="import-check"><input type="checkbox" checked={chosen} onChange={e=>change(r.key,{selected:e.target.checked})}/><strong>{c.guest}</strong></label><span className={`import-action ${r.action.toLowerCase()}`}>{actions[r.action]}</span></header>
        <div className="form-grid">
          <Field label="Huésped"><input value={d.guest??c.guest} maxLength={120} onChange={e=>change(r.key,{guest:e.target.value})}/></Field>
          <Field label={`Unidad · ${c.source_unit}`}><select value={d.unit_id??c.unit_id??""} onChange={e=>change(r.key,{unit_id:e.target.value?Number(e.target.value):null})}><option value="">Sin vincular</option>{data.units.filter(u=>u.active).map(u=><option key={u.id} value={u.id}>{data.rooms.find(room=>room.id===u.room_id)?.name} · {u.name}</option>)}</select></Field>
          <Field label="Llegada"><input type="date" value={d.start??c.start} onChange={e=>change(r.key,{start:e.target.value})}/></Field>
          <Field label="Salida"><input type="date" value={d.end??c.end} onChange={e=>change(r.key,{end:e.target.value})}/></Field>
          <Field label="Estado"><select value={d.status??c.status} onChange={e=>change(r.key,{status:e.target.value})}>{Object.entries(statuses).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></Field>
          <Field label="Vincular reserva existente"><select value={d.reservation_id??r.reservation_id??""} onChange={e=>change(r.key,{reservation_id:e.target.value?Number(e.target.value):null,new_confirmed:false})}><option value="">Nueva / vínculo del perfil</option>{data.reservations.map(res=><option key={res.id} value={res.id}>{res.code} · {res.guest} · {res.start}</option>)}</select></Field>
        </div>
        <div className="import-confirmations"><label className="import-check"><input type="checkbox" checked={d.reviewed||false} onChange={e=>change(r.key,{reviewed:e.target.checked,status:d.status||c.status})}/>Revisé fechas, estado y advertencias.</label>
          {!!r.suggestions.length&&!r.reservation_id&&<label className="import-check"><input type="checkbox" checked={d.new_confirmed||false} onChange={e=>change(r.key,{new_confirmed:e.target.checked})}/>Confirmo que es una reserva nueva, aunque hay coincidencias.</label>}
        </div>
        {r.before&&<div className="import-before"><strong>Reserva actual R-{String(r.reservation_id).padStart(5,"0")}</strong><p>{r.before.guest} · {r.before.start} → {r.before.end} · {statuses[r.before.status as keyof typeof statuses]}</p><p>Unidad actual: {r.before.units.map(u=>`${u.room} · ${u.name}`).join(", ")}</p><p>Observaciones actuales de importación: {r.before.import_notes||"Sin observaciones"}</p></div>}
        {!!c.notes.length&&<details open><summary>Observaciones ({c.notes.length})</summary><p className="import-note">{c.notes_text}</p></details>}
        {!!c.colors.length&&<div className="import-colors">{Array.from(new Set(c.colors.map(color=>color.hex))).map(hex=><span key={hex}><i className="import-color" style={{background:hex}}/>{c.colors.find(color=>color.hex===hex)?.meaning||hex}</span>)}</div>}
        {!!c.warnings.length&&<ul className="import-warnings">{Array.from(new Set(c.warnings)).map(w=><li key={w}>{w}</li>)}</ul>}
        {chosen&&!!r.errors.length&&<ul className="form-error">{r.errors.map((err,i)=><li key={i}>{err}</li>)}</ul>}
        <details><summary>Celdas de origen ({c.references.length})</summary><p className="muted">{c.references.map(ref=>`${ref.sheet}!${ref.cell}`).join(", ")}</p></details>
      </article>;
    })}</div>
    {!!draft.preview.pending_notes?.length&&<section className="import-pending"><h3>Notas pendientes ({draft.preview.pending_notes.length})</h3><p>Asigná cada nota a una reserva seleccionada o explicá su exclusión.</p>{draft.preview.pending_notes.map(n=>{
      const decision=decisions.notes?.[n.key];const value=decision?.action==="EXCLUDE"?"EXCLUDE":decision?.target||"";
      return <div key={n.key} className="import-orphan"><strong>{n.sheet}!{n.cell}</strong><p className="import-note">{n.text}</p><select aria-label={`Destino de nota ${n.key}`} value={value} onChange={e=>onChange({...decisions,notes:{...decisions.notes,[n.key]:e.target.value==="EXCLUDE"?{action:"EXCLUDE",reason:""}:{action:"ASSIGN",target:e.target.value}}})}><option value="">Elegir destino</option>{rows.filter(selected).map(r=><option key={r.key} value={r.key}>{r.candidate.guest} · {r.candidate.source_unit} · {r.candidate.start}</option>)}<option value="EXCLUDE">Excluir con motivo</option></select>{value==="EXCLUDE"&&<input aria-label={`Motivo de exclusión ${n.key}`} placeholder="Motivo obligatorio" value={decision?.reason||""} onChange={e=>onChange({...decisions,notes:{...decisions.notes,[n.key]:{action:"EXCLUDE",reason:e.target.value}}})}/>}</div>;
    })}</section>}
    <details className="import-legend"><summary>Unir continuidad entre hojas</summary><p>Solo se unen tramos consecutivos de la misma persona y unidad. Confirmá la unión antes de guardar.</p><div className="actions"><select aria-label="Primer tramo" value={joinA} onChange={e=>setJoinA(e.target.value)}><option value="">Primer tramo</option>{rows.map(r=><option key={r.key} value={r.key}>{r.candidate.guest} · {r.candidate.source_unit} · {r.candidate.start}</option>)}</select><select aria-label="Segundo tramo" value={joinB} onChange={e=>setJoinB(e.target.value)}><option value="">Segundo tramo</option>{rows.map(r=><option key={r.key} value={r.key}>{r.candidate.guest} · {r.candidate.source_unit} · {r.candidate.start}</option>)}</select><button className="button small" disabled={!joinA||!joinB||joinA===joinB} onClick={()=>{
      const pendingRows={...decisions.rows};const first=[joinA,joinB].sort((a,b)=>rows.find(r=>r.key===a)!.candidate.start.localeCompare(rows.find(r=>r.key===b)!.candidate.start))[0];delete pendingRows[first===joinA?joinB:joinA];onChange({...decisions,rows:pendingRows,joins:[...(decisions.joins||[]),[joinA,joinB]]});setJoinA("");setJoinB("");
    }}>Confirmar unión</button></div>{!!decisions.joins?.length&&<button className="text-button" onClick={()=>onChange({...decisions,joins:[],rows:{}})}>Deshacer uniones y reiniciar revisión</button>}</details>
  </section>;
}
