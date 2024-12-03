from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import logout

from authentication.models import User

from .renderers import UserJSONRenderer
from .serializers import (
    LoginSerializer, RegistrationSerializer, UserSerializer,OtpLoginSerializer
)

class LoginOTPAPIView(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = OtpLoginSerializer

    def post(self, request):
        user = request.data.get("user", {})

        # Notice here that we do not call `serializer.save()` like we did for
        # the registration endpoint. This is because we don't actually have
        # anything to save. Instead, the `validate` method on our serializer
        # handles everything we need.
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)



class UserRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = UserSerializer

    def retrieve(self, request, *args, **kwargs):
        # There is nothing to validate or save here. Instead, we just want the
        # serializer to handle turning our `User` object into something that
        # can be JSONified and sent to the client.
        serializer = self.serializer_class(request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        user_data = request.data.get('user', {})

        serializer_data = {
            'email': user_data.get('email', request.user.email),
            'phonenumber': user_data.get('phonenumber', request.user.phonenumber),
            'profile': {
                'first_name': user_data.get('first_name', request.user.profile.first_name),
                'last_name': user_data.get('last_name', request.user.profile.last_name),
                'address': user_data.get('address', request.user.profile.address),
                'studentClass': user_data.get('studentClass', request.user.profile.studentClass.id if request.user.profile.studentClass else None),
                'studentBoard': user_data.get('studentBoard', request.user.profile.studentBoard.id if request.user.profile.studentBoard else None),
                'rollno': user_data.get('rollno', request.user.profile.rollno),
                'city': user_data.get('city', request.user.profile.city.id if request.user.profile.city else None),
                'state': user_data.get('state', request.user.profile.state.id if request.user.profile.state else None),
                'pincode': user_data.get('pincode', request.user.profile.pincode)
            }
        }
        # Here is that serialize, validate, save pattern we talked about
        # before.
        serializer = self.serializer_class(
            request.user, data=serializer_data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class LoginAPIView(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = LoginSerializer

    def post(self, request):
        user = request.data.get('user', {})

        # Notice here that we do not call `serializer.save()` like we did for
        # the registration endpoint. This is because we don't actually have
        # anything to save. Instead, the `validate` method on our serializer
        # handles everything we need.
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        logout(request)

        return Response({}, status=status.HTTP_204_NO_CONTENT)

class RegistrationAPIView(APIView):
    # Allow any user (authenticated or not) to hit this endpoint.
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = RegistrationSerializer

    def post(self, request):
        user = request.data.get('user', {})

        # The create serializer, validate serializer, save serializer pattern
        # below is common and you will see it a lot throughout this course and
        # your own work later on. Get familiar with it.
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UpdatePasswordApiView(APIView):
    permission_classes = (IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        data = request.data
        password = data['password']
        user = request.user
        user.set_password(password)
        user.save()

        return Response({'status': 'Done'}, status=status.HTTP_200_OK)

class UpdateStudentPasswordApiView(APIView):
    permission_classes = (IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        username = request.data.get('user')
        user_obj = User.objects.get(username=username)
        data = request.data
        password = data['password']
        user_obj.set_password(password)
        user_obj.save()

        return Response({'status': 'Done'}, status=status.HTTP_200_OK)