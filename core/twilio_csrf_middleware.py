"""
TWILIO CSRF MIDDLEWARE BYPASS
Custom middleware to bypass CSRF for Twilio webhooks
"""

from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class TwilioCsrfExemptMiddleware(MiddlewareMixin):
    """
    Middleware to exempt Twilio webhook URLs from CSRF verification
    """
    
    def process_request(self, request):
        """
        Exempt specific Twilio webhook paths from CSRF
        """
        # Twilio webhook paths that should be exempt from CSRF
        twilio_paths = [
            '/api/calls/voice-response/',
            '/api/calls/call-status/',
            '/api/calls/fallback/',
            '/api/calls/ultimate-production-webhook/',
        ]
        
        # Check if this is a Twilio webhook request
        if request.path in twilio_paths:
            # Check for Twilio User-Agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            if 'TwilioProxy' in user_agent or 'Twilio' in user_agent:
                setattr(request, '_dont_enforce_csrf_checks', True)
        
        return None