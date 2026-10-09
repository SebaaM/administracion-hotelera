import type {State} from "../types";
import type {Configuration,Draft} from "./types";
import {Field} from "../ui";
export function MappingStep({draft,data,configuration,onChange}:{draft:Draft;data:State;configuration:Configuration;onChange:(c:Configuration)=>void}){
  const labels=draft.source_units||[];
  const colors=Array.from(new Set(draft.source_summary?.sheets.flatMap(s=>Object.keys(s.colors))||[]));
  return <section className="panel import-section">
    <h2>2. Vincular habitaciones y camas</h2>
    <p className="muted">Cada etiqueta de la planilla debe apuntar a una unidad del hotel. Las unidades faltantes se crean en Configuración.</p>
    <div className="import-mapping">{labels.map(label=><Field label={label} key={label}><select value={configuration.mapping?.[label]||""} onChange={e=>{
      const mapping={...configuration.mapping};if(e.target.value)mapping[label]=Number(e.target.value);else delete mapping[label];
      onChange({...configuration,mapping,mapping_confirmed:false});
    }}><option value="">Sin vincular</option>{data.units.filter(u=>u.active&&data.rooms.find(r=>r.id===u.room_id)?.active).map(u=><option key={u.id} value={u.id}>{data.rooms.find(r=>r.id===u.room_id)?.name} · {u.name}</option>)}</select></Field>)}</div>
    <label className="import-check"><input type="checkbox" checked={configuration.mapping_confirmed||false} onChange={e=>onChange({...configuration,mapping_confirmed:e.target.checked})}/>Confirmé la asociación de las unidades seleccionadas.</label>
    <details className="import-legend"><summary>Revisar leyenda de colores ({colors.length})</summary>
      <p>Los colores se conservan como información de origen. Los cobros se registran después de verificar los importes.</p>
      {colors.map(hex=><div className="import-color-edit" key={hex}><span className="import-color" style={{background:hex}}/><code>{hex}</code><input aria-label={`Significado de ${hex}`} value={configuration.legend?.[hex]||""} placeholder="Sin significado confirmado" maxLength={120} onChange={e=>onChange({...configuration,legend:{...configuration.legend,[hex]:e.target.value}})}/></div>)}
    </details>
  </section>;
}
