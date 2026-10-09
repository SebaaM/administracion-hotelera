import copy,hashlib,json,uuid
from collections import Counter
from datetime import date
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from pms.models import Reservation,Unit,Allocation,Maintenance
from pms.views import reservation_data
from .models import ImportBinding
from .normalize import normalize_calendar,add_note

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def identity(c):
    return digest({k:c[k] for k in ("source_unit","guest","start","end")})

def snapshot(reservation):
    return digest(reservation_data(reservation))

def notes_text(notes):
    return "\n\n".join(n["text"]+"\nOrigen: "+", ".join(f'{r.get("sheet","")}!{r.get("cell","")}' for r in n["refs"]) for n in notes)

def candidates_for(draft):
    if draft.source.get("format")=="csv":rows=copy.deepcopy(draft.source["candidates"])
    else:rows=normalize_calendar(draft.source,draft.configuration.get("sheets",[]),draft.configuration.get("legend",{}))
    by_key={r["key"]:r for r in rows}
    if len(by_key)!=len(rows):raise ValidationError("Hay filas de origen duplicadas.")
    used=set()
    for group in draft.decisions.get("joins",[]):
        if not isinstance(group,list) or len(group)<2 or any(k not in by_key or k in used for k in group):
            raise ValidationError("La unión de estadías no es válida.")
        members=sorted((by_key[k] for k in group),key=lambda c:c["start"])
        first=members[0]
        for previous,current in zip(members,members[1:]):
            if previous["end"]!=current["start"] or current["source_unit"]!=first["source_unit"] or current["guest"]!=first["guest"]:
                raise ValidationError("Solo se pueden unir tramos contiguos de la misma persona y unidad.")
            first["end"]=current["end"];first["references"]+=current["references"];first["colors"]+=current["colors"]
            for note in current["notes"]:
                for ref in note["refs"]:add_note(first["notes"],note["text"],ref)
            used.add(current["key"])
        first["warnings"]=["Continuidad entre hojas confirmada: revisá fechas finales."]
    return [r for r in rows if r["key"] not in used]

def pending_notes(draft,candidates,note_decisions,row_decisions):
    associated={(r.get("sheet"),r.get("cell")) for c in candidates for r in c["references"]}
    by_key={c["key"]:c for c in candidates}
    pending=[]
    selected={s["name"] for s in draft.configuration.get("sheets",[])}
    for sheet in draft.source.get("sheets",[]):
        if sheet["name"] not in selected:continue
        for cell in sheet["cells"]:
            if not cell.get("note") or (sheet["name"],cell["ref"]) in associated:continue
            ref={"sheet":sheet["name"],"cell":cell["ref"]};key=sheet["name"]+"!"+cell["ref"]
            decision=note_decisions.get(key,{})
            if decision.get("action")=="EXCLUDE" and str(decision.get("reason","")).strip():continue
            if decision.get("action")=="ASSIGN" and decision.get("target") in by_key and row_decisions.get(decision["target"],{}).get("selected",True):
                add_note(by_key[decision["target"]]["notes"],cell["note"],ref)
                continue
            pending.append({"key":key,**ref,"text":cell["note"]})
    return pending

