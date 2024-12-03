from django.conf.urls import include, url
from django.urls import path

from . import views

urlpatterns = [
    path('send_otp/', views.GenerateOTP.as_view(), name='send_otp'),
    path('verify_otp/', views.ValidateOTP.as_view(), name='verify_otp'),
    path('send_applink/', views.SendAppLink.as_view(), name='send_applink'),
    path('notifications_count/', views.NotificationCountAPIView.as_view(), name='notifications_count'),
    path('notifications_list/<status>/', views.NotificationAPIView.as_view(), name='notifications_list'),
    path('change_notification_status/<int:pk>/', views.ChangeNotificationStatusAPIView.as_view(), name='change_notification_status'),
    path('searchuserbynumber/', views.SearchUserByNumberSetViewSet.as_view(),
         name='searchuserbynumber'),
    path('send_bulk_notifications/', views.CreateBulkCommonNotification.as_view(), name='send_bulk_notifications'),
]