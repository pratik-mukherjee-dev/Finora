from rest_framework import viewsets
from rest_framework.response import Response
from .models import Ledger
from .serializers import LedgerSerializer
from .selectors import models_q_company


class LedgerViewSet(viewsets.ModelViewSet):
    serializer_class = LedgerSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        qs = Ledger.objects.filter(user=self.request.user)
        company_id = self.request.query_params.get("company")
        kind = self.request.query_params.get("kind")
        if company_id:
            qs = qs.filter(models_q_company(company_id))
        if kind:
            qs = qs.filter(kind=kind)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_system:
            return Response({"detail": "System ledger cannot be deleted."}, status=400)
        return super().destroy(request, *args, **kwargs)


