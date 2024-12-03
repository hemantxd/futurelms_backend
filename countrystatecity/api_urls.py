from django.conf.urls import include, url
from django.urls import path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

app_name = 'countrystatecity'
urlpatterns = [
    url(r'^', include(router.urls)),
    path('country/', views.CountryViewSet.as_view(), name='api_get_country'),
    url('states/', views.StateViewSet.as_view(), name='api_get_states'),
    url('cities/', views.CityViewSet.as_view(), name='api_get_cities'),
]