import json
from datetime import date
from django.contrib.auth import authenticate, login, logout
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.authentication import SessionAuthentication
from .models import (
    Hotel,
    Room,
    Unit,
    Reservation,
    Allocation,
    CleaningTask,
    Maintenance,
)
from .serializers import (
    HotelSerializer,
    ReservationInput,
    GuestInput,
    EntryInput,
    RoomInput,
    UnitInput,
    MaintenanceInput,
    validated_image,
)
from .services import create_reservation, transition, add_entry, totals, lock_rooms


def admin_required(user):
    if not user.is_staff:
        raise PermissionDenied(
            "Esta configuración requiere una cuenta de administración."
        )


def hotel():
    return Hotel.objects.get_or_create(pk=1)[0]


def reservation_data(r):
    return {
        "id": r.pk,
        "code": f"R-{r.pk:05d}",
        "guest": r.guest,
        "contact": r.contact,
        "document": r.document,
        "guests": r.guests,
        "start": r.start,
        "end": r.end,
        "notes": r.notes,
        "status": r.status,
        "updated_at": r.updated_at,
        "checkout_date": timezone.localtime(r.checked_out_at).date()
        if r.checked_out_at
        else None,
        "units": [
            {
                "id": a.unit_id,
                "name": a.unit.name,
                "room_id": a.unit.room_id,
                "room": a.unit.room.name,
                "kind": a.unit.room.kind,
                "rate": str(a.rate),
            }
            for a in r.allocations.select_related("unit__room")
        ],
        "ledger": [
            {
                "id": e.pk,
                "kind": e.kind,
                "description": e.description,
                "amount": str(e.amount),
                "method": e.method,
                "created_at": e.created_at,
                "user": e.created_by.username,
            }
            for e in r.ledger.select_related("created_by")
        ],
        **totals(r),
    }


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def session(request):
    h = hotel()
    return Response(
        {
            "user": {"name": request.user.username, "admin": request.user.is_staff}
            if request.user.is_authenticated
            else None,
            "hotel": HotelSerializer(h).data,
            "today": timezone.localdate(),
        }
    )


@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def signin(request):
    # DRF does not enforce session CSRF for anonymous requests. Login must do it.
    SessionAuthentication().enforce_csrf(request._request)
    user = authenticate(
        request,
        username=request.data.get("username", ""),
        password=request.data.get("password", ""),
    )
    if user is None:
        return Response({"detail": "Usuario o contraseña incorrectos."}, status=400)
    login(request, user)
    return Response({"name": user.username, "admin": user.is_staff})


@api_view(["POST"])
def signout(request):
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
def state(request):
    return Response(
        {
            "hotel": HotelSerializer(hotel()).data,
            "today": timezone.localdate(),
            "rooms": [
                {
                    "id": r.pk,
                    "name": r.name,
                    "kind": r.kind,
                    "capacity": r.capacity,
                    "active": r.active,
                    "image": r.image.url if r.image else None,
                }
                for r in Room.objects.all()
            ],
            "units": [
                {
                    "id": u.pk,
                    "room_id": u.room_id,
                    "name": u.name,
                    "rate": str(u.rate),
                    "cleaning": u.cleaning,
                    "active": u.active,
                }
                for u in Unit.objects.all()
            ],
            "reservations": [reservation_data(r) for r in Reservation.objects.all()],
            "cleaning": [
                {
                    "id": t.pk,
                    "unit_id": t.unit_id,
                    "status": t.status,
                    "note": t.note,
                    "updated_at": t.updated_at,
                }
                for t in CleaningTask.objects.all()
            ],
            "maintenance": [
                {
                    "id": m.pk,
                    "room_id": m.room_id,
                    "unit_id": m.unit_id,
                    "title": m.title,
                    "notes": m.notes,
                    "start": m.start,
                    "end": m.end,
                    "blocking": m.blocking,
                    "status": m.status,
                }
                for m in Maintenance.objects.all()
            ],
            "server_time": timezone.now(),
        }
    )


