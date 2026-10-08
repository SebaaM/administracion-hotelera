from rest_framework import serializers
from django.conf import settings
from .models import Hotel, Room, Unit, Reservation, LedgerEntry, Maintenance


class HotelSerializer(serializers.ModelSerializer):
    timezone = serializers.SerializerMethodField()
    logo = serializers.ImageField(required=False, allow_null=True)
    cover = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Hotel
        fields = [
            "name",
            "subtitle",
            "primary_color",
            "secondary_color",
            "accent_color",
            "logo",
            "cover",
            "sections",
            "currency",
            "timezone",
        ]
        read_only_fields = ["currency"]

    def get_timezone(self, obj):
        return settings.TIME_ZONE

    def validate_sections(self, value):
        allowed = {"reservations", "billing", "cleaning", "maintenance"}
        if (
            not isinstance(value, dict)
            or set(value) - allowed
            or any(type(v) is not bool for v in value.values())
        ):
            raise serializers.ValidationError(
                "Las secciones deben ser opciones válidas de mostrar u ocultar."
            )
        return value


class ReservationInput(serializers.ModelSerializer):
    unit_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    rates = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0),
        required=False,
    )

    class Meta:
        model = Reservation
        fields = [
            "guest",
            "contact",
            "document",
            "guests",
            "start",
            "end",
            "notes",
            "unit_ids",
            "rates",
        ]

    def validate(self, data):
        if data["end"] <= data["start"]:
            raise serializers.ValidationError(
                "La salida debe ser posterior a la llegada."
            )
        if (data["end"] - data["start"]).days > 366:
            raise serializers.ValidationError("La estadía no puede superar 366 noches.")
        return data


class GuestInput(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ["guest", "contact", "document", "notes"]


class EntryInput(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ["kind", "description", "amount", "method"]

    def validate(self, data):
        if data["kind"] == "PAYMENT" and not data.get("method"):
            raise serializers.ValidationError("Elegí el medio de pago.")
        return data


class RoomInput(serializers.ModelSerializer):
    beds = serializers.IntegerField(
        min_value=1, max_value=40, required=False, write_only=True
    )
    rate = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, write_only=True
    )

    class Meta:
        model = Room
        fields = ["name", "kind", "capacity", "image", "active", "beds", "rate"]

    def validate_capacity(self, value):
        if value > 40:
            raise serializers.ValidationError("La capacidad máxima es 40.")
        return value


class UnitInput(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["name", "rate", "active"]


class MaintenanceInput(serializers.ModelSerializer):
    class Meta:
        model = Maintenance
        fields = ["room", "unit", "title", "notes", "start", "end", "blocking"]

    def validate(self, data):
        if data["end"] <= data["start"]:
            raise serializers.ValidationError(
                "El fin del bloqueo debe ser posterior al inicio."
            )
        if data.get("unit") and data["unit"].room_id != data["room"].pk:
            raise serializers.ValidationError(
                "La cama no pertenece a la habitación seleccionada."
            )
        return data


def validated_image(upload):
    from PIL import Image, UnidentifiedImageError
    from django.core.files.base import ContentFile
    import io, uuid

    if upload.size > 5 * 1024 * 1024:
        raise serializers.ValidationError("La imagen no puede superar 5 MB.")
    try:
        with Image.open(upload) as picture:
            if picture.width * picture.height > 16000000:
                raise serializers.ValidationError(
                    "La imagen es demasiado grande (máximo 16 megapíxeles)."
                )
            picture.load()
            picture.thumbnail((1600, 1600))
            output = io.BytesIO()
            picture.convert("RGBA").save(output, format="PNG")
            return ContentFile(output.getvalue(), name=f"{uuid.uuid4().hex}.png")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise serializers.ValidationError("Subí una imagen PNG, JPG o WebP válida.")
