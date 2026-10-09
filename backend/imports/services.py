import copy,hashlib
from pathlib import Path
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import ImportDraft
from .readers import read_xlsx,suggest_configuration
from .csv_io import read_csv
from .normalize import DEFAULT_LEGEND
from .preview import build_preview

def check_version(draft,expected):
    if draft.revision!=expected:raise ValidationError("El borrador cambió. Volvé a cargarlo antes de guardar.")
    if draft.state!="DRAFT":raise ValidationError("El borrador ya fue aplicado o descartado.")

def create_draft(content,filename,profile,user):
    extension=Path(filename).suffix.lower()
    if extension==".xlsx":source=read_xlsx(content)
    elif extension==".csv":source={"format":"csv","sheets":[],"candidates":read_csv(content)}
    else:raise ValidationError("Subí un archivo .xlsx o el CSV normalizado del PMS.")
    configuration=copy.deepcopy(profile.configuration)
    if extension==".xlsx":
        suggestions=suggest_configuration(source)
        old={s["name"]:s for s in configuration.get("sheets",[])}
        configuration["sheets"]=[copy.deepcopy(old.get(s["name"],s)) for s in suggestions]
    configuration.setdefault("legend",DEFAULT_LEGEND)
    return ImportDraft.objects.create(profile=profile,user=user,filename=Path(filename).name[:200],
        fingerprint=hashlib.sha256(content).hexdigest(),source=source,configuration=configuration)

@transaction.atomic
def save_decisions(draft_id,expected_revision,decisions,user):
    draft=ImportDraft.objects.select_for_update().get(pk=draft_id)
    check_version(draft,expected_revision)
    draft.decisions=copy.deepcopy(decisions)
    result=build_preview(draft,decisions.get("rows",{}),decisions.get("notes",{}))
    draft.revision+=1;result["revision"]=draft.revision
    draft.preview=result;draft.save()
    return result
