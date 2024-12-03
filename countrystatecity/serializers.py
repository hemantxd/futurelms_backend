from . import models
from rest_framework import serializers

class CountrySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Countries
        fields = '__all__'

class StateSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.States
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cities
        fields = '__all__'