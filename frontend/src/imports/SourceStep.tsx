import type {Configuration,Draft,SheetConfig} from "./types";
import {Field} from "../ui";
export function SourceStep({draft,configuration,onChange}:{draft:Draft;configuration:Configuration;onChange:(c:Configuration)=>void}) {
  const sheets=configuration.sheets||[];
  function change(name:string,patch:Partial<SheetConfig>){onChange({...configuration,sheets:sheets.map(s=>s.name===name?{...s,...patch}:s)});}
  const suggestions=draft.sheet_suggestions||sheets;
  return <section className="panel import-section">
    <h2>1. Confirmar períodos y filas</h2>
    <p className="muted">Cada celda con el huésped representa una noche. La salida es el día posterior a la última noche.</p>
    {draft.source_summary?.format==="csv"?<p>CSV normalizado: las fechas y observaciones ya están en columnas explícitas.</p>:suggestions.map(s=>{
      const selected=sheets.find(x=>x.name===s.name);
      return <div className="import-sheet" key={s.name}>
        <label className="import-check"><input type="checkbox" checked={!!selected} onChange={e=>onChange({...configuration,sheets:e.target.checked?[...sheets,s]:sheets.filter(x=>x.name!==s.name)})}/><strong>{s.name}</strong></label>
        {selected&&<div className="form-grid">
          <Field label="Año"><input type="number" min={1900} max={2200} value={selected.year} onChange={e=>change(s.name,{year:Number(e.target.value)})}/></Field>
          <Field label="Mes"><select value={selected.month} onChange={e=>change(s.name,{month:Number(e.target.value)})}><option value={0}>Elegir mes</option>{["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"].map((m,i)=><option value={i+1} key={m}>{m}</option>)}</select></Field>
          <Field label="Columna de etiquetas (A = 1)"><input type="number" min={1} max={400} value={selected.label_col} onChange={e=>change(s.name,{label_col:Number(e.target.value)})}/></Field>
          <Field label="Filas de días, separadas por coma"><input defaultValue={selected.header_rows.join(", ")} onBlur={e=>change(s.name,{header_rows:e.target.value.split(",").map(x=>Number(x.trim())).filter(x=>x>0)})}/></Field>
          <Field label="Filas de camas/habitaciones"><input defaultValue={selected.unit_rows.join(", ")} onBlur={e=>change(s.name,{unit_rows:e.target.value.split(",").map(x=>Number(x.trim())).filter(x=>x>0)})}/></Field>
        </div>}
      </div>;
    })}
    <p className="import-hint">Las fechas originales se conservarán. No se trasladan las reservas a la fecha actual.</p>
  </section>;
}
