from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import (
    Room,
    Unit,
    Reservation,
    Allocation,
    LedgerEntry,
    CleaningTask,
    Maintenance,
)


def money(value):
    try:
        amount = Decimal(str(value))
        if (
            not amount.is_finite()
            or amount < 0
            or amount > Decimal("9999999999.99")
            or amount.as_tuple().exponent < -2
        ):
            raise ValueError()
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Ingresá un importe válido, con hasta dos decimales.")


def totals(reservation):
    sums = {
        x["kind"]: x["total"]
        for x in reservation.ledger.values("kind").annotate(total=Sum("amount"))
    }
    charge, paid = sums.get("CHARGE", Decimal(0)), sums.get("PAYMENT", Decimal(0))
    return {"total": str(charge), "paid": str(paid), "balance": str(charge - paid)}


def lock_rooms(room_ids):
    list(Room.objects.select_for_update().filter(pk__in=room_ids).order_by("pk"))


def assert_available(units, start, end):
    for unit in units:
        if not unit.active or not unit.room.active:
            raise ValidationError(f"{unit.room.name} · {unit.name} está desactivada.")
        if Allocation.objects.filter(
            unit=unit, active=True, start__lt=end, end__gt=start
        ).exists():
            raise ValidationError(
                f"{unit.room.name} · {unit.name} ya tiene una reserva en esas fechas."
            )
        if (
            start <= timezone.localdate() < end
            and Allocation.objects.filter(
                unit=unit, reservation__status="IN_HOUSE"
            ).exists()
        ):
            raise ValidationError(
                f"{unit.room.name} · {unit.name} todavía tiene un huésped alojado."
            )
        if (
            Maintenance.objects.filter(
                room_id=unit.room_id, blocking=True, start__lt=end, end__gt=start
            )
            .exclude(status="DONE")
            .filter(Q(unit__isnull=True) | Q(unit=unit))
            .exists()
        ):
            raise ValidationError(
                f"{unit.room.name} · {unit.name} está bloqueada por mantenimiento."
            )


@transaction.atomic
def create_reservation(data, user):
    data.setdefault("guests", 1)
    unit_ids = data.pop("unit_ids")
    rates = data.pop("rates", {})
    if len(unit_ids) != len(set(unit_ids)) or not unit_ids:
        raise ValidationError("Seleccioná unidades diferentes.")
    units = list(
        Unit.objects.select_related("room").filter(pk__in=unit_ids).order_by("pk")
    )
    if len(units) != len(unit_ids):
        raise ValidationError("Una de las unidades no existe.")
    lock_rooms({u.room_id for u in units})
    # Reload after the room locks, so inventory changes cannot race the booking.
    units = list(
        Unit.objects.select_related("room").filter(pk__in=unit_ids).order_by("pk")
    )
    assert_available(units, data["start"], data["end"])
    capacity = sum(u.room.capacity if u.room.kind == "PRIVATE" else 1 for u in units)
    if data["guests"] > capacity:
        raise ValidationError(
            "La cantidad de huéspedes supera la capacidad seleccionada."
        )
    reservation = Reservation.objects.create(**data)
    amount = Decimal(0)
    nights = (reservation.end - reservation.start).days
    for unit in units:
        rate = money(rates.get(str(unit.pk), unit.rate))
        Allocation.objects.create(
            reservation=reservation,
            unit=unit,
            start=reservation.start,
            end=reservation.end,
            rate=rate,
        )
        amount += rate * nights
    if amount > Decimal("9999999999.99"):
        raise ValidationError("El total supera el importe máximo permitido.")
    if amount:
        LedgerEntry.objects.create(
            reservation=reservation,
            kind="CHARGE",
            description=f"Alojamiento · {nights} noche(s)",
            amount=amount,
            created_by=user,
        )
    return reservation


@transaction.atomic
def transition(pk, action):
    reservation = Reservation.objects.select_for_update().get(pk=pk)
    allocations = list(reservation.allocations.select_related("unit__room"))
    lock_rooms({a.unit.room_id for a in allocations})
    today = timezone.localdate()
    if action == "checkin":
        if reservation.status != "CONFIRMED":
            raise ValidationError("Solo se puede ingresar una reserva confirmada.")
        if not reservation.start <= today < reservation.end:
            raise ValidationError(
                "El check-in debe realizarse dentro de las fechas de la estadía."
            )
        for allocation in allocations:
            unit = Unit.objects.get(pk=allocation.unit_id)
            if unit.cleaning != "CLEAN":
                raise ValidationError(f"{unit.name} todavía no está limpia.")
            if (
                Allocation.objects.filter(unit=unit, reservation__status="IN_HOUSE")
                .exclude(reservation=reservation)
                .exists()
            ):
                raise ValidationError(f"{unit.name} todavía tiene un huésped alojado.")
        reservation.status = "IN_HOUSE"
        reservation.checked_in_at = timezone.now()
    elif action == "checkout":
        if reservation.status != "IN_HOUSE":
            raise ValidationError("Solo se puede finalizar una estadía alojada.")
        reservation.status = "CHECKED_OUT"
        reservation.checked_out_at = timezone.now()
        reservation.allocations.update(active=False)
        for a in allocations:
            Unit.objects.filter(pk=a.unit_id).update(cleaning="DIRTY")
            CleaningTask.objects.get_or_create(
                unit_id=a.unit_id,
                status="PENDING",
                defaults={"note": f"Salida de {reservation.guest}"},
            )
    elif action == "cancel":
        if reservation.status != "CONFIRMED":
            raise ValidationError("Solo se puede cancelar una reserva confirmada.")
        if reservation.ledger.filter(kind="PAYMENT").exists():
            raise ValidationError(
                "Esta reserva tiene cobros: resolvé la devolución antes de cancelarla. Las devoluciones quedan fuera de esta versión."
            )
        reservation.status = "CANCELLED"
        reservation.allocations.update(active=False)
    else:
        raise ValidationError("Acción desconocida.")
    reservation.save()
    return reservation


@transaction.atomic
def add_entry(pk, data, user):
    reservation = Reservation.objects.select_for_update().get(pk=pk)
    if reservation.status == "CANCELLED":
        raise ValidationError("La reserva está cancelada.")
    amount = money(data["amount"])
    if amount <= 0:
        raise ValidationError("El importe debe ser mayor a cero.")
    if data["kind"] == "PAYMENT" and amount > Decimal(totals(reservation)["balance"]):
        raise ValidationError("El cobro supera el saldo pendiente.")
    return LedgerEntry.objects.create(
        reservation=reservation, created_by=user, **{**data, "amount": amount}
    )
