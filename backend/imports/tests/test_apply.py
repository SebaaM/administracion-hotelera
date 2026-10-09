from datetime import date,timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from pms.models import Reservation,Allocation,LedgerEntry
from imports.models import ImportBatch,ImportBinding
from imports.services import save_decisions
from . import test_preview as setup
from .fixtures import source_candidate

class ApplyTests(TestCase):
    def setUp(self):setup.PreviewTests.setUp(self)
    def prepared(self,candidate=None,status="CHECKED_OUT"):
        draft=setup.PreviewTests.draft(self)
        if candidate:draft.source["candidates"]=[candidate];draft.save()
        decisions=setup.PreviewTests.reviewed(self)
        decisions["rows"]["AGO-26:2:10"]["status"]=status
        save_decisions(draft.pk,1,decisions,self.user);draft.refresh_from_db()
        return draft
    def test_application_is_idempotent_and_does_not_invent_finance(self):
        from imports.apply import apply_draft
        draft=self.prepared()
        batch=apply_draft(draft.pk,draft.revision,self.user)
        self.assertEqual(apply_draft(draft.pk,draft.revision,self.user).pk,batch.pk)
        self.assertEqual(Reservation.objects.count(),1)
        self.assertEqual(ImportBatch.objects.count(),1)
        reservation=Reservation.objects.get()
        self.assertTrue(reservation.financial_review_required)
        self.assertEqual(reservation.import_notes,"Llegada tarde\nOrigen: AGO-26!K2")
        self.assertFalse(LedgerEntry.objects.exists())
        self.assertIsNone(reservation.allocations.get().rate)
        second=self.prepared()
        apply_draft(second.pk,second.revision,self.user)
        self.assertEqual(Reservation.objects.count(),1)
    def test_new_payment_invalidates_preview_and_preserves_manual_data(self):
        from imports.apply import apply_draft
        first=self.prepared();apply_draft(first.pk,first.revision,self.user)
        reservation=Reservation.objects.get();reservation.notes="Nota manual";reservation.save()
        draft=self.prepared()
        LedgerEntry.objects.create(reservation=reservation,kind="PAYMENT",description="Cobro real",amount=10,created_by=self.user)
        with self.assertRaises(ValidationError):apply_draft(draft.pk,draft.revision,self.user)
        reservation.refresh_from_db()
        self.assertEqual(reservation.notes,"Nota manual")
        self.assertEqual(LedgerEntry.objects.count(),1)
        self.assertEqual(ImportBatch.objects.count(),1)
    def test_later_conflict_leaves_no_partial_batch(self):
        from imports.apply import apply_draft
        today=timezone.localdate();candidate=source_candidate(start=(today+timedelta(days=1)).isoformat(),end=(today+timedelta(days=4)).isoformat())
        draft=self.prepared(candidate,"CONFIRMED")
        r=Reservation.objects.create(guest="Otra persona",start=date.fromisoformat(candidate["start"]),end=date.fromisoformat(candidate["end"]))
        Allocation.objects.create(reservation=r,unit=self.unit,start=r.start,end=r.end,rate=100)
        with self.assertRaises(ValidationError):apply_draft(draft.pk,draft.revision,self.user)
        self.assertEqual(Reservation.objects.count(),1)
        self.assertFalse(ImportBinding.objects.exists())
        self.assertFalse(ImportBatch.objects.exists())
    def test_unresolved_note_blocks_application(self):
        from imports.apply import apply_draft
        from imports.services import create_draft
        from .fixtures import calendar
        draft=create_draft(calendar(),"prueba.xlsx",self.profile,self.user)
        result=save_decisions(draft.pk,1,setup.PreviewTests.reviewed(self),self.user)
        with self.assertRaises(ValidationError):apply_draft(draft.pk,result["revision"],self.user)
        self.assertFalse(Reservation.objects.exists())
