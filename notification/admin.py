from django.contrib import admin

from . import models

admin.site.register(models.NotificationType)

admin.site.register(models.Notifications)

@admin.register(models.MobileValidation)
class MobileValidationAdmin(admin.ModelAdmin):
    list_display = ('phone_number','otp',)
    search_fields = ('phone_number', 'otp')