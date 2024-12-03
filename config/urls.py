from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.views.generic import TemplateView


admin.site.site_header = 'erdr Admin'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="index.html"), name="home"),
    path('api/password_reset/',
         include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/', include('authentication.api_urls')),
    path('api/', include('profiles.api_urls')),
    path('api/', include('courses.api_urls')),
    path('api/', include('notification.api_urls')),
    path('api/', include('content.api_urls')),
    path('api/', include('countrystatecity.api_urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('api/school/', include('mmp_school.api_urls')),
    # path('dashboard/', include('dashboard.urls')),
    # path('api/dashboard/', include('dashboard.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
