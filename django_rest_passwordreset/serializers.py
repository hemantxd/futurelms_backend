from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth import get_user_model
User = get_user_model()

from rest_framework import serializers

from profiles import models as profiles_models
from django.db.models import Q

class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, email):
        try:
            User.objects.get(email=email)
        except:
            raise serializers.ValidationError('Email Does not exist')
        return email

class PhoneOrEmailSerializer(serializers.Serializer):
    email = serializers.CharField()

    def validate_email(self, email):
        try:
            profile_obj = profiles_models.Profile.objects.get(Q(user__phonenumber__iexact=email) | Q(user__email__iexact=email))
        except:
            raise serializers.ValidationError('Email Does not exist')
        return profile_obj.user


class PasswordTokenSerializer(serializers.Serializer):
    password = serializers.CharField(label=_("Password"), style={'input_type': 'password'})
    token = serializers.CharField()

    def validate_password(self, password):
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)

        return password


class ResetPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate_old_password(self, old_password):
        user = self.context['request'].user
        if not user.check_password(old_password):
            raise serializers.ValidationError('Incorrect Old Password.')

        return old_password

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError('Password did not match.')

        return attrs