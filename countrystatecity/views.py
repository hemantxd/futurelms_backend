from rest_framework.generics import ListAPIView
from . import serializers as countrystatecity_serializers
from . import models

class CountryViewSet(ListAPIView):
    serializer_class = countrystatecity_serializers.CountrySerializer

    def get_queryset(self):
        country = self.request.query_params.get('country_sortname')
        if country:
            return models.Countries.objects.filter(sortname=country)
        return models.Countries.objects.filter()

class StateViewSet(ListAPIView):
    serializer_class = countrystatecity_serializers.StateSerializer

    def get_queryset(self):
        country = self.request.query_params.get('country_sortname')
        if country:
            return models.States.objects.filter(country__sortname=country)
        return models.States.objects.filter()

class CityViewSet(ListAPIView):
    serializer_class = countrystatecity_serializers.CitySerializer

    def get_queryset(self):
        state = self.request.query_params.get('state_id')
        if state:
            return models.Cities.objects.filter(state_id=state)
        return models.Cities.objects.filter()