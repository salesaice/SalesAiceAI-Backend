"""
TTS Response Endpoint for Twilio
"""

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.twiml.voice_response import VoiceResponse
import urllib.parse
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def tts_response(request):
    """Generate TTS response for AI text"""
    try:
        # Get text and voice from URL parameters
        text = request.GET.get('text', 'Sorry, I did not receive the message properly.')
        voice = request.GET.get('voice', 'Polly.Joanna')
        
        # Decode URL encoded text
        text = urllib.parse.unquote(text)
        
        logger.info(f"🔊 TTS Endpoint called: '{text[:50]}...' with voice: {voice}")
        
        # Create TwiML response
        response = VoiceResponse()
        
        # Add the AI's text as speech
        response.say(text, voice=voice)
        
        # Continue the stream after TTS
        response.pause(length=1)
        
        logger.info(f"✅ TTS TwiML generated successfully")
        
        return HttpResponse(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"❌ TTS endpoint error: {e}")
        
        # Fallback response
        response = VoiceResponse()
        response.say("Sorry, there was an error processing the response.", voice='Polly.Joanna')
        return HttpResponse(str(response), content_type='text/xml')