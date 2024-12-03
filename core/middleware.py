from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

class HealthEndpointMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.META["PATH_INFO"] == "/stat":
            return HttpResponse("OK")