import copy
from collections import Counter
from django.db import transaction,IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from pms.views import admin_required
from .models import ImportProfile,ImportDraft
from .serializers import ProfileInput,UploadInput,DraftInput,RevisionInput,validate_decisions
from .services import create_draft,save_decisions,check_version
from .preview import candidates_for
from .apply import apply_draft
from .csv_io import write_csv

def profile_data(profile):
    return {"id":profile.pk,"name":profile.name,"configuration":profile.configuration}

def draft_data(draft,full=True):
    result={"id":draft.pk,"profile_id":draft.profile_id,"filename":draft.filename,"revision":draft.revision,
        "state":draft.state,"created_at":draft.created_at,"configuration":draft.configuration,"decisions":draft.decisions}
    if full:
        result["preview"]=draft.preview
        result["source_summary"]={"format":draft.source.get("format"),"sheets":[{"name":s["name"],
            "notes":sum(bool(c.get("note")) for c in s["cells"]),"colors":dict(Counter(c["color"] for c in s["cells"] if c.get("color"))),
            "warnings":s.get("warnings",[])} for s in draft.source.get("sheets",[])]}
        if draft.state=="APPLIED":result["batch"]={"id":draft.batch.pk,"actions":draft.batch.actions,"created_at":draft.batch.created_at}
    return result

@api_view(["GET","POST"])
def profiles(request):
    admin_required(request.user)
    if request.method=="GET":return Response([profile_data(p) for p in ImportProfile.objects.order_by("name")])
    serializer=ProfileInput(data=request.data);serializer.is_valid(raise_exception=True)
    try:profile=ImportProfile.objects.create(**serializer.validated_data)
    except IntegrityError:raise ValidationError("Ya existe un perfil con ese nombre.")
    return Response(profile_data(profile),status=201)

@api_view(["PATCH"])
def profile(request,pk):
    admin_required(request.user)
    item=get_object_or_404(ImportProfile,pk=pk)
    serializer=ProfileInput(data=request.data,partial=True);serializer.is_valid(raise_exception=True)
    for key,value in serializer.validated_data.items():setattr(item,key,value)
    try:item.save()
    except IntegrityError:raise ValidationError("Ya existe un perfil con ese nombre.")
    return Response(profile_data(item))

@api_view(["GET","POST"])
def drafts(request):
    admin_required(request.user)
    if request.method=="GET":return Response([draft_data(d,False) for d in ImportDraft.objects.order_by("-pk")[:100]])
    serializer=UploadInput(data=request.data);serializer.is_valid(raise_exception=True)
    upload=serializer.validated_data["file"]
    if upload.size>5*1024*1024:raise ValidationError("El archivo no puede superar 5 MB.")
    profile=get_object_or_404(ImportProfile,pk=serializer.validated_data["profile_id"])
    draft=create_draft(upload.read(),upload.name,profile,request.user)
    return Response(draft_data(draft),status=201)

@api_view(["GET","PATCH"])
def draft(request,pk):
    admin_required(request.user)
    if request.method=="GET":return Response(draft_data(get_object_or_404(ImportDraft,pk=pk)))
    serializer=DraftInput(data=request.data);serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        item=get_object_or_404(ImportDraft.objects.select_for_update(),pk=pk)
        check_version(item,serializer.validated_data["expected_revision"])
        if "configuration" in serializer.validated_data:
            item.configuration=serializer.validated_data["configuration"];item.save(update_fields=["configuration"])
        decisions=serializer.validated_data.get("decisions",item.decisions)
        validate_decisions(decisions,item)
        save_decisions(item.pk,item.revision,decisions,request.user)
        item.refresh_from_db()
    return Response(draft_data(item))

@api_view(["POST"])
def preview(request,pk):
    admin_required(request.user)
    serializer=RevisionInput(data=request.data);serializer.is_valid(raise_exception=True)
    item=get_object_or_404(ImportDraft,pk=pk)
    save_decisions(item.pk,serializer.validated_data["expected_revision"],item.decisions,request.user)
    item.refresh_from_db()
    return Response(draft_data(item))

@api_view(["POST"])
def apply(request,pk):
    admin_required(request.user)
    serializer=RevisionInput(data=request.data);serializer.is_valid(raise_exception=True)
    get_object_or_404(ImportDraft,pk=pk)
    apply_draft(pk,serializer.validated_data["expected_revision"],request.user)
    return Response(draft_data(ImportDraft.objects.get(pk=pk)))

@api_view(["POST"])
def discard(request,pk):
    admin_required(request.user)
    serializer=RevisionInput(data=request.data);serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        item=get_object_or_404(ImportDraft.objects.select_for_update(),pk=pk)
        check_version(item,serializer.validated_data["expected_revision"])
        item.source={};item.preview={};item.decisions={};item.configuration={};item.filename="";item.state="DISCARDED";item.revision+=1;item.save()
    return Response(draft_data(item))

@api_view(["GET"])
def export_csv(request,pk):
    admin_required(request.user)
    item=get_object_or_404(ImportDraft,pk=pk)
    if not item.preview.get("can_apply") and item.state!="APPLIED":raise ValidationError("Revisá el borrador antes de exportar.")
    rows=[r["candidate"] for r in item.preview.get("rows",[]) if r["selected"]]
    response=HttpResponse(write_csv(rows),content_type="text/csv; charset=utf-8")
    response["Content-Disposition"]=f'attachment; filename="reservas-lote-{pk}.csv"'
    response["Cache-Control"]="no-store"
    return response
