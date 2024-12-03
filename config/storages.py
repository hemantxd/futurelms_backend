
# from django.conf import settings
# from storages.backends.s3boto import S3BotoStorage

# class MediaStorage(S3BotoStorage):
#     location = settings.MEDIAFILES_LOCATION
    
# class StaticStorage(S3BotoStorage):
#     location = settings.STATICFILES_LOCATION

from django.conf import settings
from storages.backends.azure_storage import AzureStorage

class MediaStorage(AzureStorage):
    location = settings.MEDIAFILES_LOCATION

class StaticStorage(AzureStorage):
    location = settings.STATICFILES_LOCATION


# class MediaStorage(AzureStorage):
#     account_name = settings.AZURE_ACCOUNT_NAME
#     account_key = settings.AZURE_ACCOUNT_KEY
#     #azure_container = settings.AZURE_MEDIA_CONTAINER_NAME
#     location = settings.MEDIAFILES_LOCATION
    
# class StaticStorage(AzureStorage):
#     account_name = settings.AZURE_ACCOUNT_NAME
#     account_key = settings.AZURE_ACCOUNT_KEY
#     #azure_container = settings.AZURE_STATIC_CONTAINER_NAME
#     location = settings.STATICFILES_LOCATION
