from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import FinancialYear
from .serializers import FinancialYearSerializer
from . import services


class FinancialYearViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = FinancialYearSerializer

    def get_queryset(self):
        return FinancialYear.objects.filter(user=self.request.user)

    def create(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        fy = services.open_first_fy(
            request.user, s.validated_data["start_date"], s.validated_data["end_date"]
        )
        return Response(self.get_serializer(fy).data, status=201)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        fy = self.get_object()
        nxt = services.close_year(request.user, fy)
        return Response(
            {"closed": fy.id, "next": self.get_serializer(nxt).data if nxt else None}
        )
