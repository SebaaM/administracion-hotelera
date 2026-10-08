from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction, close_old_connections, connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from .models import (
    Hotel,
    Room,
    Unit,
    Reservation,
    Allocation,
    CleaningTask,
    Maintenance,
)
from .services import create_reservation, transition, add_entry, totals


class PMSFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "admin", password="Prueba-Segura-2026!", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        Hotel.objects.create(pk=1)
        self.room = Room.objects.create(name="101", kind="PRIVATE", capacity=2)
        self.unit = Unit.objects.create(
            room=self.room, name="Habitación completa", rate=Decimal("100.00")
        )
        self.today = timezone.localdate()

    def book(self, **extra):
        data = {
            "guest": "Huésped de prueba",
            "guests": 1,
            "start": self.today,
            "end": self.today + timedelta(days=2),
            "unit_ids": [self.unit.pk],
        }
        return create_reservation({**data, **extra}, self.user)

    def test_private_room_cannot_be_sold_twice(self):
        self.book()
        with self.assertRaises(ValidationError):
            self.book(guest="Otra persona")

    def test_checkout_date_can_be_next_arrival(self):
        self.book()
        next_stay = self.book(
            start=self.today + timedelta(days=2), end=self.today + timedelta(days=3)
        )
        self.assertEqual(next_stay.status, "CONFIRMED")

    def test_beds_have_independent_inventory(self):
        self.room.kind = "SHARED"
        self.room.save()
        second = Unit.objects.create(room=self.room, name="Cama 02", rate=50)
        self.book()
        self.book(unit_ids=[second.pk])
        self.assertEqual(Reservation.objects.count(), 2)

    def test_database_constraint_rejects_overlapping_raw_insert(self):
        self.book()
        other = Reservation.objects.create(
            guest="Duplicado", start=self.today, end=self.today + timedelta(days=1)
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Allocation.objects.create(
                reservation=other,
                unit=self.unit,
                start=self.today,
                end=self.today + timedelta(days=1),
                rate=100,
            )

    def test_capacity_validation_is_atomic(self):
        with self.assertRaises(ValidationError):
            self.book(guests=3)
        self.assertFalse(Reservation.objects.exists())

    def test_guest_account_and_payment_limits(self):
        stay = self.book()
        self.assertEqual(Decimal(totals(stay)["balance"]), Decimal("200.00"))
        add_entry(
            stay.pk,
            {
                "kind": "PAYMENT",
                "amount": "50.00",
                "description": "Anticipo",
                "method": "CASH",
            },
            self.user,
        )
        add_entry(
            stay.pk,
            {
                "kind": "CHARGE",
                "amount": "25.00",
                "description": "Desayuno",
                "method": "",
            },
            self.user,
        )
        self.assertEqual(Decimal(totals(stay)["balance"]), Decimal("175.00"))
        with self.assertRaises(ValidationError):
            add_entry(
                stay.pk,
                {
                    "kind": "PAYMENT",
                    "amount": "176",
                    "description": "Exceso",
                    "method": "CASH",
                },
                self.user,
            )

    def test_checkout_creates_cleaning_and_repeated_checkout_is_rejected(self):
        stay = self.book()
        transition(stay.pk, "checkin")
        transition(stay.pk, "checkout")
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.cleaning, "DIRTY")
        self.assertEqual(
            CleaningTask.objects.filter(unit=self.unit, status="PENDING").count(), 1
        )
        with self.assertRaises(ValidationError):
            transition(stay.pk, "checkout")

    def test_checkin_requires_clean_unit(self):
        stay = self.book()
        self.unit.cleaning = "DIRTY"
        self.unit.save()
        with self.assertRaises(ValidationError):
            transition(stay.pk, "checkin")

    def test_cleaning_transitions_restore_readiness(self):
        stay = self.book()
        transition(stay.pk, "checkin")
        transition(stay.pk, "checkout")
        task = CleaningTask.objects.get(unit=self.unit)
        self.assertEqual(
            self.client.post(
                f"/api/cleaning/{task.pk}/", {"status": "DONE"}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                f"/api/cleaning/{task.pk}/", {"status": "IN_PROGRESS"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                f"/api/cleaning/{task.pk}/", {"status": "DONE"}, format="json"
            ).status_code,
            200,
        )
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.cleaning, "CLEAN")

    def test_maintenance_blocks_room_and_resolution_releases_it(self):
        item = Maintenance.objects.create(
            room=self.room,
            title="Reparar",
            start=self.today,
            end=self.today + timedelta(days=2),
        )
        with self.assertRaises(ValidationError):
            self.book()
        self.client.post(
            f"/api/maintenance/{item.pk}/", {"status": "IN_PROGRESS"}, format="json"
        )
        self.client.post(
            f"/api/maintenance/{item.pk}/", {"status": "DONE"}, format="json"
        )
        self.assertEqual(self.book().status, "CONFIRMED")

    def test_maintenance_cannot_block_existing_booking(self):
        self.book()
        response = self.client.post(
            "/api/maintenance/",
            {
                "room": self.room.pk,
                "title": "Trabajo",
                "start": str(self.today),
                "end": str(self.today + timedelta(days=1)),
                "blocking": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Maintenance.objects.exists())

    def test_cancel_releases_inventory(self):
        stay = self.book()
        transition(stay.pk, "cancel")
        self.assertEqual(self.book().status, "CONFIRMED")

    def test_paid_booking_cannot_be_cancelled_without_refund(self):
        stay = self.book()
        add_entry(
            stay.pk,
            {
                "kind": "PAYMENT",
                "amount": "1.00",
                "description": "Anticipo",
                "method": "CASH",
            },
            self.user,
        )
        with self.assertRaises(ValidationError):
            transition(stay.pk, "cancel")

    def test_settings_are_admin_only_and_colors_validated(self):
        response = self.client.patch(
            "/api/settings/",
            {
                "name": "Hotel Azul",
                "primary_color": "#112233",
                "sections": {"cleaning": False},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.client.patch(
                "/api/settings/", {"primary_color": "rojo"}, format="json"
            ).status_code,
            400,
        )
        receptionist = User.objects.create_user(
            "recepcionista", password="Prueba-Segura-2026!"
        )
        self.client.force_authenticate(receptionist)
        self.assertEqual(
            self.client.patch(
                "/api/settings/", {"name": "Otro"}, format="json"
            ).status_code,
            403,
        )

    def test_multipart_settings_and_removing_logo(self):
        response = self.client.patch(
            "/api/settings/",
            {"name": "Hotel Verde", "sections": '{"cleaning":false}', "logo": ""},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Hotel.objects.get(pk=1).sections, {"cleaning": False})

    def test_shared_room_generates_beds_and_can_add_another(self):
        response = self.client.post(
            "/api/rooms/",
            {"name": "Dormitorio", "kind": "SHARED", "beds": 3, "rate": "20.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        room = Room.objects.get(pk=response.data["id"])
        self.assertEqual(room.units.count(), 3)
        response = self.client.post(
            f"/api/rooms/{room.pk}/units/",
            {"name": "Cama 04", "rate": "20.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        room.refresh_from_db()
        self.assertEqual(room.capacity, 4)

    def test_snapshot_and_api_require_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/state/").status_code, 403)
        self.assertEqual(self.client.get("/api/session/").status_code, 200)

    def test_csrf_is_required_for_login(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                "/api/login/",
                {"username": "admin", "password": "Prueba-Segura-2026!"},
                format="json",
            ).status_code,
            403,
        )
        client.get("/api/session/")
        token = client.cookies["csrftoken"].value
        response = client.post(
            "/api/login/",
            {"username": "admin", "password": "Prueba-Segura-2026!"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200, response.data)


class ConcurrentBookingTests(TransactionTestCase):
    def test_two_receptionists_cannot_reserve_the_same_unit(self):
        user = User.objects.create_user("concurrencia")
        room = Room.objects.create(name="Concurrencia", kind="PRIVATE", capacity=2)
        unit = Unit.objects.create(room=room, name="Completa", rate=100)
        barrier = Barrier(2)
        today = timezone.localdate()

        def attempt(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                create_reservation(
                    {
                        "guest": f"Huésped {index}",
                        "guests": 1,
                        "start": today,
                        "end": today + timedelta(days=2),
                        "unit_ids": [unit.pk],
                    },
                    User.objects.get(pk=user.pk),
                )
                return "created"
            except ValidationError:
                return "rejected"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, [1, 2]))
        self.assertCountEqual(results, ["created", "rejected"])
        self.assertEqual(Reservation.objects.count(), 1)
