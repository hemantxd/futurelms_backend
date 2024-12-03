"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production')

application = get_wsgi_application()

try:
    import newrelic.agent
    newrelic.agent.initialize('newrelic.ini')
    application = newrelic.agent.WSGIApplicationWrapper(application)
except Exception as e:
    print("newrelic initialize failed")
    print(e)