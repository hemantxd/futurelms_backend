""" URL Configuration for core auth
"""
from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm, reset_password_apiview

app_name = 'password_reset'

urlpatterns = [
    path('reset_password/', reset_password_apiview, name='reset-password-api'),
    path('confirm/', reset_password_confirm, name="reset-password-confirm"),
    path('', reset_password_request_token, name="reset-password-request"),
]
