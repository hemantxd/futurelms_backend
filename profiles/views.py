import hashlib
import os
from authentication.models import User
from content.models import Batch, LearnerBatches, UnregisteredMentorBatch, UserClassRoom
from notification.models import MobileValidation
import profiles
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveAPIView, ListAPIView, UpdateAPIView, RetrieveUpdateAPIView

from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from rest_framework.exceptions import ParseError
from rest_framework.views import APIView
from django.shortcuts import render, get_object_or_404
from profiles.exceptions import ProfileDoesNotExist
from profiles.models import City, Institute, Profile, State
from core.models import UserBoard, UserClass, UserGroup
from profiles.renderers import ProfileJSONRenderer
from profiles.serializers import CitySerializer, CreateInstituteSerializer, EditProfileSerializer, InstituteSerializer, ProfileSerializer, ShortProfileSerializer, ProfileImageUploadSerializer, StateSerializer, StudentSerializer, UserBoardSerializer, UserClassSerializer, UserGroupChangeSerializer
from core import permissions
from core import paginations as core_paginations
from django.db.models import Q
from django.conf import settings
from notification import utils as notification_utils
import random
from django.core.exceptions import ObjectDoesNotExist
import datetime
from profiles import utils as profile_utils
from datetime import datetime
import uuid


class ProfileRetrieveAPIView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ProfileJSONRenderer,)
    serializer_class = ProfileSerializer

    def retrieve(self, request, *args, **kwargs):
        
        # Try to retrieve the requested profile and throw an exception if the
        # profile could not be found.
        try:
            # We use the `select_related` method to avoid making unnecessary
            # database calls.
           
            profile = Profile.objects.select_related('user', 'state', 'city', 'studentClass').get(
                        user__id=request.user.id)
        except Profile.DoesNotExist:
            raise ProfileDoesNotExist
        
        serializer = self.serializer_class(profile)

        return Response(serializer.data, status=status.HTTP_200_OK)

class ShortProfileRetrieveAPIView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ProfileJSONRenderer,)
    serializer_class = ShortProfileSerializer

    def retrieve(self, request, *args, **kwargs):
        username=request.user.username

        # Try to retrieve the requested profile and throw an exception if the
        # profile could not be found.
        try:
            # We use the `select_related` method to avoid making unnecessary
            # database calls.
            profile = Profile.objects.select_related('user').get(
                user__username=username
            )
        except Profile.DoesNotExist:
            raise ProfileDoesNotExist

        serializer = self.serializer_class(profile)

        return Response(serializer.data, status=status.HTTP_200_OK)

