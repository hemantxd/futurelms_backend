# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from authentication.models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username','email', 'phonenumber')

    search_fields = ('username',)