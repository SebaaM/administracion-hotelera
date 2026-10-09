from django.db import models
from django.db.models import Q, F
from django.core.validators import RegexValidator, MinValueValidator
from decimal import Decimal
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators

hex_color = RegexValidator(
    r"^#[0-9a-fA-F]{6}$", "Usá un color hexadecimal de seis dígitos."
)


class Hotel(models.Model):
    name = models.CharField(max_length=100, default="Nido Hotel & Hostel")
    subtitle = models.CharField(max_length=120, default="Recepción", blank=True)
    primary_color = models.CharField(
        max_length=7, default="#153a43", validators=[hex_color]
    )
    secondary_color = models.CharField(
        max_length=7, default="#0d766e", validators=[hex_color]
    )
    accent_color = models.CharField(
        max_length=7, default="#e9a23b", validators=[hex_color]
    )
    logo = models.ImageField(upload_to="brand/", blank=True)
    cover = models.ImageField(upload_to="brand/", blank=True)
    sections = models.JSONField(default=dict)
    currency = models.CharField(max_length=3, default="ARS")
    updated_at = models.DateTimeField(auto_now=True)


class Room(models.Model):
    name = models.CharField(max_length=60, unique=True)
    kind = models.CharField(
        max_length=10, choices=[("PRIVATE", "Privada"), ("SHARED", "Compartida")]
    )
    capacity = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1)]
    )
    image = models.ImageField(upload_to="rooms/", blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]


class Unit(models.Model):
    room = models.ForeignKey(Room, related_name="units", on_delete=models.PROTECT)
    name = models.CharField(max_length=60)
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    cleaning = models.CharField(
        max_length=10,
        default="CLEAN",
        choices=[
            ("CLEAN", "Lista"),
            ("DIRTY", "Pendiente"),
            ("CLEANING", "En limpieza"),
        ],
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["room__name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["room", "name"], name="unique_unit_name")
        ]


class Reservation(models.Model):
    guest = models.CharField(max_length=120)
    contact = models.CharField(max_length=120, blank=True)
    document = models.CharField(max_length=80, blank=True)
    guests = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    start = models.DateField()
    end = models.DateField()
    status = models.CharField(
        max_length=20,
        default="CONFIRMED",
        choices=[
            ("CONFIRMED", "Confirmada"),
            ("IN_HOUSE", "Alojado"),
            ("CHECKED_OUT", "Finalizada"),
            ("CANCELLED", "Cancelada"),
        ],
    )
    notes = models.TextField(blank=True)
    import_notes = models.TextField(blank=True)
    import_colors = models.JSONField(default=list)
    financial_review_required = models.BooleanField(default=False)
    account_reviewed_at = models.DateTimeField(null=True, blank=True)
    account_reviewed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.PROTECT, related_name='reviewed_accounts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="reservation_positive_stay"
            )
        ]


class Allocation(models.Model):
    reservation = models.ForeignKey(
        Reservation, related_name="allocations", on_delete=models.PROTECT
    )
    unit = models.ForeignKey(Unit, related_name="allocations", on_delete=models.PROTECT)
    start = models.DateField()
    end = models.DateField()
    rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="allocation_positive_stay"
            ),
            models.UniqueConstraint(
                fields=["reservation", "unit"], name="unique_reservation_unit"
            ),
            ExclusionConstraint(
                name="no_overlapping_active_allocation",
                expressions=[
                    ("unit", RangeOperators.EQUAL),
                    (
                        models.Func(
                            F("start"),
                            F("end"),
                            models.Value("[)"),
                            function="DATERANGE",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(active=True),
            ),
        ]


class LedgerEntry(models.Model):
    reservation = models.ForeignKey(
        Reservation, related_name="ledger", on_delete=models.PROTECT
    )
    kind = models.CharField(
        max_length=10, choices=[("CHARGE", "Cargo"), ("PAYMENT", "Cobro")]
    )
    description = models.CharField(max_length=160)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    method = models.CharField(
        max_length=12,
        blank=True,
        choices=[
            ("CASH", "Efectivo"),
            ("CARD", "Tarjeta"),
            ("TRANSFER", "Transferencia"),
            ("OTHER", "Otro"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("auth.User", on_delete=models.PROTECT)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="ledger_positive_amount"
            )
        ]


class CleaningTask(models.Model):
    unit = models.ForeignKey(
        Unit, related_name="cleaning_tasks", on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=12,
        default="PENDING",
        choices=[
            ("PENDING", "Pendiente"),
            ("IN_PROGRESS", "En curso"),
            ("DONE", "Lista"),
        ],
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["unit"],
                condition=~Q(status="DONE"),
                name="one_open_cleaning_task",
            )
        ]


class Maintenance(models.Model):
    room = models.ForeignKey(Room, related_name="maintenance", on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    start = models.DateField()
    end = models.DateField()
    blocking = models.BooleanField(default=True)
    status = models.CharField(
        max_length=12,
        default="OPEN",
        choices=[
            ("OPEN", "Pendiente"),
            ("IN_PROGRESS", "En curso"),
            ("DONE", "Resuelta"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="maintenance_positive_period"
            )
        ]
