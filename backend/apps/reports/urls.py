from django.urls import path
from .views import (
    SalesReportView, PurchaseReportView, StockReportView, DailySheetView,
)

urlpatterns = [
    path("sales/", SalesReportView.as_view(), name="report-sales"),
    path("purchases/", PurchaseReportView.as_view(), name="report-purchases"),
    path("stock/", StockReportView.as_view(), name="report-stock"),
    path("daily-sheet/", DailySheetView.as_view(), name="daily-sheet"),
]
