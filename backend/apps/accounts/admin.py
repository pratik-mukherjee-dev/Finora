from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, UserCompanySetting, License

admin.site.register(User, UserAdmin)
admin.site.register(Company)
admin.site.register(UserCompanySetting)
admin.site.register(License)
