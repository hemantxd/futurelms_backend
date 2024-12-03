from .base import *

import authkey
DEBUG = False

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = authkey.EMAIL_HOST
EMAIL_HOST_USER = authkey.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = authkey.EMAIL_HOST_PASSWORD
EMAIL_PORT = authkey.EMAIL_PORT
EMAIL_USE_TLS = authkey.EMAIL_USE_TLS
DEFAULT_FROM_EMAIL = authkey.DEFAULT_FROM_EMAIL
SERVER_EMAIL = authkey.DEFAULT_FROM_EMAIL

# CREATE DATABASE devmakemypath CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_general_ci;

if 'RDS_DB_NAME' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ['RDS_DB_NAME'],
            'USER': os.environ['RDS_USERNAME'],
            'PASSWORD': os.environ['RDS_PASSWORD'],
            'HOST': os.environ['RDS_HOSTNAME'],
            'PORT': '3306',
            'OPTIONS': {
                'charset': 'utf8mb4',
                # The most forward compatible sql_mode, for 5.7
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_DATE,"
                                "NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,"
                                "innodb_strict_mode=1",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': authkey.RDS_DB_NAME,
            'USER': authkey.RDS_USERNAME,
            'PASSWORD': authkey.RDS_PASSWORD,
            'HOST': authkey.RDS_HOSTNAME,
            'PORT': '3306',
            'OPTIONS': {
                'charset': 'utf8mb4',
                # The most forward compatible sql_mode, for 5.7
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_DATE,"
                                "NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO',"
                                "innodb_strict_mode=1",
            },
        }
    }


INSTALLED_APPS = INSTALLED_APPS +[
    'storages',
]

DATABASES['default']['ATOMIC_REQUESTS'] = True

INTERNAL_IPS = ('127.0.0.1', 'localhost',)

# if 'AWS_STORAGE_BUCKET_NAME' in os.environ:
#     AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
#     if 'AWS_ACCESS_KEY_ID_LAMBDA' in os.environ:
#         AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID_LAMBDA']
#         AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY_LAMBDA']
#     else:
#         AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
#         AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
# else:
#     AWS_STORAGE_BUCKET_NAME = authkey.AWS_STORAGE_BUCKET_NAME
#     AWS_ACCESS_KEY_ID = authkey.AWS_ACCESS_KEY_ID
#     AWS_SECRET_ACCESS_KEY = authkey.AWS_SECRET_ACCESS_KEY

# AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
# AWS_S3_HOST = authkey.AWS_S3_HOST

# STATICFILES_LOCATION = 'static'
# STATICFILES_STORAGE = 'config.storages.StaticStorage'
# STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)

# MEDIAFILES_LOCATION = 'media'
# MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, MEDIAFILES_LOCATION)
# DEFAULT_FILE_STORAGE = 'config.storages.MediaStorage'

# TMP_ROOT = '/tmp'
# SECURE_LOCATION = 'secure'
# SECURE_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, SECURE_LOCATION)

# # Azure Lambda configuration 

# if 'AZURE_STORAGE_CONTAINER_NAME' in os.environ:
#     AZURE_STORAGE_CONTAINER_NAME = os.environ['AZURE_STORAGE_CONTAINER_NAME']
#     if 'AZURE_STORAGE_CONNECTION_STRING' in os.environ:
#         AZURE_STORAGE_CONNECTION_STRING = os.environ['AZURE_STORAGE_CONNECTION_STRING']
#     else:
#         AZURE_STORAGE_CONNECTION_STRING = os.environ['AZURE_STORAGE_CONNECTION_STRING_LAMBDA']
# else:
#     AZURE_STORAGE_CONTAINER_NAME = authkey.AZURE_STORAGE_CONTAINER_NAME
#     AZURE_STORAGE_CONNECTION_STRING = authkey.AZURE_STORAGE_CONNECTION_STRING

# AZURE_STORAGE_CUSTOM_DOMAIN = f"{AZURE_STORAGE_CONTAINER_NAME}.blob.core.windows.net"
# AZURE_STORAGE_HOST = authkey.AZURE_STORAGE_HOST



#Azure used for storage media and static files 

AZURE_ACCOUNT_NAME = 'mmpprodstorageaccount'
AZURE_CONTAINER = 'makemypathfiles/media'
AZURE_CONTAINER_STATIC = 'makemypathfiles/static'

MEDIAFILES_LOCATION = 'media'
DEFAULT_FILE_STORAGE = 'config.storages.MediaStorage'
MEDIA_URL = f'https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER}/{MEDIAFILES_LOCATION}/'


STATICFILES_LOCATION = 'static'
STATICFILES_STORAGE = 'config.storages.StaticStorage'
STATIC_URL = f'https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_STATIC}/{STATICFILES_LOCATION}/'

SECURE_LOCATION = 'secure'
SECURE_URL = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER}/{SECURE_LOCATION}/"

