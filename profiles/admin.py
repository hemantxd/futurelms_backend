from django.contrib import admin

from . import models

@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user','contact_verified', 'account_verified')
    search_fields = ('user__phonenumber', 'user__username')

admin.site.register(models.State)
admin.site.register(models.City)
admin.site.register(models.Institute)