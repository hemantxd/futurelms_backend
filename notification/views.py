from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from authentication.models import User
from profiles.models import Institute, Profile
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework.exceptions import ParseError
from notification import models as notification_models
from notification import serializers as notification_serializers
from notification import utils as notification_utils
from core import permissions as core_permissions
from core import paginations as core_paginations
from django.db import transaction
from authentication.serializers import UserSerializer
from profiles.serializers import ProfileSerializer
from rest_framework.views import APIView

class GenerateOTP(CreateAPIView):
    queryset = notification_models.MobileValidation.objects.all()
    serializer_class = notification_serializers.PhoneTokenCreateSerializer

    def post(self, request, format=None):
        ser = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        if ser.is_valid():
            token = notification_models.MobileValidation.create_otp_for_number(
                request.data.get('phone_number')
            )
            if token:
                phone_token = self.serializer_class(
                    token, context={'request': request}
                )
                data = phone_token.data
                return Response(data)
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)


class ValidateOTP(CreateAPIView):
    queryset = notification_models.MobileValidation.objects.all()
    serializer_class = notification_serializers.PhoneTokenValidateSerializer

    def post(self, request, format=None):
        # Get the patient if present or result None.
        ser = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if ser.is_valid():
            phone_number = request.data.get('phone_number')
            otp = request.data.get("otp")
            user = User.objects.filter(phonenumber=phone_number).first()
            if user is None:
                return Response(
                        {'reason': "Account doesn't exists, please register first to login"},
                        status=status.HTTP_406_NOT_ACCEPTABLE
                    )
            try:
                validation_obj = notification_models.MobileValidation.objects.filter(phone_number=phone_number, otp=otp).last()
                # if validation_obj:
                    # validation_obj.delete()
                if not validation_obj:
                    return Response(
                        {'reason': "Invalid OTP"},
                        status=status.HTTP_406_NOT_ACCEPTABLE
                    )
                try:
                    with transaction.atomic():
                        user = self.request.user
                        profile_obj = Profile.objects.get(user=user)
                        user.phonenumber = request.data.get('phone_number')
                        user.save()
                except:
                    profile_obj = Profile.objects.get(user__phonenumber=request.data.get('phone_number'))
                profile_obj.contact_verified = True
                profile_obj.save()
                return Response({"phone_number":phone_number}, status=status.HTTP_200_OK)
            except ObjectDoesNotExist:
                return Response(
                    {'reason': "Invalid OTP"},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)

class SendAppLink(CreateAPIView):

    def post(self, request, format=None):
        number = request.data.get('number')
        message="Thanks you for showing interest in MAKEMYPATH APP mobile app. Click link to download: https://makemypathapp.app.link"
        vars_data = {("VAR1","https://makemypathapp.app.link")}
        success, errors  = notification_utils.SmsMessage(number, 'APTINN', message, vars_data, '2factor', 'MAKEMYPATHAPPLINK')
        if number not in success:
            return Response({'reason': 'Invalid Number'}, status=status.HTTP_406_NOT_ACCEPTABLE)
        return Response({"number":number}, status=status.HTTP_200_OK)


class NotificationAPIView(ListAPIView):
    serializer_class = notification_serializers.NotificationSerializers
    permission_classes = (core_permissions.IsStudent,)
    pagination_class = core_paginations.CustomPagination

    def get_queryset(self):
        user = self.request.user
        status = self.kwargs["status"]
        if status == 'read':
            status = True
        elif status == 'unread':
            status = False
        else:
            return notification_models.Notifications.objects.filter(id=None)
        notification_queryset = notification_models.Notifications.objects.filter(user=user, is_read=status).order_by('-id')
        return notification_queryset

class ChangeNotificationStatusAPIView(RetrieveAPIView):
    serializer_class = notification_serializers.NotificationSerializers
    permission_classes = (core_permissions.IsStudent,)
    lookup_field = 'pk'

    def get_queryset(self):
        pk = self.kwargs["pk"]
        try:
            user_notifications = notification_models.Notifications.objects.get(user=self.request.user, id=pk)
            user_notifications.is_read = True
            user_notifications.save()
        except:
            raise ParseError('No data found.')
        return notification_models.Notifications.objects.filter(id=pk)


class NotificationCountAPIView(RetrieveAPIView):
    serializer_class = notification_serializers.NotificationCountSerializer
    permission_classes = (core_permissions.IsStudent,)

    def get_object(self):
        return self.request.user

class SearchUserByNumberSetViewSet(ListAPIView):
    queryset = User.objects.all()
    serializer_class = ProfileSerializer

    def get_queryset(self):
        searchtext = self.request.query_params.get('phonenumber')
        if searchtext:
            user_obj = Profile.objects.filter(
                user__phonenumber=searchtext, account_verified=True)
            if user_obj:
                return user_obj
            else:
                return []

class CreateBulkCommonNotification(APIView):
    serializer_class = notification_serializers.NotificationSerializers

    def post(self, request, *args, **kwargs):
        try:
            notification = request.data.get('notification')
            subject = request.data.get('subject')
            institute = request.data.get('institute')
            image = request.data.get('image')
            notification_type = notification_models.NotificationType.objects.get(name="support")
            user=None
            userIds = []
            institute_obj = None
            if institute and not institute == "null":
                profiles = Profile.objects.filter(institute_id=institute)
                userIds.extend(profiles.values_list("user", flat=True))
                users= User.objects.filter(id__in=userIds)
                institute_obj = Institute.objects.get(id=institute)
            else:
                profiles = Profile.objects.filter(institute_id__isnull=True)
                userIds.extend(profiles.values_list("user", flat=True))
                users= User.objects.filter(id__in=userIds)
                
            if users:
                for user in users:
                    if image:
                        notification_models.Notifications.objects.create(user=user, notification=notification, image=image, subject=subject, institute=institute_obj, type=notification_type)
                    else:
                        notification_models.Notifications.objects.create(user=user, notification=notification, subject=subject, institute=institute_obj, type=notification_type)
        except:
            return Response({"message": "error in sending bulk notification"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "bulk notification sent successfully"}, status=201)