import re
from rest_framework import serializers

class StrictSerializer(serializers.Serializer):
    def to_internal_value(self,data):
        unknown=set(data)-set(self.fields)
        if unknown:raise serializers.ValidationError({"non_field_errors": ["Campos desconocidos: "+", ".join(sorted(unknown))]})
        return super().to_internal_value(data)

def validate_configuration(value):
    if not isinstance(value,dict):raise serializers.ValidationError("La configuración debe ser un objeto.")
    if set(value)-{"sheets","mapping","mapping_confirmed","legend"}:raise serializers.ValidationError("Configuración desconocida.")
    mapping=value.get("mapping",{})
    if not isinstance(mapping,dict) or any(not isinstance(k,str) or not isinstance(v,int) or isinstance(v,bool) or v<1 for k,v in mapping.items()):
        raise serializers.ValidationError("El mapa debe vincular etiquetas con identificadores de unidad.")
    if not isinstance(value.get("mapping_confirmed",False),bool):raise serializers.ValidationError("La confirmación del mapa debe ser booleana.")
    legend=value.get("legend",{})
    if not isinstance(legend,dict) or any(not re.fullmatch(r"#[0-9a-fA-F]{6}",k) or not isinstance(v,str) or len(v)>120 for k,v in legend.items()):
        raise serializers.ValidationError("La leyenda debe usar colores hexadecimales y textos.")
    sheets=value.get("sheets",[])
    if not isinstance(sheets,list) or len(sheets)>20:raise serializers.ValidationError("La configuración admite hasta 20 hojas.")
    for s in sheets:
        if not isinstance(s,dict) or set(s)!={"name","year","month","label_col","header_rows","unit_rows"}:raise serializers.ValidationError("Faltan campos en la configuración de hojas.")
        if not isinstance(s["name"],str):raise serializers.ValidationError("Nombre de hoja inválido.")
        for field,minimum,maximum in (("year",1900,2200),("month",1,12),("label_col",1,400)):
            if not isinstance(s[field],int) or isinstance(s[field],bool) or not minimum<=s[field]<=maximum:raise serializers.ValidationError("Período o columna de etiquetas inválidos.")
        for field in ("header_rows","unit_rows"):
            if not isinstance(s[field],list) or any(not isinstance(v,int) or isinstance(v,bool) or not 1<=v<=5000 for v in s[field]):raise serializers.ValidationError("Filas de hoja inválidas.")
    return value

class ProfileInput(StrictSerializer):
    name=serializers.CharField(max_length=100)
    configuration=serializers.JSONField(required=False)
    def validate_configuration(self,value):return validate_configuration(value)

class UploadInput(StrictSerializer):
    file=serializers.FileField(max_length=200)
    profile_id=serializers.IntegerField(min_value=1)

class RevisionInput(StrictSerializer):
    expected_revision=serializers.IntegerField(min_value=1)

class DraftInput(RevisionInput):
    configuration=serializers.JSONField(required=False)
    decisions=serializers.JSONField(required=False)
    def validate_configuration(self,value):return validate_configuration(value)

def validate_decisions(value,draft):
    if not isinstance(value,dict) or set(value)-{"rows","notes","joins"}:raise serializers.ValidationError("Decisiones inválidas.")
    rows=value.get("rows",{});notes=value.get("notes",{});joins=value.get("joins",[])
    if not isinstance(rows,dict) or not isinstance(notes,dict) or not isinstance(joins,list):raise serializers.ValidationError("Filas, notas o uniones inválidas.")
    if len(rows)>10000 or len(notes)>10000:raise serializers.ValidationError("Demasiadas decisiones en el borrador.")
    fields={"selected","guest","start","end","status","unit_id","reservation_id","reviewed","new_confirmed"}
    for key,row in rows.items():
        if not isinstance(row,dict) or set(row)-fields:raise serializers.ValidationError("Campos desconocidos en una fila.")
        for field in ("selected","reviewed","new_confirmed"):
            if field in row and not isinstance(row[field],bool):raise serializers.ValidationError("La confirmación de una fila debe ser booleana.")
        for field in ("unit_id","reservation_id"):
            if field in row and row[field] is not None and (not isinstance(row[field],int) or isinstance(row[field],bool) or row[field]<1):raise serializers.ValidationError("Identificador inválido.")
        for field in ("guest","start","end","status"):
            if field in row and not isinstance(row[field],str):raise serializers.ValidationError("Nombre, fechas y estado deben ser textos.")
    known={s["name"]+"!"+c["ref"] for s in draft.source.get("sheets",[]) for c in s["cells"] if c.get("note")}
    for key,note in notes.items():
        if key not in known or not isinstance(note,dict) or set(note)-{"action","target","reason"} or note.get("action") not in ("ASSIGN","EXCLUDE"):
            raise serializers.ValidationError("Decisión de nota inválida.")
        if note["action"]=="EXCLUDE" and not isinstance(note.get("reason"),str):raise serializers.ValidationError("Explicá la exclusión de la nota.")
        if note["action"]=="ASSIGN" and not isinstance(note.get("target"),str):raise serializers.ValidationError("Elegí una reserva para la nota.")
    if any(not isinstance(group,list) or any(not isinstance(key,str) for key in group) for group in joins):raise serializers.ValidationError("Unión inválida.")
    return value
