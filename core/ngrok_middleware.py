"""
Middleware to bypass ngrok browser warning for Twilio webhooks
"""

class NgrokBypassMiddleware:
    """Add ngrok-skip-browser-warning header to all requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # This header tells ngrok to skip the browser warning page
        request.META['HTTP_NGROK_SKIP_BROWSER_WARNING'] = 'true'
        
        response = self.get_response(request)
        return response
