from rest_framework.views import APIView
from rest_framework.response import Response

from . import selectors, services


class SuggestView(APIView):
    def get(self, request):
        entity = request.query_params.get("type", "").upper()
        q = request.query_params.get("q", "").strip()
        limit = int(request.query_params.get("limit", 10))
        if not q:
            return Response([])
        if entity == "ITEM":
            rows = selectors.suggest_items(request.user, q, limit)
            data = [{"id": r.id, "name": r.name, "base_unit": r.base_unit} for r in rows]
        elif entity == "PARTY":
            rows = selectors.suggest_parties(request.user, q, limit)
            data = [{"id": r.id, "name": r.name} for r in rows]
        else:
            data = []
        return Response(data)


class RecordUsageView(APIView):
    def post(self, request):
        services.record_usage(
            request.user,
            request.data["type"].upper(),
            int(request.data["id"]),
        )
        return Response(status=204)