def build_preview(draft,decisions,note_decisions):
    candidates=candidates_for(draft);keys={c["key"] for c in candidates}
    if any(key not in keys for key in decisions):raise ValidationError("Una decisión no corresponde al borrador actual.")
    pending=pending_notes(draft,candidates,note_decisions,decisions)
    result=[];mapping=draft.configuration.get("mapping",{})
    for c in candidates:
        c["origin_signature"]=identity(c)
        decision=decisions.get(c["key"],{})
        selected=decision.get("selected",True)
        if not isinstance(selected,bool):raise ValidationError("La selección debe ser verdadera o falsa.")
        c["guest"]=str(decision.get("guest",c["guest"])).strip()
        c["start"]=decision.get("start",c["start"]);c["end"]=decision.get("end",c["end"])
        c["status"]=decision.get("status",c.get("status") or ("CHECKED_OUT" if c["end"]<=timezone.localdate().isoformat() else "CONFIRMED"))
        c["notes_text"]=notes_text(c["notes"])
        errors=[];action="CREATE";reservation=None;binding=None;suggestions=[]
        if not c["guest"] or len(c["guest"])>120:errors.append("El nombre es obligatorio y admite hasta 120 caracteres.")
        try:
            start=date.fromisoformat(c["start"]);end=date.fromisoformat(c["end"])
            if end<=start or (end-start).days>366:raise ValueError()
        except (ValueError,TypeError):errors.append("La estadía debe durar entre 1 y 366 noches.");start=end=None
        if c["status"] not in ("CONFIRMED","IN_HOUSE","CHECKED_OUT","CANCELLED"):errors.append("Elegí un estado válido.")
        if not decision.get("reviewed",False):errors.append("Confirmá la revisión de fechas y estado.")
        if not draft.configuration.get("mapping_confirmed"):errors.append("Confirmá el mapa de unidades.")
        try:
            unit_id=int(decision.get("unit_id",mapping.get(c["source_unit"],0)))
            unit=Unit.objects.select_related("room").filter(pk=unit_id).first()
        except (ValueError,TypeError):unit=None
        c["unit_id"]=unit.pk if unit else None
        if not unit:errors.append("Vinculá una habitación o cama.")
        if unit and (not unit.active or not unit.room.active):errors.append("La unidad está desactivada.");action="CONFLICT"
        source_id=c.get("source_id")
        if source_id:
            try:binding=ImportBinding.objects.filter(profile=draft.profile,source_id=uuid.UUID(source_id)).select_related("reservation").first()
            except (ValueError,TypeError):errors.append("El identificador de origen no es válido.")
        else:
            matches=list(ImportBinding.objects.filter(profile=draft.profile,signature=c["origin_signature"]).select_related("reservation"))
            if len(matches)==1:binding=matches[0]
        target=decision.get("reservation_id")
        if target:
            try:reservation=Reservation.objects.filter(pk=int(target)).first()
            except (ValueError,TypeError):reservation=None
            if reservation is None:errors.append("La reserva elegida no existe.")
            if binding and reservation and binding.reservation_id!=reservation.pk:errors.append("El identificador pertenece a otra reserva.")
        elif binding:reservation=binding.reservation
        if reservation:
            action="UPDATE"
            allocations=list(reservation.allocations.all())
            if len(allocations)!=1:errors.append("Esta reserva tiene varias unidades: revisala desde el PMS.")
            changed=start!=reservation.start or end!=reservation.end or c["status"]!=reservation.status or not allocations or allocations[0].unit_id!=c["unit_id"]
            if changed and reservation.status!="CONFIRMED":errors.append("Una estadía operativa no permite cambiar fechas, unidad o estado desde la importación.")
            same=not changed and c["guest"]==reservation.guest and c["notes_text"]==reservation.import_notes and c["colors"]==reservation.import_colors
            if same:action="UNCHANGED"
            existing_binding=ImportBinding.objects.filter(profile=draft.profile,reservation=reservation).first()
            if existing_binding and source_id and str(existing_binding.source_id)!=source_id:errors.append("La reserva ya tiene otro identificador dentro del perfil.")
            if existing_binding:binding=existing_binding
        else:
            suggestions=list(Reservation.objects.filter(Q(guest=c["guest"])|Q(allocations__unit_id=c["unit_id"],start=c["start"])).distinct().values("id","guest","start","end")[:15]) if start else []
            if suggestions and not decision.get("new_confirmed"):errors.append("Hay coincidencias posibles: elegí una reserva o confirmá que es nueva.")
        if c["status"]=="IN_HOUSE" and start and not start<=timezone.localdate()<end:errors.append("Solo se puede importar como alojado dentro de las fechas de estadía.")
        if unit and start and c["status"] in ("CONFIRMED","IN_HOUSE"):
            overlap=Allocation.objects.filter(unit=unit,active=True,start__lt=end,end__gt=start)
            occupied=Allocation.objects.filter(unit=unit,reservation__status="IN_HOUSE")
            if reservation:overlap=overlap.exclude(reservation=reservation);occupied=occupied.exclude(reservation=reservation)
            if overlap.exists() or (start<=timezone.localdate()<end and occupied.exists()):
                errors.append("La unidad tiene otra reserva o un huésped alojado.");action="CONFLICT"
            blocked=Maintenance.objects.filter(room_id=unit.room_id,blocking=True,start__lt=end,end__gt=start).exclude(status="DONE").filter(Q(unit__isnull=True)|Q(unit=unit))
            if blocked.exists():errors.append("Hay un bloqueo de mantenimiento.");action="CONFLICT"
            if c["status"]=="IN_HOUSE" and unit.cleaning!="CLEAN":errors.append("La unidad debe estar limpia para alojar al huésped.")
        if errors and action!="CONFLICT":action="REVIEW"
        c["source_id"]=str(binding.source_id) if binding else source_id or str(uuid.uuid5(uuid.NAMESPACE_URL,f"pms:{draft.profile_id}:{draft.pk}:{c['key']}"))
        result.append({"key":c["key"],"selected":selected,"action":action,"errors":errors,"candidate":c,
            "reservation_id":reservation.pk if reservation else None,"before":json.loads(json.dumps(reservation_data(reservation),default=str)) if reservation else None,
            "snapshot":snapshot(reservation) if reservation else "","suggestions":[{**s,"start":str(s["start"]),"end":str(s["end"])} for s in suggestions]})
    targets=Counter(r["reservation_id"] for r in result if r["selected"] and r["reservation_id"])
    for r in result:
        if targets[r["reservation_id"]]>1:
            r["errors"].append("Varias filas intentan actualizar la misma reserva.");r["action"]="REVIEW"
    selected_rows=[r for r in result if r["selected"]]
    for index,r in enumerate(selected_rows):
        c=r["candidate"]
        if c["status"] not in ("CONFIRMED","IN_HOUSE") or not c["unit_id"]:continue
        for other in selected_rows[index+1:]:
            o=other["candidate"]
            if o["status"] in ("CONFIRMED","IN_HOUSE") and c["unit_id"]==o["unit_id"] and c["start"]<o["end"] and c["end"]>o["start"]:
                for row in (r,other):row["action"]="CONFLICT";row["errors"].append("Hay otra fila seleccionada en la misma unidad y fechas.")
    summary=dict(Counter(r["action"] for r in selected_rows))
    return {"rows":result,"pending_notes":pending,"summary":summary,"revision":draft.revision,
        "can_apply":bool(selected_rows) and not pending and all(not r["errors"] for r in selected_rows)}
