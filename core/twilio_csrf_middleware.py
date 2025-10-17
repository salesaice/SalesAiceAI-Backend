"""
TWILIO CSRF MIDDLEWARE BYPASS - PRODUCTION FIX
Custom middleware to bypass CSRF for Twilio webhooks - AGGRESSIVE APPROACH
"""

from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class TwilioCsrfExemptMiddleware(MiddlewareMixin):
    """
    Middleware to exempt Twilio webhook URLs from CSRF verification
    MUST BE PLACED BEFORE django.middleware.csrf.CsrfViewMiddleware in MIDDLEWARE
    """
    
    def process_request(self, request):
        """
        Exempt specific Twilio webhook paths from CSRF - AGGRESSIVE BYPASS
        """
        # Twilio webhook paths that should be exempt from CSRF
        twilio_paths = [
            '/api/calls/voice-response/',
            '/api/calls/call-status/', 
            '/api/calls/fallback/',
            '/api/calls/ultimate-production-webhook/',
            '/api/calls/enhanced-voice-webhook/',
            '/api/calls/pure-hume-webhook/',
            '/api/calls/hume-webhook/',
            '/api/calls/auto-voice-webhook/',
        ]
        
        # Check if this is a Twilio webhook request
        if request.path in twilio_paths:
            logger.info(f"🚨 Twilio webhook detected: {request.path}")
            
            # Get request details for debugging
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            remote_addr = request.META.get('REMOTE_ADDR', '')
            forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
            
            logger.info(f"   User-Agent: {user_agent}")
            logger.info(f"   Remote-Addr: {remote_addr}")
            logger.info(f"   X-Forwarded-For: {forwarded_for}")
            
            # AGGRESSIVE BYPASS - Always exempt Twilio paths regardless of User-Agent
            # This fixes the issue where Twilio User-Agent might be missing or different
            setattr(request, '_dont_enforce_csrf_checks', True)
            logger.info(f"   ✅ CSRF EXEMPTED for Twilio webhook: {request.path}")
            
            # Also check for common Twilio indicators
            is_twilio_request = (
                'Twilio' in user_agent or 
                'TwilioProxy' in user_agent or
                request.path in twilio_paths or
                # Twilio IP ranges (basic check)
                remote_addr.startswith('54.') or
                remote_addr.startswith('52.') or
                # PythonAnywhere might forward differently
                'twilio' in forwarded_for.lower() if forwarded_for else False
            )
            
            if is_twilio_request:
                logger.info(f"   🎯 CONFIRMED Twilio request indicators found")
            else:
                logger.warning(f"   ⚠️ Exempting path but Twilio indicators not found - might be test request")
        
        return None