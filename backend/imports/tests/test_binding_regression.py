from django.test import TestCase
from . import test_preview as setup
from .fixtures import source_candidate
from imports.services import save_decisions
from imports.apply import apply_draft
from imports.preview import candidates_for
from pms.models import Reservation

class BindingRegressionTests(TestCase):
    def setUp(self):setup.PreviewTests.setUp(self)
    def prepared(self,name=None):
        draft=setup.PreviewTests.draft(self)
        decisions=setup.PreviewTests.reviewed(self)
        if name:decisions["rows"]["AGO-26:2:10"]["guest"]=name
        save_decisions(draft.pk,1,decisions,self.user);draft.refresh_from_db();return draft
    def test_original_file_does_not_duplicate_corrected_guest(self):
        first=self.prepared("Nombre corregido");apply_draft(first.pk,first.revision,self.user)
        second=self.prepared();apply_draft(second.pk,second.revision,self.user)
        self.assertEqual(Reservation.objects.count(),1)
    def test_continuity_join_retains_all_notes_and_final_checkout(self):
        draft=setup.PreviewTests.draft(self)
        draft.source["candidates"]=[source_candidate(key="A",start="2026-08-31",end="2026-09-01"),
            source_candidate(key="B",start="2026-09-01",end="2026-09-03",notes=[{"text":"Segunda nota","refs":[{"sheet":"SEP-26","cell":"B2"}]}])]
        draft.decisions={"joins":[["A","B"]]}
        rows=candidates_for(draft)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["end"],"2026-09-03")
        self.assertEqual({n["text"] for n in rows[0]["notes"]},{"Llegada tarde","Segunda nota"})
    def test_unchanged_manual_link_is_persisted_for_future_loads(self):
        from datetime import date
        from pms.models import Allocation
        from imports.models import ImportBinding
        existing=Reservation.objects.create(guest="Persona ficticia",start=date(2026,8,10),end=date(2026,8,13),status="CHECKED_OUT")
        Allocation.objects.create(reservation=existing,unit=self.unit,start=existing.start,end=existing.end,rate=100,active=False)
        draft=setup.PreviewTests.draft(self)
        draft.source["candidates"]=[source_candidate(notes=[],colors=[])];draft.save()
        decisions=setup.PreviewTests.reviewed(self);decisions["rows"]["AGO-26:2:10"]["reservation_id"]=existing.pk
        preview=save_decisions(draft.pk,1,decisions,self.user)
        self.assertEqual(preview["rows"][0]["action"],"UNCHANGED")
        draft.refresh_from_db();apply_draft(draft.pk,draft.revision,self.user)
        self.assertTrue(ImportBinding.objects.filter(profile=self.profile,reservation=existing).exists())
