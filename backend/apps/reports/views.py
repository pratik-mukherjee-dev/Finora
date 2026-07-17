from rest_framework.views import APIView
from rest_framework.response import Response

from apps.vouchers.serializers import (
    SaleDerivedSerializer, PurchaseSerializer,
)
from apps.stock.serializers import StockLedgerSerializer
from . import selectors


def _params(request):
    p = request.query_params
    return {
        "company": p.get("company"),
        "party": p.get("party"),
        "date_from": p.get("date_from"),
        "date_to": p.get("date_to"),
        "category": p.get("category"),
        "item": p.get("item"),
    }


class DashboardView(APIView):
    def get(self, request):
        date = request.query_params.get("date")
        company = request.query_params.get("company")
        return Response(selectors.dashboard(request.user, date, company))



class SalesReportView(APIView):
    def get(self, request):
        f = _params(request)
        r = selectors.sales_report(request.user, **f)
        return Response({
            "count": r["count"], "total": r["total"],
            "rows": SaleDerivedSerializer(r["rows"], many=True).data,
        })


class PurchaseReportView(APIView):
    def get(self, request):
        f = _params(request)
        r = selectors.purchase_report(request.user, **f)
        return Response({
            "count": r["count"], "total": r["total"],
            "rows": PurchaseSerializer(r["rows"], many=True).data,
        })


class StockReportView(APIView):
    def get(self, request):
        p = request.query_params
        r = selectors.stock_report(
            request.user, company=p.get("company"), mapping=p.get("mapping"),
            date_from=p.get("date_from"), date_to=p.get("date_to"),
        )
        return Response({
            "in": r["in"], "out": r["out"],
            "rows": StockLedgerSerializer(r["rows"], many=True).data,
        })


class DailySheetView(APIView):
    def get(self, request):
        date = request.query_params.get("date")
        company = request.query_params.get("company")
        return Response(selectors.daily_sheet(request.user, date, company))
