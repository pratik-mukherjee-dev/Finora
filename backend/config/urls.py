from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("api/accounts/", include("apps.accounts.urls")),
    # path("api/fy/", include("apps.financialyear.urls")),
    # path("api/catalogue/", include("apps.catalogue.urls")),
    # path("api/parties/", include("apps.parties.urls")),
    # path("api/stock/", include("apps.stock.urls")),
    # path("api/vouchers/", include("apps.vouchers.urls")),
    # path("api/search/", include("apps.search.urls")),
    # path("api/reports/", include("apps.reports.urls")),
]
