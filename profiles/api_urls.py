from django.urls import path

from profiles.views import AddEmployeeUserView, ApproveInstituteViewSet, CityViewSet, DeleteUserView, FetchInstituteDetailsView, FetchTotalStudentsCountInSchoolViewSet, FetchUserProfileView, InstituteCreateViewSet, ProfileRetrieveAPIView, SearchStudentListView, SearchUserbyGroupViewSetViewSet, ShortProfileRetrieveAPIView, ProfileImageUploadView, StateViewSet, UnverifiedInstitutesViewSet, UpdateContactForVerifiedOTPViewSet, UpdateContactSendOTPViewSet, UpdateProfileDetailsViewSet, UpdateUserProfileDetailsViewSet, UserBoardViewSet, UserClassViewSet, UserGroupChangeView, UserLogoutUpdateView, UserSchoolChangeView, VerifiedInstitutesViewSet, studentsList

urlpatterns = [
    path('profile/', ProfileRetrieveAPIView.as_view()),
    path('shortprofile/', ShortProfileRetrieveAPIView.as_view()),
    path('profile/image/<user__pk>/', ProfileImageUploadView.as_view()),
    path('profile/usergroup/<user__pk>/', UserGroupChangeView.as_view()),
    path('userboard/', UserBoardViewSet.as_view()),
    path('userclass/', UserClassViewSet.as_view()),
    path('updateprofile/', UpdateProfileDetailsViewSet.as_view()),
    path('studentsList/', studentsList.as_view()),
    path('statesList/', StateViewSet.as_view()),
    path('citiesList/', CityViewSet.as_view()),
    path('updatecontactsendotp/', UpdateContactSendOTPViewSet.as_view()),
    path('updatecontact/', UpdateContactForVerifiedOTPViewSet.as_view()),
    path('searchuser/', SearchUserbyGroupViewSetViewSet.as_view()),
    path('searchuserbyparameters/', SearchStudentListView.as_view()),
    path('adduser/', AddEmployeeUserView.as_view()),
    path('fetchprofile/<user__pk>/', FetchUserProfileView.as_view()),
    path('updateuserprofile/', UpdateUserProfileDetailsViewSet.as_view()),
    path('createinstitute/', InstituteCreateViewSet.as_view()),
    path('profile/userschoolandverify/<user__pk>/', UserSchoolChangeView.as_view()),
    path('unverifiedinstitutes/', UnverifiedInstitutesViewSet.as_view()),
    path('approveinstitute/', ApproveInstituteViewSet.as_view()),
    path('profile/updateuserlogout/<user__pk>/', UserLogoutUpdateView.as_view()),
    path('profile/deleteuser/<user__pk>/', DeleteUserView.as_view()),
    path('verifiedinstitutes/', VerifiedInstitutesViewSet.as_view()),
    path('fetchinstitutedetails/<pk>/', FetchInstituteDetailsView.as_view()),
    path('fetchinstitutetotalstudents/', FetchTotalStudentsCountInSchoolViewSet.as_view()),
]