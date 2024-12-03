from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from authentication.models import User
from notification import models as notification_models

class PhoneTokenCreateSerializer(ModelSerializer):
    phone_number = serializers.CharField()

    class Meta:
        model = notification_models.MobileValidation
        fields = ('phone_number',)


class PhoneTokenValidateSerializer(ModelSerializer):
    phone_number = serializers.CharField()
    otp = serializers.CharField(max_length=40)

    class Meta:
        model =notification_models.MobileValidation
        fields = ('phone_number', 'otp')

class NotificationSerializers(serializers.ModelSerializer):

    class Meta:
        model = notification_models.Notifications
        fields = '__all__'

class NotificationCountSerializer(serializers.ModelSerializer):
    notification_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('notification_count',)

    def get_notification_count(self, instance):
        return instance.notifications_set.filter(is_read=False).count()