@api_view(["PATCH"])
def configure(request):
    admin_required(request.user)
    data = dict(request.data.items())
    if isinstance(data.get("sections"), str):
        try:
            data["sections"] = json.loads(data["sections"])
        except (ValueError, TypeError):
            raise ValidationError("Configuración de secciones inválida.")
    for key in ["logo", "cover"]:
        if key in request.FILES:
            data[key] = validated_image(request.FILES[key])
        elif data.get(key) == "":
            data[key] = None
    with transaction.atomic():
        item = Hotel.objects.select_for_update().get(pk=hotel().pk)
        serializer = HotelSerializer(item, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
def reservations(request):
    serializer = ReservationInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        result = create_reservation(dict(serializer.validated_data), request.user)
    except IntegrityError:
        raise ValidationError(
            "La disponibilidad cambió. Actualizá y elegí otra unidad."
        )
    return Response(reservation_data(result), status=201)


@api_view(["PATCH"])
def reservation(request, pk):
    with transaction.atomic():
        item = get_object_or_404(Reservation.objects.select_for_update(), pk=pk)
        expected = request.data.get("expected_updated_at")
        if expected and expected != item.updated_at.isoformat().replace("+00:00", "Z"):
            raise ValidationError(
                "Otra persona modificó esta reserva. Cerrá el detalle y volvé a abrirlo antes de guardar."
            )
        serializer = GuestInput(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(reservation_data(item))


@api_view(["POST"])
def reservation_action(request, pk, action):
    get_object_or_404(Reservation, pk=pk)
    return Response(reservation_data(transition(pk, action)))


@api_view(["POST"])
def ledger(request, pk):
    get_object_or_404(Reservation, pk=pk)
    serializer = EntryInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    add_entry(pk, serializer.validated_data, request.user)
    return Response(reservation_data(Reservation.objects.get(pk=pk)), status=201)


@api_view(["POST"])
def rooms(request):
    admin_required(request.user)
    data = request.data.copy()
    if "image" in request.FILES:
        data["image"] = validated_image(request.FILES["image"])
    serializer = RoomInput(data=data)
    serializer.is_valid(raise_exception=True)
    values = dict(serializer.validated_data)
    beds = values.pop("beds", 1)
    rate = values.pop("rate", 0)
    if values["kind"] == "SHARED":
        values["capacity"] = beds
    try:
        with transaction.atomic():
            item = Room.objects.create(**values)
            for i in range(beds if item.kind == "SHARED" else 1):
                Unit.objects.create(
                    room=item,
                    name=f"Cama {i + 1:02d}"
                    if item.kind == "SHARED"
                    else "Habitación completa",
                    rate=rate,
                )
    except IntegrityError:
        raise ValidationError("Ya existe una habitación con ese nombre.")
    return Response({"id": item.pk}, status=201)


@api_view(["PATCH"])
def room(request, pk):
    admin_required(request.user)
    with transaction.atomic():
        item = get_object_or_404(Room.objects.select_for_update(), pk=pk)
        data = request.data.copy()
        if "image" in request.FILES:
            data["image"] = validated_image(request.FILES["image"])
        if data.get("kind", item.kind) != item.kind or "beds" in data:
            raise ValidationError(
                "El tipo y la cantidad de camas se definen al crear la habitación."
            )
        if Allocation.objects.filter(unit__room=item, active=True).exists() and (
            "capacity" in data or data.get("active") in [False, "false", "False"]
        ):
            raise ValidationError(
                "No se puede cambiar la capacidad o desactivar una habitación con reservas activas."
            )
        serializer = RoomInput(item, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response({"ok": True})


@api_view(["PATCH"])
def unit(request, pk):
    admin_required(request.user)
    item = get_object_or_404(Unit, pk=pk)
    with transaction.atomic():
        lock_rooms([item.room_id])
        item = Unit.objects.get(pk=pk)
        serializer = UnitInput(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if (
            serializer.validated_data.get("active") is False
            and item.allocations.filter(active=True).exists()
        ):
            raise ValidationError("La unidad tiene reservas activas.")
        if (
            item.room.units.filter(
                name=serializer.validated_data.get("name", item.name)
            )
            .exclude(pk=item.pk)
            .exists()
        ):
            raise ValidationError(
                "Ya existe una unidad con ese nombre en la habitación."
            )
        serializer.save()
        if item.room.kind == "SHARED":
            room = item.room
            room.capacity = max(1, room.units.filter(active=True).count())
            room.save()
    return Response({"ok": True})


@api_view(["POST"])
def add_unit(request, pk):
    admin_required(request.user)
    with transaction.atomic():
        item = get_object_or_404(Room.objects.select_for_update(), pk=pk)
        if item.kind != "SHARED":
            raise ValidationError(
                "Solo se pueden agregar camas a habitaciones compartidas."
            )
        if item.units.count() >= 40:
            raise ValidationError("La habitación ya alcanzó el máximo de 40 camas.")
        serializer = UnitInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if item.units.filter(name=serializer.validated_data["name"]).exists():
            raise ValidationError("Ya existe una cama con ese nombre.")
        result = serializer.save(room=item)
        item.capacity = item.units.filter(active=True).count()
        item.save()
    return Response({"id": result.pk}, status=201)


@api_view(["POST"])
def cleaning(request):
    item = get_object_or_404(Unit, pk=request.data.get("unit_id"))
    with transaction.atomic():
        lock_rooms([item.room_id])
        if item.cleaning_tasks.exclude(status="DONE").exists():
            raise ValidationError("Esta unidad ya tiene una tarea pendiente.")
        if item.allocations.filter(reservation__status="IN_HOUSE").exists():
            raise ValidationError(
                "La unidad está ocupada. Registrá la limpieza de salida después del check-out."
            )
        task = CleaningTask.objects.create(
            unit=item, note=str(request.data.get("note", ""))[:200]
        )
        Unit.objects.filter(pk=item.pk).update(cleaning="DIRTY")
    return Response({"id": task.pk}, status=201)


@api_view(["POST"])
def cleaning_action(request, pk):
    task = get_object_or_404(CleaningTask, pk=pk)
    with transaction.atomic():
        lock_rooms([task.unit.room_id])
        task = CleaningTask.objects.select_for_update().get(pk=pk)
        status = request.data.get("status")
        if (task.status, status) not in [
            ("PENDING", "IN_PROGRESS"),
            ("IN_PROGRESS", "DONE"),
        ]:
            raise ValidationError("La tarea cambió o la transición no es válida.")
        task.status = status
        task.save()
        Unit.objects.filter(pk=task.unit_id).update(
            cleaning="CLEANING" if status == "IN_PROGRESS" else "CLEAN"
        )
    return Response({"ok": True})


@api_view(["POST"])
def maintenance(request):
    serializer = MaintenanceInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        lock_rooms([data["room"].pk])
        if data.get("blocking", True):
            bookings = Allocation.objects.filter(
                unit__room=data["room"],
                active=True,
                start__lt=data["end"],
                end__gt=data["start"],
            )
            occupied = Allocation.objects.filter(
                unit__room=data["room"], reservation__status="IN_HOUSE"
            )
            if data.get("unit"):
                bookings = bookings.filter(unit=data["unit"])
                occupied = occupied.filter(unit=data["unit"])
            if bookings.exists() or (
                data["start"] <= timezone.localdate() < data["end"]
                and occupied.exists()
            ):
                raise ValidationError(
                    "Hay reservas o huéspedes en ese período. Registrá la incidencia sin bloqueo o reubicá las reservas."
                )
        result = serializer.save()
    return Response({"id": result.pk}, status=201)


@api_view(["POST"])
def maintenance_action(request, pk):
    item = get_object_or_404(Maintenance, pk=pk)
    with transaction.atomic():
        lock_rooms([item.room_id])
        item = Maintenance.objects.select_for_update().get(pk=pk)
        status = request.data.get("status")
        if (item.status, status) not in [
            ("OPEN", "IN_PROGRESS"),
            ("IN_PROGRESS", "DONE"),
        ]:
            raise ValidationError("La incidencia cambió o la transición no es válida.")
        item.status = status
        item.save()
    return Response({"ok": True})
