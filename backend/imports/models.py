import uuid
from django.conf import settings
from django.db import models

class ImportProfile(models.Model):
    name = models.CharField(max_length=100, unique=True)
    configuration = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

class ImportDraft(models.Model):
    profile = models.ForeignKey(ImportProfile, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    filename = models.CharField(max_length=200, blank=True)
    fingerprint = models.CharField(max_length=64)
    source = models.JSONField(default=dict)
    configuration = models.JSONField(default=dict)
    decisions = models.JSONField(default=dict)
    preview = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=12, default="DRAFT", choices=[("DRAFT","Borrador"),("APPLIED","Aplicado"),("DISCARDED","Descartado")])
    created_at = models.DateTimeField(auto_now_add=True)

class ImportBinding(models.Model):
    profile = models.ForeignKey(ImportProfile, on_delete=models.PROTECT)
    source_id = models.UUIDField(default=uuid.uuid4)
    reservation = models.ForeignKey("pms.Reservation", related_name="import_bindings", on_delete=models.PROTECT)
    signature = models.CharField(max_length=64, blank=True)
    content = models.JSONField(default=dict)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile","source_id"],name="unique_import_source"),
            models.UniqueConstraint(fields=["profile","reservation"],name="unique_import_reservation"),
        ]

class ImportBatch(models.Model):
    draft = models.OneToOneField(ImportDraft, on_delete=models.PROTECT, related_name="batch")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
