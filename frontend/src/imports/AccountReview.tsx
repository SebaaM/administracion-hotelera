import {useState} from "react";
import type {Reservation,Perform} from "../types";
import {api} from "../api";
export function AccountReview({snapshot,perform,busy,onClose}:{snapshot:Reservation;perform:Perform;busy:boolean;onClose:()=>void}){
  const [zero,setZero]=useState(false);
  return <section className="inline-form" aria-label="Confirmar revisión de cuenta">
    <h3>Confirmar conciliación</h3><p>Verificá los cargos y cobros con la planilla de origen. Esta confirmación registra quién revisó la cuenta.</p>
    <p>{snapshot.ledger.length} movimientos en la cuenta que estás revisando.</p>
    {!snapshot.ledger.length&&<label className="import-check"><input type="checkbox" checked={zero} onChange={e=>setZero(e.target.checked)}/>Confirmo que esta estadía no tiene cargos ni cobros pendientes de cargar.</label>}
    <div className="actions"><button className="button primary" disabled={busy||(!snapshot.ledger.length&&!zero)} onClick={()=>void perform(()=>api(`reservations/${snapshot.id}/account-review/`,"POST",{expected_updated_at:snapshot.updated_at,ledger_signature:snapshot.ledger_signature,confirmed_zero:zero}),"Cuenta revisada").then(ok=>{if(ok)onClose();})}>Confirmar cuenta revisada</button><button className="button" onClick={onClose}>Volver</button></div>
  </section>;
}
