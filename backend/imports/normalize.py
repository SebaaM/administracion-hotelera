from datetime import date,timedelta
from calendar import monthrange
from rest_framework.exceptions import ValidationError

DEFAULT_LEGEND={"#FF0000":"Check out","#0070C0":"Cambio de habitación: sale","#FF00FF":"Cambio de habitación: entra","#C6EFCE":"Pagado","#FFE598":"Falta pagar","#00FF00":"Llegó; falta entregar llave","#00FFFF":"Pedido especial","#00B0F0":"Agencia","#FFFF00":"Llegó; no pagó y falta entregar llave","#6D9EEB":"Liquidado Despegar","#9900FF":"Pagado Despegar"}

def add_note(notes,text,ref):
    if not text:return
    existing=next((n for n in notes if n["text"]==text),None)
    if existing:
        if ref not in existing["refs"]:existing["refs"].append(ref)
    else:notes.append({"text":text,"refs":[ref]})

def normalize_calendar(source,sheets,legend):
    result=[]
    names=[c["name"] for c in sheets]
    if len(names)!=len(set(names)):raise ValidationError("No repitas hojas en la configuración.")
    for config in sheets:
        sheet=next((s for s in source["sheets"] if s["name"]==config["name"]),None)
        if sheet is None:raise ValidationError("Una hoja seleccionada no existe.")
        try:
            year=int(config["year"]);month=int(config["month"])
            if not 1900<=year<=2200:raise ValueError()
            last=monthrange(year,month)[1]
            label_col=int(config["label_col"]);headers=sorted(set(map(int,config["header_rows"])))
            unit_rows=list(map(int,config["unit_rows"]))
            if not headers or not unit_rows or len(unit_rows)!=len(set(unit_rows)):raise ValueError()
        except (ValueError,KeyError,TypeError):raise ValidationError("Confirmá año, mes, encabezados y filas de unidades válidos.")
        cells={(c["row"],c["col"]):c for c in sheet["cells"]};seen=set()
        for row in unit_rows:
            if row in headers:raise ValidationError("Una fila de unidades también está marcada como encabezado.")
            unit=cells.get((row,label_col),{}).get("value","")
            if not unit or unit in seen:raise ValidationError("Las etiquetas de unidades deben existir y ser únicas en cada hoja.")
            seen.add(unit)
            header=max((r for r in headers if r<row),default=0)
            if not header:raise ValidationError("Falta un encabezado de días antes de una unidad.")
            days=[]
            for (r,col),cell in cells.items():
                if r!=header or col<=label_col:continue
                try:day=int(cell["value"])
                except (TypeError,ValueError):continue
                if day<1 or day>last:raise ValidationError("El encabezado contiene un día fuera del mes.")
                days.append((day,col))
            if not days or len(days)!=len(set(d for d,c in days)):raise ValidationError("Los días del encabezado deben ser únicos.")
            current=None
            for day,col in sorted(days):
                cell=cells.get((row,col),{})
                guest=cell.get("value","").strip();dt=date(year,month,day)
                ref={"sheet":sheet["name"],"cell":cell.get("ref","")}
                if cell.get("color")=="#FF0000":
                    if guest:
                        if current and current["guest"]==guest and current["end"]==dt.isoformat():
                            current["warnings"].append("Hay nombre en una celda de salida: confirmá las fechas.")
                            add_note(current["notes"],cell.get("note",""),ref)
                            current["references"].append(ref)
                            current["colors"].append({"hex":"#FF0000",**ref,"meaning":legend.get("#FF0000","Check out")})
                        else:
                            result.append({"key":f'{sheet["name"]}:{row}:{day}',"source_id":"","source_unit":unit,
                                "guest":guest,"start":dt.isoformat(),"end":(dt+timedelta(days=1)).isoformat(),
                                "notes":[{"text":cell["note"],"refs":[ref]}] if cell.get("note") else [],
                                "colors":[{"hex":"#FF0000",**ref,"meaning":legend.get("#FF0000","Check out")}],
                                "references":[ref],"warnings":["Celda de salida sin estadía anterior: corregí fechas antes de importar."]})
                    current=None;continue
                if not guest:current=None;continue
                if not current or current["guest"]!=guest or current["end"]!=dt.isoformat():
                    current={"key":f'{sheet["name"]}:{row}:{day}',"source_id":"","source_unit":unit,"guest":guest,
                        "start":dt.isoformat(),"end":dt.isoformat(),"notes":[],"colors":[],"references":[],
                        "warnings":list(sheet.get("warnings",[]))}
                    result.append(current)
                current["end"]=(dt+timedelta(days=1)).isoformat()
                current["references"].append(ref)
                add_note(current["notes"],cell.get("note",""),ref)
                if cell.get("color"):current["colors"].append({"hex":cell["color"],**ref,"meaning":legend.get(cell["color"],"Sin significado confirmado")})
                if cell.get("kind")=="f":current["warnings"].append("La celda contiene una fórmula: escribí el nombre del huésped.")
                if day==1 or day==last:current["warnings"].append("La estadía toca un límite mensual: confirmá continuidad y fechas.")
    return result
