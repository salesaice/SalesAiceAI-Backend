"""
LIVE HUME AI TWILIO INTEGRATION
Existing Twilio webhooks ko Hume AI EVI ke saath integrate karta hai
Real-time live calls handle karta hai
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils import timezone
import json
import logging
from twilio.twiml.voice_response import VoiceResponse

from .models import Agent
from .complete_hume_voice_system import CompleteHumeVoiceAgent, process_live_speech
import sys
import os

# Add the directory containing live_hume_integration.py to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from live_hume_integration import LiveHumeAIIntegration
except ImportError:
    print("Warning: live_hume_integration not found in parent directory")
    LiveHumeAIIntegration = None

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def hume_twilio_webhook_handler(request):
    """
    Enhanced Twilio webhook with complete Hume AI EVI integration
    Real-time live calls handle karta hai
    """
    try:
        # Get Twilio webhook data
        call_sid = request.data.get('CallSid') or request.POST.get('CallSid')
        call_status = request.data.get('CallStatus') or request.POST.get('CallStatus')
        from_number = request.data.get('From') or request.POST.get('From')
        to_number = request.data.get('To') or request.POST.get('To')
        speech_result = request.data.get('SpeechResult') or request.POST.get('SpeechResult', '')
        
        logger.info(f"Hume Twilio webhook: CallSid={call_sid}, Status={call_status}, Speech={speech_result[:50] if speech_result else 'None'}")
        
        # Find appropriate agent for this call
        agent = find_agent_for_call(to_number, from_number)
        
        if not agent:
            return create_no_agent_response()
        
        # Handle different call statuses
        if call_status == 'ringing':
            return handle_incoming_call(agent, call_sid, from_number)
        elif call_status in ['in-progress', 'initiated'] and speech_result:
            return handle_customer_speech(agent, speech_result, call_sid)
        elif call_status == 'completed':
            return handle_call_completion(agent, call_sid)
        else:
            # Default response for other statuses
            return create_default_response(agent)
            
    except Exception as e:
        logger.error(f"Hume Twilio webhook error: {str(e)}")
        return HttpResponse(str(create_error_response()), content_type='text/xml')

def find_agent_for_call(to_number: str, from_number: str):
    """
    Call ke liye appropriate agent find karta hai
    """
    try:
        # Priority 1: Active outbound agents
        agent = Agent.objects.filter(
            status='active',
            agent_type='outbound'
        ).first()
        
        if not agent:
            # Priority 2: Any active agent
            agent = Agent.objects.filter(status='active').first()
        
        return agent
    except Exception as e:
        logger.error(f"Agent finding error: {str(e)}")
        return None

def handle_incoming_call(agent: Agent, call_sid: str, customer_phone: str):
    """
    Incoming call handle karta hai with Hume AI
    """
    try:
        # Start Hume AI voice session
        voice_agent = CompleteHumeVoiceAgent(str(agent.id))
        session_result = voice_agent.start_live_call(customer_phone, {
            "call_sid": call_sid,
            "call_type": "inbound"
        })
        
        # Create Twilio response
        response = VoiceResponse()
        
        if session_result["success"]:
            # Opening message from agent
            opening_message = f"Hello! This is {agent.name}. Thank you for calling. How can I help you today?"
            
            response.say(opening_message, voice='alice', language='en-US')
            response.gather(
                input='speech',
                timeout=10,
                action=f'/agents/webhooks/hume-twilio/',
                method='POST',
                speech_timeout='auto'
            )
            
            logger.info(f"Incoming call handled with Hume AI: {call_sid}")
        else:
            # Fallback response
            response.say("Hello! Thank you for calling. Please hold on while I connect you.", voice='alice')
            response.gather(input='speech', timeout=10, action='/agents/webhooks/hume-twilio/', method='POST')
        
        return HttpResponse(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Incoming call handling error: {str(e)}")
        return HttpResponse(str(create_error_response()), content_type='text/xml')

def handle_customer_speech(agent: Agent, customer_speech: str, call_sid: str):
    """
    Customer speech ko Hume AI ke saath process karta hai
    """
    try:
        # Process speech with Hume AI EVI
        result = process_live_speech(str(agent.id), customer_speech, call_sid)
        
        if result["success"]:
            # Return Hume AI generated TwiML response
            return HttpResponse(result["twiml_response"], content_type='text/xml')
        else:
            # Create fallback response
            response = VoiceResponse()
            fallback_message = result.get("fallback_response", "I understand. Let me help you with that.")
            
            response.say(fallback_message, voice='alice', language='en-US')
            response.gather(
                input='speech',
                timeout=10,
                action='/agents/webhooks/hume-twilio/',
                method='POST'
            )
            
            return HttpResponse(str(response), content_type='text/xml')
            
    except Exception as e:
        logger.error(f"Customer speech processing error: {str(e)}")
        return HttpResponse(str(create_error_response()), content_type='text/xml')

def handle_call_completion(agent: Agent, call_sid: str):
    """
    Call completion handle karta hai aur learning apply karta hai
    """
    try:
        from .complete_hume_voice_system import complete_call_analysis
        
        # Complete call analysis and learning
        analysis_result = complete_call_analysis(str(agent.id))
        
        logger.info(f"Call completed and analyzed: {call_sid} - {analysis_result.get('message', 'Analysis completed')}")
        
        # Return empty response for completed calls
        response = VoiceResponse()
        return HttpResponse(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Call completion handling error: {str(e)}")
        return HttpResponse("", content_type='text/xml')

def create_no_agent_response():
    """
    Agent nahi milne par response
    """
    response = VoiceResponse()
    response.say(
        "Thank you for calling. All our agents are currently busy. Please try again later.",
        voice='alice',
        language='en-US'
    )
    response.hangup()
    
    return HttpResponse(str(response), content_type='text/xml')

def create_default_response(agent: Agent):
    """
    Default response for agent
    """
    response = VoiceResponse()
    response.say(
        f"Hello, this is {agent.name}. How can I assist you today?",
        voice='alice',
        language='en-US'
    )
    response.gather(
        input='speech',
        timeout=10,
        action='/agents/webhooks/hume-twilio/',
        method='POST'
    )
    
    return HttpResponse(str(response), content_type='text/xml')

def create_error_response():
    """
    Error response
    """
    response = VoiceResponse()
    response.say(
        "I apologize, we're experiencing technical difficulties. Please try your call again.",
        voice='alice',
        language='en-US'
    )
    response.hangup()
    
    return response

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def start_hume_ai_call(request):
    """
    Programmatically Hume AI call start karta hai
    """
    try:
        agent_id = request.data.get('agent_id')
        customer_phone = request.data.get('customer_phone')
        call_context = request.data.get('context', {})
        
        if not agent_id or not customer_phone:
            return Response({
                'error': 'Missing required fields',
                'required': ['agent_id', 'customer_phone']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check agent exists
        try:
            agent = Agent.objects.get(id=agent_id)
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Start Hume AI call
        from .complete_hume_voice_system import start_hume_voice_call
        
        call_result = start_hume_voice_call(agent_id, customer_phone, call_context)
        
        if call_result["success"]:
            return Response({
                'success': True,
                'message': 'Hume AI call started successfully',
                'agent_name': agent.name,
                'hume_session_id': call_result.get('session_id'),
                'call_data': call_result
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': call_result.get('error'),
                'fallback': call_result.get('fallback')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Start Hume AI call error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST']) 
@permission_classes([AllowAny])
def test_hume_integration(request):
    """
    Hume AI integration test karta hai
    """
    try:
        agent_id = request.data.get('agent_id')
        test_message = request.data.get('test_message', 'Hello, this is a test message')
        
        if not agent_id:
            return Response({
                'error': 'Missing agent_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test Hume AI integration
        if LiveHumeAIIntegration:
            hume_integration = LiveHumeAIIntegration()
            test_result = hume_integration.test_evi_integration()
            
            if test_result:
                # Test with specific agent
                result = process_live_speech(agent_id, test_message)
                
                return Response({
                    'success': True,
                    'message': 'Hume AI integration working correctly',
                    'test_result': result,
                    'hume_evi_status': 'operational'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Hume AI EVI configuration issue',
                    'recommendation': 'Check Hume AI dashboard and API key'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'success': False,
                'error': 'Hume AI integration not available',
                'recommendation': 'Check live_hume_integration.py file'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Hume integration test error: {str(e)}")
        return Response({
            'error': 'Test failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)