from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from pms.models import Room, Unit, Reservation, Allocation
from pms.views import reservation_data

class MigrationStorageTests(TestCase):
    def test_unknown_rate_is_not_free_stay(self):
        reservation = Reservation.objects.create(guest="Persona ficticia", start=date(2026,8,10), end=date(2026,8,13), financial_review_required=True)
        room = Room.objects.create(name="2",kind="SHARED")
        unit = Unit.objects.create(room=room,name="a")
        Allocation.objects.create(reservation=reservation, unit=unit, start=reservation.start, end=reservation.end, rate=None)
        dto = reservation_data(reservation)
        self.assertTrue(dto["financial_review_required"])
        self.assertIsNone(dto["units"][0]["rate"])
        self.assertEqual(dto["ledger"], [])
        self.assertEqual(dto["import_notes"], "")
    def test_binding_and_batch_are_unique(self):
        from imports.models import ImportProfile, ImportDraft, ImportBinding, ImportBatch
        user = User.objects.create_user("prueba")
        profile = ImportProfile.objects.create(name="Calendario")
        draft = ImportDraft.objects.create(profile=profile,user=user,fingerprint="a"*64,source={})
        reservation = Reservation.objects.create(guest="Persona",start=date(2026,8,10),end=date(2026,8,13))
        binding = ImportBinding.objects.create(profile=profile,reservation=reservation)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ImportBinding.objects.create(profile=profile,reservation=reservation)
        ImportBatch.objects.create(draft=draft,user=user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ImportBatch.objects.create(draft=draft,user=user)
        self.assertTrue(binding.source_id)
