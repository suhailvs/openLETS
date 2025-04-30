from django.contrib import admin
from core.models import * 

from django.contrib.auth.admin import UserAdmin
admin.site.register(User,UserAdmin)
admin.site.register(UserBalance)
admin.site.register(Balance)
admin.site.register(Transaction)
admin.site.register(TransactionRecord)
admin.site.register(Currency)
admin.site.register(Resolution)
admin.site.register(UserResolution)
admin.site.register(ExchangeRate)