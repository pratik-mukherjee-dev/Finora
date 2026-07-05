from django.contrib import admin
from .models import (
    SaleMaster, SaleDerived, SaleLine, Purchase, PurchaseLine,
    Received, Payment, Allocation, VoucherNumberSeq,
)

for m in (SaleMaster, SaleDerived, SaleLine, Purchase, PurchaseLine,
          Received, Payment, Allocation, VoucherNumberSeq):
    admin.site.register(m)
