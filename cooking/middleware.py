from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class HostValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request details
        logger.debug(f"Request host: {request.get_host()}")
        logger.debug(f"Request headers: {request.headers}")
        logger.debug(f"Request META: {request.META}")
        
        # Get response
        response = self.get_response(request)
        return response 