class ProfileImageUploadView(UpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileImageUploadSerializer
    lookup_field = 'user__pk'
    permission_classes = (IsAuthenticated,)
    parser_class = (FileUploadParser)

    def get_queryset(self):
        profile = Profile.objects.filter(user__pk=self.kwargs.get('user__pk'))
        if not profile:
            raise ParseError("User with This id DoesNotExist")
        if not int(self.request.user.id) == int(self.kwargs.get('user__pk')):
            raise ParseError("Seems this is not valid user id")
        return profile

class UserGroupChangeView(UpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = UserGroupChangeSerializer
    lookup_field = 'user__pk'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        profile = Profile.objects.filter(user__pk=self.kwargs.get('user__pk'))
        if not profile:
            raise ParseError("User with This id DoesNotExist")
        return profile
    
    def put(self, request, *args, **kwargs):
        try:
            groupObj = UserGroup.objects.get(name=request.data['user_group'])
        except:
            return Response({"message": "Please enter valid usergroup"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            profileObj = Profile.objects.get(user__pk=self.kwargs["user__pk"])
            profileObj.user_group = groupObj
            profileObj.save()
            if groupObj.name == 'teacher':
                unreg_batch_obj = UnregisteredMentorBatch.objects.filter(phonenumber=profileObj.user.phonenumber)
                for unreg in unreg_batch_obj:
                    batch_obj = Batch.objects.create(teacher=profileObj.user, batch_code=uuid.uuid4().hex[:6].upper(), institute_room=unreg.institute_room)
                    if len(batch_obj.students.all()) < 250:
                        students = UserClassRoom.objects.prefetch_related("institute_rooms").filter(
                        institute_rooms=unreg.institute_room).values_list("user", flat=True)
                        batch_obj.students.add(*students)
                        batch_obj.save()
                        for student in students:
                            LearnerBatches.objects.create(user_id=student, batch=batch_obj)
                UnregisteredMentorBatch.objects.filter(phonenumber=profileObj.user.phonenumber).delete()
        except:
            return Response({"message": "error in updating user group"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "user group updated successfully"}, status=201)
        
class UserBoardViewSet(ListAPIView):
    serializer_class = UserBoardSerializer
    queryset = UserBoard.objects.all()

class UserClassViewSet(ListAPIView):
    serializer_class = UserClassSerializer
    queryset = UserClass.objects.all()

class UpdateProfileDetailsViewSet(RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    update_serializer_class = EditProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        profile_obj = Profile.objects.filter(User=self.request.user)
        if not profile_obj:
            raise ParseError("data DoesNotExist")
        return profile_obj

    def update(self, request, *args, **kwargs):
        username = request.data.get('username')
        if username:
            try:
                profile_obj = Profile.objects.get(user__username=username)
            except:
                profile_obj = Profile.objects.get(user=self.request.user)
        else:
            profile_obj = Profile.objects.get(user=self.request.user)
        serializer = self.update_serializer_class(
            profile_obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(self.serializer_class(profile_obj).data, status=status.HTTP_200_OK)

class UpdateContactSendOTPViewSet(RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    update_serializer_class = EditProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        profile_obj = Profile.objects.filter(User=self.request.user)
        if not profile_obj:
            raise ParseError("data DoesNotExist")
        return profile_obj

    def update(self, request, *args, **kwargs):
        contactNumber = request.data.get('contactNumber')
        isAvailable = False
        if not contactNumber:
            raise ParseError("Please enter contact number")
        own_profile_obj = Profile.objects.filter(user=self.request.user, user__phonenumber=contactNumber).exists()
        if own_profile_obj:
            isAvailable = True
        else:
            check_usage = Profile.objects.filter(user__phonenumber=contactNumber).exists()
            if check_usage:
                isAvailable = False
            else:
                isAvailable = True
        if not isAvailable:
            raise ParseError("Contact number already in use by another user")    
        profile_obj = Profile.objects.get(user=self.request.user)

        old_token = MobileValidation.objects.filter(phone_number=contactNumber)
        if old_token:
            otp = old_token[0].otp
        else:
            hash_algorithm = getattr(settings, 'PHONE_LOGIN_OTP_HASH_ALGORITHM', 'sha256')
            m = getattr(hashlib, hash_algorithm)()
            m.update(getattr(settings, 'SECRET_KEY', None).encode('utf-8'))
            m.update(os.urandom(16))
            otp = str(int(m.hexdigest(), 16))[-6:]
        phone_token = MobileValidation(phone_number=contactNumber, otp=otp)
        phone_token.save()

        message = "{0} is the Onetime password (OTP) for login. This is usable only once. Please DO NOT SHARE WITH ANYONE. ERDRCL".format(otp)
        
        success  = notification_utils.SmsMessage(contactNumber, 'ERDRCL',message, '2factor')
        count = 0
        for val in success:
            if (len(val) > 0) and (contactNumber == val[0]):
                count += 1
        if count == 0:
            raise ParseError("Some error occured while sending OTP")

        return Response(self.serializer_class(profile_obj).data, status=status.HTTP_200_OK)

class UpdateContactForVerifiedOTPViewSet(RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    update_serializer_class = EditProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        profile_obj = Profile.objects.filter(User=self.request.user)
        if not profile_obj:
            raise ParseError("data DoesNotExist")
        return profile_obj

    def update(self, request, *args, **kwargs):
        contactNumber = request.data.get('contactNumber')
        otp = request.data.get('otp')
        isAvailable = False
        if not contactNumber:
            raise ParseError("Please enter contact number")
        otp_obj = MobileValidation.objects.filter(phone_number=contactNumber, otp=otp).exists()
        if not otp_obj:
            raise ParseError("Please enter valid OTP")
        own_profile_obj = Profile.objects.filter(user=self.request.user, user__phonenumber=contactNumber).exists()
        if own_profile_obj:
            isAvailable = True
        else:
            check_usage = Profile.objects.filter(user__phonenumber=contactNumber).exists()
            if check_usage:
                isAvailable = False
            else:
                isAvailable = True
        if not isAvailable:
            raise ParseError("Contact number already in use by another user") 
        MobileValidation.objects.filter(phone_number=contactNumber).delete()
        profile_obj = Profile.objects.get(user=self.request.user)
        profile_obj.user.phonenumber = contactNumber
        profile_obj.user.save()
        profile_obj.save()

        return Response(self.serializer_class(profile_obj).data, status=status.HTTP_200_OK)
    
class studentsList(ListAPIView):
    serializer_class = StudentSerializer
    permission_classes = (permissions.IsMMPAdminUser, )
    pagination_class = core_paginations.CustomPagination

    def get_queryset(self):
        search_username = self.request.query_params.get('username', '')
        requser = self.request.user
        usergroup = UserGroup.objects.get(name='student')
        students = Profile.objects.filter(user_group=usergroup)
        usernames = [user.user.username for user in students]
        if search_username:
            return User.objects.filter(Q(username__icontains=search_username) | Q(phonenumber__icontains=search_username) | Q(profile__first_name__icontains=search_username) | Q(profile__last_name__icontains=search_username), username__in=usernames)
        else:
            return User.objects.filter(username__in=usernames)

class createStudent(GenericAPIView):
    serializer_class = StudentSerializer
    permission_classes = (permissions.IsMMPAdminUser, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class uploadStudent(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsInstituteStaff, ]
    parser_class = (FileUploadParser)

    def create(self, request, *args, **kwargs):
        csv_file = request.FILES['csv_file']
        # institute_id = self.request.user.institutestaff.institute.id
        institute_id = request.data.get('institute')
        grade_id = request.data.get('grade')
        # If error = True then mssg is a List of error strings.
        # If error = False then mssg is a List of User.
        mssg, no_error = profile_utils.bulkuploadUserCSV(
            csv_file=csv_file, institute_id=institute_id, grade_id=grade_id)

        if(no_error):
            return Response({'data': mssg, 'status': True, 'uploaded': no_error}, status=status.HTTP_200_OK)
        else:
            return Response({'errors': mssg, 'status': False, 'uploaded': no_error}, status=status.HTTP_200_OK)

class InstituteCreateViewSet(GenericAPIView):
    serializer_class = CreateInstituteSerializer
    # permission_classes = (permissions.IsMMPAdminUser, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        institute = serializer.save()
        return Response({
            "institute": InstituteSerializer(institute, context=self.get_serializer_context()).data
        })

class UnverifiedInstitutesViewSet(ListAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = InstituteSerializer

    def get_queryset(self):
        return Institute.objects.filter(is_verified=False).order_by('name')

class VerifiedInstitutesViewSet(ListAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = InstituteSerializer

    def get_queryset(self):
        return Institute.objects.filter(is_verified=True).order_by('name')

class ApproveInstituteViewSet(UpdateAPIView):
    serializer_class = InstituteSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            institute = request.data.get('institute')
            if not institute:
                raise ParseError("Please select institute")
            else:   
                institute_obj = Institute.objects.get(id=int(institute))
            if not institute_obj:
                raise ParseError("Institute with this id DoesNotExist")
            institute_obj.is_verified = True
            institute_obj.save()
        except:
            return Response({"message": "error in approving the institute"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(institute_obj).data, status=201)

class StateViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = StateSerializer

    def get_queryset(self):
        return State.objects.all().order_by('name')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CityViewSet(ListAPIView, CreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, ]
    serializer_class = CitySerializer

    def get_queryset(self):
        state = self.request.query_params.get('state')
        if state:
            return City.objects.filter(state_id=state).order_by('name')
        return City.objects.filter().order_by('name')

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class SearchUserbyGroupViewSetViewSet(ListAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    pagination_class = core_paginations.CustomPagination5
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        role = self.request.query_params.get('role')
        groupObj = UserGroup.objects.get(name=role)
        if groupObj:
            users = Profile.objects.filter(
                user_group=groupObj).order_by('id')
            if users:
                return users
            else:
                return []

class SearchStudentListView(ListAPIView):
    serializer_class = ProfileSerializer
    pagination_class = core_paginations.CustomPagination5
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        username = self.request.query_params.get('username')
        role = self.request.query_params.get('role')
        groupObj = UserGroup.objects.get(name=role)
        rdate1 = self.request.query_params.get('rdate1')
        if (rdate1 and rdate1 != 'null'):
            rdate1 = datetime.datetime.strptime(rdate1, "%Y-%m-%d")
        else:
            rdate1 = None
        rdate2 = self.request.query_params.get('rdate2')
        if (rdate2 and rdate2 != 'null'):
            rdate2 = datetime.datetime.strptime(rdate2, "%Y-%m-%d")
            rdate2 += datetime.timedelta(days=1)
        else:
            rdate2 = None
        if (username and not (username == 'null' or username == 'undefined')):
            try:
                phonenumber = int(username)
            except:
                phonenumber = None
            if rdate1 and rdate2:
                if phonenumber:
                    userdata = Profile.objects.filter(user_group=groupObj, created_at__gte=rdate1, created_at__lte=rdate2).filter(Q(user__username__icontains=username) | Q(user__email__icontains=username) | Q(
                        first_name__icontains=username) | Q(last_name__icontains=username) | Q(user__phonenumber__icontains=phonenumber))
                else:
                    fullname = username.split(' ')
                    if len(fullname) > 1:
                        fname, lname = username.split(' ')[0], username.split(' ')[-1]
                        userdata = Profile.objects.filter(user_group=groupObj, created_at__gte=rdate1, created_at__lte=rdate2).filter(Q(user__username__icontains=username) | Q(user__email__icontains=username) | (Q(first_name__icontains=fname) & Q(last_name__icontains=lname)))
                    else:
                        userdata = Profile.objects.filter(user_group=groupObj, created_at__gte=rdate1, created_at__lte=rdate2).filter(Q(user__username__icontains=username) | Q(user__email__icontains=username) | Q(first_name__icontains=username) | Q(last_name__icontains=username))
            else:
                if phonenumber:
                        userdata = Profile.objects.filter(user_group=groupObj).filter(Q(user__username__icontains=username) | Q(user__email__icontains=username) | Q(
                            first_name__icontains=username) | Q(last_name__icontains=username) | Q(user__phonenumber__icontains=phonenumber))
                else:
                    fullname = username.split(' ')
                    if len(fullname) > 1:
                        fname, lname = username.split(' ')[0], username.split(' ')[-1]
                        userdata = Profile.objects.filter(user_group=groupObj).filter(Q(user__username__icontains=username) | Q(user__email__icontains=username) | (Q(first_name__icontains=fname) & Q(last_name__icontains=lname)))
                    else:
                        userdata = Profile.objects.filter(user_group=groupObj).filter(Q(user__username__icontains=username) | Q(user__email__icontains=username) | Q(first_name__icontains=username) | Q(last_name__icontains=username))
        elif rdate1 and rdate2:
            userdata = Profile.objects.filter(user_group=groupObj, created_at__gte=rdate1, created_at__lte=rdate2)
        else:
            userdata = Profile.objects.filter(user_group=groupObj)
        return userdata

class AddEmployeeUserView(CreateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        contactNumber = request.data.get('phonenumber')
        email = request.data.get('email')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        role = request.data.get('user_group')
        groupObj = UserGroup.objects.get(name=role)
        isAvailable = False
        if not contactNumber:
            raise ParseError("Please enter contact number")
        check_usage = Profile.objects.filter(user__phonenumber=contactNumber).exists()
        if check_usage:
            isAvailable = False
        else:
            isAvailable = True
        if not isAvailable:
            raise ParseError("Contact number already in use by another user") 
        check_usage_email = Profile.objects.filter(user__email=email).exists()
        if check_usage_email:
            isAvailable = False
        else:
            isAvailable = True
        if not isAvailable:
            raise ParseError("Email number already in use by another user")   
        last_user_created_id = User.objects.all().last().id
        username = create_username(str(10000 + last_user_created_id))
        fullname = first_name + ' ' + last_name
        user_obj = User.objects.create(username=username, email=email, phonenumber=contactNumber, fullname=fullname) 
        user_obj.set_password(username)
        user_obj.save()
        profile_obj = Profile.objects.get(user=user_obj)
        profile_obj.user_group=groupObj
        profile_obj.contact_verified = True
        profile_obj.account_verified = True
        profile_obj.save()
        return Response(self.serializer_class(profile_obj).data, status=status.HTTP_201_CREATED)

def create_username(username):
    check_count = 1
    while check_username(username):
        if check_count >= 2:
            username = username + str(check_count)
        if len(username) < 6:
            username = username + \
            "".join(map(str, random.sample(range(1, 10), 6-len(username))))
        check_count += 1
    return username

def check_username(username):
    try:
        User.objects.get(username=username)
    except ObjectDoesNotExist:
        return False
    return True

class FetchUserProfileView(RetrieveAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'user__pk'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        profile = Profile.objects.filter(user__pk=self.kwargs.get('user__pk'))
        if not profile:
            raise ParseError("User with This id DoesNotExist")
        return profile

class UpdateUserProfileDetailsViewSet(RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    update_serializer_class = EditProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        try:
            user=None
            if self.request.query_params.get('user'):
                user= User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        profile_obj = Profile.objects.filter(user=user)
        if not profile_obj:
            raise ParseError("data DoesNotExist")
        return profile_obj

    def update(self, request, *args, **kwargs):
        contactNumber = request.data.get('phonenumber')
        email = request.data.get('email')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        try:
            user=None
            if self.request.query_params.get('user'):
                user= User.objects.get(username=self.request.query_params.get('user'))
            else:
                user = self.request.user
        except:
            user = self.request.user
        isAvailable = False
        if not contactNumber:
            raise ParseError("Please enter contact number")
        own_profile_obj = Profile.objects.filter(user=user, user__phonenumber=contactNumber).exists()
        if own_profile_obj:
            isAvailable = True
        else:
            check_usage = Profile.objects.filter(user__phonenumber=contactNumber).exists()
            if check_usage:
                isAvailable = False
            else:
                isAvailable = True
        if not isAvailable:
            raise ParseError("Contact number already in use by another user") 
        isAvailableEmail = False
        email_own_profile_obj = Profile.objects.filter(user=user, user__email=email).exists()
        if email_own_profile_obj:
            isAvailableEmail = True
        else:
            check_usage_email = Profile.objects.filter(user__email=email).exists()
            if check_usage_email:
                isAvailableEmail = False
            else:
                isAvailableEmail = True
        if not isAvailableEmail:
            raise ParseError("Email already in use by another user")
        profile_obj = Profile.objects.get(user=user)
        profile_obj.first_name=first_name
        profile_obj.last_name=last_name
        # if profile_obj.user.email != email:
        profile_obj.user.email=email
        # if profile_obj.user.phonenumber != contactNumber:
        profile_obj.user.phonenumber = contactNumber
        profile_obj.user.save()
        profile_obj.save()

        return Response(self.serializer_class(profile_obj).data, status=status.HTTP_200_OK)

class UserSchoolChangeView(UpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = UserGroupChangeSerializer
    lookup_field = 'user__pk'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        profile = Profile.objects.filter(user__pk=self.kwargs.get('user__pk'))
        if not profile:
            raise ParseError("User with This id DoesNotExist")
        return profile
    
    def put(self, request, *args, **kwargs):
        try:
            schoolObj = Institute.objects.get(id=request.data['institute'])
        except:
            return Response({"message": "Please enter valid institute"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            profileObj = Profile.objects.get(user__pk=self.kwargs["user__pk"])
            profileObj.institute = schoolObj
            profileObj.contact_verified = True
            profileObj.save()
        except:
            return Response({"message": "error in updating school"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "School updated successfully"}, status=201)

class UserLogoutUpdateView(UpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ShortProfileSerializer
    lookup_field = 'user__pk'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        profile = Profile.objects.filter(user__pk=self.kwargs.get('user__pk'))
        if not profile:
            raise ParseError("User with This id DoesNotExist")
        return profile
    
    def put(self, request, *args, **kwargs):
        current_date = datetime.now()
        try:
            profileObj = Profile.objects.get(user__pk=self.kwargs["user__pk"])
            profileObj.logout_updated_on = current_date
            profileObj.save()
        except:
            return Response({"message": "error in updating logout time"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "user logout time updated successfully"}, status=201)

class DeleteUserView(UpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ShortProfileSerializer
    lookup_field = 'user__pk'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        profile = Profile.objects.filter(user__pk=self.kwargs.get('user__pk'))
        if not profile:
            raise ParseError("User with This id DoesNotExist")
        return profile
    
    def put(self, request, *args, **kwargs):
        try:
            Profile.objects.filter(user__pk=self.kwargs["user__pk"]).delete()
            User.objects.filter(id=self.kwargs["user__pk"]).delete()
        except:
            return Response({"message": "some error occured"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "account deleted successfully"}, status=201)

class FetchInstituteDetailsView(RetrieveAPIView):
    queryset = Institute.objects.all()
    serializer_class = InstituteSerializer
    lookup_field = 'pk'
    permission_classes = (AllowAny,)

    def get_queryset(self):
        school = Institute.objects.filter(pk=self.kwargs.get('pk'))
        if not school:
            raise ParseError("Institute with This id DoesNotExist")
        return school

class FetchTotalStudentsCountInSchoolViewSet(ListAPIView,):
    permission_classes = [IsAuthenticatedOrReadOnly, ]

    def get_queryset(self):
        institute_id = self.request.query_params.get('institute', None)
        
        if not institute_id:
            raise ParseError("Please enter institute Id")
        
        institute_id = int(institute_id)
        
        students_count = Profile.objects.filter(institute__id=institute_id).count()
        return students_count

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            return Response({
                'totalusers':queryset,
            })
        except:
            return Response({'error': 'Error.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
