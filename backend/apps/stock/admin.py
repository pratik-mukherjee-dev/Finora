from django.contrib import admin
from .models import StockLedger, StockConversion

admin.site.register(StockLedger)
admin.site.register(StockConversion)
