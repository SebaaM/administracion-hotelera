import csv,json,uuid,re
from io import StringIO
from datetime import date
from rest_framework.exceptions import ValidationError
from .readers import LIMIT

HEADERS=["id_origen","huésped","unidad_origen","llegada","salida","estado","observaciones","colores","referencias"]
TEXT_FIELDS=["huésped","unidad_origen","observaciones"]
# El máximo de campo coincide con el máximo de archivo, también para notas extensas.
csv.field_size_limit(LIMIT)

def valid_reference(ref):
    if not isinstance(ref,dict) or set(ref)!={"sheet","cell"} or not all(isinstance(ref[k],str) for k in ("sheet","cell")):
        raise ValueError("referencia")
    if len(ref["sheet"])>255 or len(ref["cell"])>50:raise ValueError("referencia")

def validate_metadata(refs,colors,notes):
    if not all(isinstance(value,list) for value in (refs,colors,notes)):raise ValueError("metadatos")
    protected=[];references=[]
    for ref in refs:
        if isinstance(ref,dict) and "csv_metadata" in ref:
            fields=ref.get("protected")
            if set(ref)!={"csv_metadata","protected"} or ref["csv_metadata"] is not True or not isinstance(fields,list):
                raise ValueError("protección")
            if not all(isinstance(field,str) and field in TEXT_FIELDS for field in fields):raise ValueError("protección")
            protected+=fields
        else:
            valid_reference(ref);references.append(ref)
    if len(protected)!=len(set(protected)):raise ValueError("protección repetida")
    for note in notes:
        if not isinstance(note,dict) or set(note)!={"text","refs"} or not isinstance(note["text"],str) or not isinstance(note["refs"],list):
            raise ValueError("nota")
        for ref in note["refs"]:valid_reference(ref)
    for color in colors:
        if not isinstance(color,dict) or set(color)-{"hex","meaning","sheet","cell"} or not isinstance(color.get("hex"),str):
            raise ValueError("color")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}",color["hex"]):raise ValueError("color")
        if any(not isinstance(value,str) for value in color.values()):raise ValueError("color")
    return references,protected

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
            refs,protected=validate_metadata(refs,colors,notes)
            for field in protected:
                if not row[field].startswith("'"):raise ValueError("protección")
                row[field]=row[field][1:]
            start=date.fromisoformat(row["llegada"]);end=date.fromisoformat(row["salida"])
            if end<=start or (end-start).days>366:raise ValueError("fechas")
            if row["estado"] not in ("CONFIRMED","IN_HOUSE","CHECKED_OUT","CANCELLED"):raise ValueError("estado")
            rows.append({"key":sid,"source_id":sid,"source_unit":row["unidad_origen"],"guest":row["huésped"],
                "start":start.isoformat(),"end":end.isoformat(),"status":row["estado"],"notes":notes,"colors":colors,
                "references":refs,"warnings":[]})
        if not rows:raise ValueError("sin reservas")
        return rows
    except (ValueError,TypeError,KeyError,csv.Error,UnicodeError,RecursionError) as exc:
        raise ValidationError("CSV inválido: usá el formato exportado por el PMS, con identificadores únicos y fechas válidas.") from exc
