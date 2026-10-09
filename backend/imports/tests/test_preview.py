from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError
from pms.models import Room,Unit,Reservation
from imports.models import ImportProfile,ImportDraft
from .fixtures import calendar,source_candidate

class PreviewTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("admin",is_staff=True)
        room=Room.objects.create(name="2",kind="SHARED")
        self.unit=Unit.objects.create(room=room,name="a")
        self.profile=ImportProfile.objects.create(name="Prueba",configuration={"mapping":{"2-a":self.unit.pk},"mapping_confirmed":True})
    def draft(self,**extra):
        return ImportDraft.objects.create(profile=self.profile,user=self.user,fingerprint="a"*64,
            source={"format":"csv","sheets":[],"candidates":[source_candidate()]},configuration=self.profile.configuration,**extra)
    def reviewed(self):
        return {"rows":{"AGO-26:2:10":{"selected":True,"reviewed":True,"status":"CHECKED_OUT","new_confirmed":True}},"notes":{}}
    def test_upload_does_not_create_reservations_and_notes_require_decision(self):
        from imports.services import create_draft
        from imports.preview import build_preview
        draft=create_draft(calendar(),"prueba.xlsx",self.profile,self.user)
        result=build_preview(draft,{}, {})
        self.assertFalse(Reservation.objects.exists())
        self.assertEqual(len(result["pending_notes"]),1)
        self.assertEqual(result["pending_notes"][0]["text"],"Nota de cama")
    def test_mapping_review_and_inactive_unit_are_required(self):
        from imports.preview import build_preview
        draft=self.draft()
        result=build_preview(draft,self.reviewed()["rows"],{})
        self.assertEqual(result["rows"][0]["action"],"CREATE")
        self.unit.active=False;self.unit.save()
        result=build_preview(draft,self.reviewed()["rows"],{})
        self.assertEqual(result["rows"][0]["action"],"CONFLICT")
    def test_homonym_does_not_bind_silently(self):
        from imports.preview import build_preview
        Reservation.objects.create(guest="Persona ficticia",start=date(2026,8,10),end=date(2026,8,13))
        decisions=self.reviewed()["rows"];decisions["AGO-26:2:10"]["new_confirmed"]=False
        result=build_preview(self.draft(),decisions,{})
        self.assertEqual(result["rows"][0]["action"],"REVIEW")
        self.assertIsNone(result["rows"][0]["before"])
    def test_stale_decision_save_rejected(self):
        from imports.services import save_decisions
        draft=self.draft()
        save_decisions(draft.pk,draft.revision,self.reviewed(),self.user)
        with self.assertRaises(ValidationError):save_decisions(draft.pk,draft.revision,self.reviewed(),self.user)
