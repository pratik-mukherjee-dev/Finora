from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Party
from .serializers import PartySerializer, PartyLedgerSerializer
from .selectors import ledger_entries
from . import services


class PartyViewSet(viewsets.ModelViewSet):
    serializer_class = PartySerializer

    def get_queryset(self):
        return Party.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            party = services.create_party(
                self.request.user,
                serializer.validated_data["name"],
                phone=serializer.validated_data.get("phone"),
                address=serializer.validated_data.get("address"),
                opening_balance=serializer.validated_data.get("opening_balance", 0),
            )
        except IntegrityError:
            raise ValidationError({
                "name": "Party with this name already exists",
            })
        serializer.instance = party


    @action(detail=True, methods=["get"])
    def ledger(self, request, pk=None):
        party = self.get_object()
        return Response(PartyLedgerSerializer(ledger_entries(party), many=True).data)
