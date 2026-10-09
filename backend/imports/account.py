from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from pms.models import Reservation
from pms.views import reservation_data
from .serializers import StrictSerializer

class AccountInput(StrictSerializer):
    expected_updated_at=serializers.CharField()
    ledger_signature=serializers.CharField()
    confirmed_zero=serializers.BooleanField(default=False)

@api_view(["POST"])
@transaction.atomic
def account_review(request,pk):
    serializer=AccountInput(data=request.data);serializer.is_valid(raise_exception=True)
    values=serializer.validated_data
    item=get_object_or_404(Reservation.objects.select_for_update(),pk=pk)
    dto=reservation_data(item)
    if values["expected_updated_at"]!=item.updated_at.isoformat().replace("+00:00","Z") or values["ledger_signature"]!=dto["ledger_signature"]:
        raise ValidationError("La reserva o su cuenta cambió. Abrí nuevamente la revisión.")
    if not dto["ledger"] and not values["confirmed_zero"]:raise ValidationError("La cuenta está vacía. Confirmá explícitamente que no tiene cargos ni cobros.")
    item.financial_review_required=False;item.account_reviewed_at=timezone.now();item.account_reviewed_by=request.user;item.save()
    return Response(reservation_data(item))
