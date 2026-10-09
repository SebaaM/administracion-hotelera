import csv,json,uuid
from io import StringIO
from datetime import date
from rest_framework.exceptions import ValidationError
from .readers import LIMIT

HEADERS=["id_origen","huésped","unidad_origen","llegada","salida","estado","observaciones","colores","referencias"]
TEXT_FIELDS=["huésped","unidad_origen","observaciones"]
def write_csv(candidates):
    stream=StringIO(newline="");writer=csv.DictWriter(stream,fieldnames=HEADERS);writer.writeheader()
    for c in candidates:
        notes=c.get("notes",[])
        references=list(c.get("references",[]))
        row={"id_origen":c["source_id"],"huésped":c["guest"],"unidad_origen":c["source_unit"],
            "llegada":c["start"],"salida":c["end"],"estado":c.get("status","CONFIRMED"),
            "observaciones":json.dumps(notes,ensure_ascii=False),"colores":json.dumps(c.get("colors",[]),ensure_ascii=False)}
        protected=[]
        for field in TEXT_FIELDS:
            if row[field].lstrip().startswith(("=","+","-","@")):
                row[field]="'"+row[field];protected.append(field)
        references.append({"csv_metadata":True,"protected":protected})
        row["referencias"]=json.dumps(references,ensure_ascii=False);writer.writerow(row)
    return stream.getvalue().encode("utf-8-sig")

def read_csv(content):
    if not content or len(content)>LIMIT:raise ValidationError("El CSV no puede superar 5 MB.")
    try:
        reader=csv.DictReader(StringIO(content.decode("utf-8-sig"),newline=""))
        if reader.fieldnames!=HEADERS:raise ValueError("encabezados")
        rows=[];ids=set()
        for index,row in enumerate(reader):
            if index>=10000 or None in row or any(v is None for v in row.values()):raise ValueError("columnas")
            sid=str(uuid.UUID(row["id_origen"]))
            if sid in ids:raise ValueError("identificador duplicado")
            ids.add(sid)
            refs=json.loads(row["referencias"]);colors=json.loads(row["colores"]);notes=json.loads(row["observaciones"])
            if not all(isinstance(v,list) for v in (refs,colors,notes)):raise ValueError("metadatos")
            protected=[f for r in refs if isinstance(r,dict) and r.get("csv_metadata") for f in r.get("protected",[])]
            refs=[r for r in refs if not (isinstance(r,dict) and r.get("csv_metadata"))]
            for field in protected:
                if field not in TEXT_FIELDS or not row[field].startswith("'"):raise ValueError("protección")
                row[field]=row[field][1:]
            for note in notes:
                if not isinstance(note,dict) or not isinstance(note.get("text"),str) or not isinstance(note.get("refs"),list):raise ValueError("nota")
            for color in colors:
                if not isinstance(color,dict) or not isinstance(color.get("hex"),str):raise ValueError("color")
            start=date.fromisoformat(row["llegada"]);end=date.fromisoformat(row["salida"])
            if end<=start or (end-start).days>366:raise ValueError("fechas")
            if row["estado"] not in ("CONFIRMED","IN_HOUSE","CHECKED_OUT","CANCELLED"):raise ValueError("estado")
            rows.append({"key":sid,"source_id":sid,"source_unit":row["unidad_origen"],"guest":row["huésped"],
                "start":start.isoformat(),"end":end.isoformat(),"status":row["estado"],"notes":notes,"colors":colors,
                "references":refs,"warnings":[]})
        if not rows:raise ValueError("sin reservas")
        return rows
    except (ValueError,TypeError,KeyError,csv.Error,UnicodeError) as exc:
        raise ValidationError("CSV inválido: usá el formato exportado por el PMS, con identificadores únicos y fechas válidas.") from exc
