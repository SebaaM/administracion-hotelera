from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from pms.models import Reservation,LedgerEntry
from pms.views import reservation_data

class AccountReviewTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("recepcion")
        self.client=APIClient();self.client.force_authenticate(self.user)
        self.reservation=Reservation.objects.create(guest="Persona ficticia",start=date(2026,8,10),end=date(2026,8,13),financial_review_required=True)
    def payload(self):
        dto=reservation_data(self.reservation)
        return {"expected_updated_at":self.reservation.updated_at.isoformat().replace("+00:00","Z"),"ledger_signature":dto.get("ledger_signature",""),"confirmed_zero":False}
    def test_empty_account_requires_explicit_zero(self):
        endpoint=f"/api/reservations/{self.reservation.pk}/account-review/"
        self.assertEqual(self.client.post(endpoint,self.payload(),format="json").status_code,400)
        payload=self.payload();payload["confirmed_zero"]=True
        response=self.client.post(endpoint,payload,format="json")
        self.assertEqual(response.status_code,200)
        self.reservation.refresh_from_db()
        self.assertFalse(self.reservation.financial_review_required)
        self.assertEqual(self.reservation.account_reviewed_by,self.user)
        self.assertFalse(LedgerEntry.objects.exists())
    def test_new_entry_invalidates_account_snapshot(self):
        payload=self.payload();payload["confirmed_zero"]=True
        LedgerEntry.objects.create(reservation=self.reservation,created_by=self.user,kind="CHARGE",amount=100,description="Alojamiento")
        response=self.client.post(f"/api/reservations/{self.reservation.pk}/account-review/",payload,format="json")
        self.assertEqual(response.status_code,400)
        self.reservation.refresh_from_db()
        self.assertTrue(self.reservation.financial_review_required)
    def test_review_current_ledger_preserves_movements(self):
        LedgerEntry.objects.create(reservation=self.reservation,created_by=self.user,kind="CHARGE",amount=100,description="Alojamiento")
        response=self.client.post(f"/api/reservations/{self.reservation.pk}/account-review/",self.payload(),format="json")
        self.assertEqual(response.status_code,200)
        self.reservation.refresh_from_db()
        self.assertFalse(self.reservation.financial_review_required)
        self.assertEqual(LedgerEntry.objects.count(),1)
