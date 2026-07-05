from django.urls import path
from .views import SuggestView, RecordUsageView

urlpatterns = [
    path("suggest/", SuggestView.as_view(), name="suggest"),
    path("record/", RecordUsageView.as_view(), name="record-usage"),
]
