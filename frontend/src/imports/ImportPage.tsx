import {useEffect,useState} from "react";
import type {FormEvent} from "react";
import {Upload,FileSpreadsheet,Download,CheckCircle2,ArrowRight,Save} from "lucide-react";
import type {State} from "../types";
import type {Configuration,Decisions,Draft,Profile} from "./types";
import * as api from "./api";
import "./imports.css";
import {SourceStep} from "./SourceStep";
import {MappingStep} from "./MappingStep";
import {ReviewStep} from "./ReviewStep";
export function ImportPage({data,onApplied}:{data:State;onApplied:()=>Promise<void>}){
  const [profiles,setProfiles]=useState<Profile[]>([]),[history,setHistory]=useState<Draft[]>([]);
  const [profileId,setProfileId]=useState(""),[profileName,setProfileName]=useState("");
  const [draft,setDraft]=useState<Draft|null>(null),[configuration,setConfiguration]=useState<Configuration>({}),[decisions,setDecisions]=useState<Decisions>({});
  const [step,setStep]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState(""),[dirty,setDirty]=useState(false),[confirmation,setConfirmation]=useState(false),[discardConfirmation,setDiscardConfirmation]=useState(false);
  async function refresh(){const [p,h]=await Promise.all([api.profiles(),api.drafts()]);setProfiles(p);setHistory(h);setProfileId(id=>id||String(p[0]?.id||""));}
  useEffect(()=>{void refresh().catch(e=>setError(e.message));},[]);
  async function work(action:()=>Promise<void>){setBusy(true);setError("");setNotice("");try{await action();}catch(e){setError(e instanceof Error?e.message:"No se pudo completar la operación.");}finally{setBusy(false);}}
  function adopt(value:Draft){setDraft(value);setConfiguration(structuredClone(value.configuration));setDecisions(structuredClone(value.decisions));setDirty(false);setConfirmation(false);}
  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();const file=new FormData(e.currentTarget).get("file");if(!(file instanceof File)||!file.size)return;
    await work(async()=>{let id=Number(profileId);if(!id){const p=await api.createProfile(profileName);id=p.id;setProfiles(prev=>[...prev,p]);await refresh();setProfileId(String(id));}adopt(await api.upload(file,id));setStep(1);});
  }
  async function save(next?:number){if(!draft)return;await work(async()=>{adopt(await api.save(draft,configuration,decisions));if(next!==undefined)setStep(next);setNotice("Revisión guardada. La operación del PMS sigue sin cambios.");});}

  return <div className="import-page">
    <section className="panel import-intro"><div className="import-intro-icon"><FileSpreadsheet size={28}/></div><div><h2>Migrar reservas desde una planilla</h2><p>Conservá observaciones y colores. Revisá fechas, camas y cambios antes de incorporarlos al hotel.</p></div><span className="badge confirmed">Excel / CSV</span></section>
    {error&&<div className="banner error" role="alert">{error}{draft&&<button className="button small" onClick={()=>void work(async()=>adopt(await api.getDraft(draft.id)))}>Volver a cargar borrador</button>}</div>}
    {notice&&<div className="banner" role="status">{notice}</div>}
    {!draft?<><form className="panel import-section" onSubmit={e=>void submit(e)}>
      <h2>Cargar archivo</h2><div className="form-grid"><label className="field"><span>Perfil del hotel</span><select value={profileId} onChange={e=>setProfileId(e.target.value)}><option value="">Crear nuevo perfil</option>{profiles.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>{!profileId&&<label className="field"><span>Nombre del perfil</span><input required value={profileName} maxLength={100} onChange={e=>setProfileName(e.target.value)} placeholder="Calendario del hotel"/></label>}</div>
      <label className="import-upload"><Upload size={24}/><strong>Seleccionar Excel o CSV</strong><span>.xlsx con notas y colores · CSV exportado por el PMS · máximo 5 MB</span><input type="file" name="file" accept=".xlsx,.csv" required /></label>
      <button className="button primary" disabled={busy}><FileSpreadsheet size={17}/>{busy?"Analizando…":"Analizar archivo"}</button>
    </form><section className="panel import-section"><h2>Importaciones anteriores</h2>{history.length?<div className="import-history">{history.map(h=><button className="button" key={h.id} disabled={busy} onClick={()=>void work(async()=>{adopt(await api.getDraft(h.id));setStep(h.state==="APPLIED"?3:1);})}>Lote {h.id} · {h.filename||"Descartado"} · {h.state==="DRAFT"?"Borrador":h.state==="APPLIED"?"Aplicado":"Descartado"}</button>)}</div>:<p className="muted">Todavía no hay importaciones.</p>}</section></>:<>
      <nav className="import-steps" aria-label="Etapas de importación">{["Archivo","Períodos","Unidades","Revisión"].map((name,i)=><span key={name} className={step===i?"current":step>i?"done":""}><b>{i+1}</b>{name}</span>)}</nav>
      <section className="import-meta"><strong>{draft.filename||"Borrador descartado"}</strong><span>Lote {draft.id} · {draft.state==="APPLIED"?"Aplicado":draft.state==="DISCARDED"?"Descartado":"Borrador"}</span><span>{draft.source_summary?.sheets.reduce((n,s)=>n+s.notes,0)||0} notas de origen</span></section>
      {draft.state==="APPLIED"?<section className="panel import-section"><CheckCircle2 size={32}/><h2>Importación aplicada</h2><p>{draft.batch?.actions.length} reservas procesadas. Las cuentas nuevas quedan pendientes de revisión.</p><p>Registro de lote: {draft.batch?.id}</p></section>:draft.state==="DISCARDED"?<p className="panel import-section">Se descartó el archivo y sus datos personales.</p>:<fieldset className="import-fieldset" disabled={busy}>
        {step===1&&<SourceStep draft={draft} configuration={configuration} onChange={c=>{setConfiguration(c);setDirty(true);setConfirmation(false);}}/>}
        {step===2&&<MappingStep draft={draft} data={data} configuration={configuration} onChange={c=>{setConfiguration(c);setDirty(true);setConfirmation(false);}}/>}
        {step===3&&<ReviewStep draft={draft} data={data} decisions={decisions} onChange={d=>{setDecisions(d);setDirty(true);setConfirmation(false);}}/>}
      </fieldset>}
      {draft.state==="DRAFT"&&<div className="import-sticky">
        <div><strong>{draft.preview.rows?.filter(r=>r.selected).length||0} reservas seleccionadas</strong><small className="block muted">{dirty?"Hay cambios sin guardar":"Revisión guardada"} · {draft.preview.pending_notes?.length||0} notas pendientes</small></div>
        <div className="actions">{step>1&&<button className="button" disabled={busy} onClick={()=>setStep(step-1)}>Volver</button>}
        {step<3?<button className="button primary" disabled={busy} onClick={()=>void save(step+1)}>Guardar y continuar<ArrowRight size={16}/></button>:<><button className="button" disabled={busy} onClick={()=>void save()}><Save size={16}/>Guardar revisión</button><button className="button primary" disabled={busy||dirty||!draft.preview.can_apply} onClick={()=>setConfirmation(true)}>Revisar aplicación</button></>}</div>
      </div>}
      {confirmation&&draft.state==="DRAFT"&&<section className="panel import-section" role="region" aria-label="Confirmar importación"><h2>Confirmar cambios en el hotel</h2><p>Se aplicarán las filas seleccionadas: {Object.entries(draft.preview.summary||{}).map(([a,n])=>`${n} ${({CREATE:"altas",UPDATE:"actualizaciones",UNCHANGED:"sin cambios"} as Record<string,string>)[a]||a}`).join(" · ")}.</p><p>Se validará nuevamente la disponibilidad. Un conflicto revierte todo el lote.</p><div className="actions"><button className="button primary" disabled={busy||dirty} onClick={()=>void work(async()=>{adopt(await api.apply(draft));await onApplied();await refresh();setNotice("Reservas incorporadas al PMS.");})}>Confirmar importación</button><button className="button" disabled={busy} onClick={()=>setConfirmation(false)}>Volver a revisar</button></div></section>}
      <div className="actions import-secondary">
        <button className="button" disabled={busy||dirty||(!draft.preview.can_apply&&draft.state!=="APPLIED")} onClick={()=>void work(()=>api.download(draft.id))}><Download size={16}/>Exportar CSV</button>
        <button className="button" disabled={busy||dirty||draft.state!=="DRAFT"} onClick={()=>void work(async()=>{await api.saveProfile(draft.profile_id,configuration);await refresh();setNotice("Perfil guardado para futuras cargas.");})}>Guardar perfil para próximas cargas</button>
        <button className="button" disabled={busy} onClick={()=>{setDraft(null);setStep(0);setError("");}}>Volver a archivos</button>
        {draft.state==="DRAFT"&&<button className="text-button" disabled={busy} onClick={()=>setDiscardConfirmation(true)}>Descartar borrador</button>}
      </div>
      {discardConfirmation&&draft.state==="DRAFT"&&<section className="panel import-section"><h3>Descartar archivo y revisión</h3><p>Se eliminarán los datos del archivo de este borrador.</p><button className="button danger" disabled={busy} onClick={()=>void work(async()=>{adopt(await api.discard(draft));setDiscardConfirmation(false);await refresh();})}>Confirmar descarte</button><button className="button" onClick={()=>setDiscardConfirmation(false)}>Volver</button></section>}
    </>}
  </div>;
}
