from django.db import transaction,IntegrityError
from django.utils import timezone
from rest_framework.exceptions import ValidationError,PermissionDenied
from pms.models import Reservation,Allocation,Unit
from pms.services import lock_rooms
from .models import ImportDraft,ImportProfile,ImportBinding,ImportBatch
from .services import check_version
from .preview import build_preview,snapshot,identity

def apply_draft(draft_id,expected_revision,user):
    if not user.is_staff:raise PermissionDenied("La migración requiere administración.")
    try:
        with transaction.atomic():
            draft=ImportDraft.objects.select_for_update().get(pk=draft_id)
            if draft.state=="APPLIED":return draft.batch
            check_version(draft,expected_revision)
            if not draft.preview.get("can_apply"):raise ValidationError("Revisá las filas seleccionadas y las notas pendientes antes de aplicar.")
            ImportProfile.objects.select_for_update().get(pk=draft.profile_id)
            previous={r["key"]:r for r in draft.preview["rows"] if r["selected"]}
            reservation_ids=sorted({r["reservation_id"] for r in previous.values() if r["reservation_id"]})
            locked={r.pk:r for r in Reservation.objects.select_for_update().filter(pk__in=reservation_ids).order_by("pk")}
            for row in previous.values():
                if row["reservation_id"]:
                    item=locked.get(row["reservation_id"])
                    if item is None or snapshot(item)!=row["snapshot"]:raise ValidationError("Una reserva o su cuenta cambió después de la revisión. Volvé a generar la vista previa.")
            room_ids=set(Unit.objects.filter(pk__in=[r["candidate"]["unit_id"] for r in previous.values()]).values_list("room_id",flat=True))
            room_ids.update(Allocation.objects.filter(reservation_id__in=reservation_ids).values_list("unit__room_id",flat=True))
            lock_rooms(room_ids)
            fresh=build_preview(draft,draft.decisions.get("rows",{}),draft.decisions.get("notes",{}))
            if not fresh["can_apply"]:raise ValidationError("La disponibilidad o la validación cambió. Revisá nuevamente el borrador.")
            actions=[]
            for row in fresh["rows"]:
                if not row["selected"]:continue
                old=previous.get(row["key"])
                if old is None or row["reservation_id"]!=old["reservation_id"] or row["candidate"]!=old["candidate"]:
                    raise ValidationError("La vinculación cambió desde la revisión. Volvé a revisar.")
                c=row["candidate"];reservation=locked.get(row["reservation_id"])
                if row["action"]=="UNCHANGED":
                    actions.append({"action":"UNCHANGED","reservation_id":reservation.pk,"source_id":c["source_id"]});continue
                unit=Unit.objects.select_related("room").get(pk=c["unit_id"])
                if reservation:
                    changed=str(reservation.start)!=c["start"] or str(reservation.end)!=c["end"] or reservation.allocations.get().unit_id!=unit.pk
                    if changed:reservation.financial_review_required=True;reservation.account_reviewed_at=None;reservation.account_reviewed_by=None
                    reservation.guest=c["guest"];reservation.start=c["start"];reservation.end=c["end"];reservation.status=c["status"]
                    allocation=reservation.allocations.get()
                    allocation.unit=unit;allocation.start=c["start"];allocation.end=c["end"]
                    allocation.active=c["status"] in ("CONFIRMED","IN_HOUSE")
                    if changed:allocation.rate=None
                    allocation.save()
                else:
                    reservation=Reservation.objects.create(guest=c["guest"],start=c["start"],end=c["end"],status=c["status"],financial_review_required=True)
                    Allocation.objects.create(reservation=reservation,unit=unit,start=c["start"],end=c["end"],rate=None,active=c["status"] in ("CONFIRMED","IN_HOUSE"))
                reservation.import_notes=c["notes_text"];reservation.import_colors=c["colors"];reservation.save()
                ImportBinding.objects.update_or_create(profile=draft.profile,reservation=reservation,
                    defaults={"source_id":c["source_id"],"signature":identity(c),"content":c})
                actions.append({"action":row["action"],"reservation_id":reservation.pk,"source_id":c["source_id"]})
            batch=ImportBatch.objects.create(draft=draft,user=user,actions=actions)
            draft.state="APPLIED";draft.revision+=1;draft.save()
            return batch
    except IntegrityError as exc:
        raise ValidationError("Otra operación cambió la disponibilidad o el vínculo. No se aplicó ninguna fila: revisá el borrador.") from exc
