from django.urls import path

from authentication.views import LoginAPIView, LogoutView, RegistrationAPIView, UpdatePasswordApiView, UpdateStudentPasswordApiView, UserRetrieveUpdateAPIView, LoginOTPAPIView

urlpatterns = [
    path('user/', UserRetrieveUpdateAPIView.as_view(), name='profile'),
    path('users/register/', RegistrationAPIView.as_view(), name='register'),
    path('users/login/', LoginAPIView.as_view(), name='login'),
    path('users/logout/', LogoutView.as_view(), name='logout'),
    path("users/otplogin/", LoginOTPAPIView.as_view(), name="otplogin"),
    path("users/updatepassword/", UpdatePasswordApiView.as_view(), name="updatepassword"),
    path("users/updatestudentpassword/", UpdateStudentPasswordApiView.as_view(), name="updatestudentpassword"),
]