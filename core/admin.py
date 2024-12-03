from django.contrib import admin

from . import models

admin.site.register(models.UserGroup)

admin.site.register(models.UserBoard)

admin.site.register(models.UserClass)

admin.site.register(models.UserSeasson)