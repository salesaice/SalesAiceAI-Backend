"""
HUME AI WEBHOOK CONFIGURATION FOR REAL-TIME CONVERSATION
Complete HumeAI EVI integration for dynamic customer conversations
Customer ko listen karna aur real-time mein response dena
"""

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from twilio.twiml.voice_response import VoiceResponse
import json
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
@api_view(['POST'])
@permission_classes([AllowAny])
def hume_ai_webhook(request):
    """
    HumeAI webhook for real-time conversation handling
    Customer ki har message ko process karta hai aur dynamic response deta hai
    """
    try:
        # Parse HumeAI webhook data
        webhook_data = json.loads(request.body) if request.body else {}
        
        logger.info(f"🎭 HumeAI Webhook received: {webhook_data}")
        
        # Extract conversation data
        event_type = webhook_data.get('type', 'message')
        session_id = webhook_data.get('session_id')
        user_message = webhook_data.get('message', {}).get('content', '')
        emotions = webhook_data.get('emotions', [])
        
        # Get call session from HumeAI session
        from .models import CallSession
        call_session = None
        if session_id:
            # Find call session by HumeAI session ID
            call_sessions = CallSession.objects.filter(
                notes__icontains=session_id
            ).first()
            if call_sessions:
                call_session = call_sessions
        
        # Process based on event type
        if event_type == 'user_message':
            # Customer ne kuch bola hai - process karo
            response_data = process_customer_message(
                user_message=user_message,
                emotions=emotions,
                call_session=call_session,
                session_id=session_id
            )
            
            return JsonResponse(response_data)
            
        elif event_type == 'conversation_end':
            # Conversation khatam ho gayi
            if call_session:
                call_session.status = 'completed'
                call_session.save()
            
            return JsonResponse({'status': 'conversation_ended'})
            
        else:
            # Other events
            return JsonResponse({'status': 'received', 'type': event_type})
    
    except Exception as e:
        logger.error(f"HumeAI webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def process_customer_message(user_message, emotions, call_session, session_id):
    """
    Customer ke message ko process karta hai aur intelligent response banata hai
    """
    try:
        # Analyze customer message
        message_analysis = analyze_customer_intent(user_message, emotions)
        
        # Generate dynamic response based on analysis
        agent_response = generate_agent_response(
            customer_message=user_message,
            intent=message_analysis['intent'],
            sentiment=message_analysis['sentiment'],
            call_session=call_session
        )
        
        # Log conversation for analytics
        if call_session:
            conversation_log = {
                'timestamp': str(timezone.now()),
                'customer_message': user_message,
                'emotions': emotions,
                'intent': message_analysis['intent'],
                'sentiment': message_analysis['sentiment'],
                'agent_response': agent_response
            }
            
            # Update call session notes
            current_notes = call_session.notes or ""
            conversation_history = f"{current_notes}\n--- HumeAI Conversation ---\n{json.dumps(conversation_log)}"
            call_session.notes = conversation_history
            call_session.save()
        
        # Return response for HumeAI
        return {
            'type': 'agent_response',
            'message': {
                'content': agent_response,
                'type': 'text'
            },
            'session_id': session_id,
            'continue_conversation': True
        }
        
    except Exception as e:
        logger.error(f"Message processing error: {str(e)}")
        return {
            'type': 'agent_response',
            'message': {
                'content': "I understand. Could you tell me more about that?",
                'type': 'text'
            },
            'session_id': session_id,
            'continue_conversation': True
        }


def analyze_customer_intent(message, emotions):
    """
    Customer ke message ka intent aur sentiment analyze karta hai
    """
    message_lower = message.lower()
    
    # Intent detection
    intent = 'general'
    if any(word in message_lower for word in ['buy', 'purchase', 'interested', 'want', 'need']):
        intent = 'purchase_interest'
    elif any(word in message_lower for word in ['price', 'cost', 'expensive', 'cheap', 'budget']):
        intent = 'pricing_inquiry'
    elif any(word in message_lower for word in ['no', 'not interested', 'busy', 'later']):
        intent = 'objection'
    elif any(word in message_lower for word in ['tell me more', 'explain', 'how', 'what']):
        intent = 'information_request'
    elif any(word in message_lower for word in ['yes', 'okay', 'sure', 'sounds good']):
        intent = 'positive_response'
    
    # Sentiment analysis from emotions
    sentiment = 'neutral'
    if emotions:
        # Get dominant emotion
        dominant_emotion = max(emotions, key=lambda x: x.get('confidence', 0))
        emotion_name = dominant_emotion.get('name', 'neutral')
        
        if emotion_name in ['joy', 'satisfaction', 'excitement']:
            sentiment = 'positive'
        elif emotion_name in ['anger', 'frustration', 'annoyance']:
            sentiment = 'negative'
        elif emotion_name in ['confusion', 'surprise']:
            sentiment = 'uncertain'
    
    return {
        'intent': intent,
        'sentiment': sentiment,
        'confidence': 0.8
    }


def generate_agent_response(customer_message, intent, sentiment, call_session):
    """
    Customer ke intent aur sentiment ke base par dynamic response generate karta hai
    """
    try:
        # Get agent from call session
        agent = call_session.agent if call_session else None
        agent_name = agent.name if agent else "Assistant"
        
        # Generate response based on intent
        if intent == 'purchase_interest':
            if sentiment == 'positive':
                response = f"That's wonderful to hear! I'm excited that you're interested. Let me share some specific details about how {agent_name if agent else 'our solution'} can help you. What aspect interests you most?"
            else:
                response = f"I appreciate your interest. Let me explain how this could work for your specific situation. What's most important to you right now?"
                
        elif intent == 'pricing_inquiry':
            response = f"Great question about pricing! The investment varies based on your specific needs. Before I share the details, help me understand - what value would this need to provide to make it worthwhile for you?"
            
        elif intent == 'objection':
            if sentiment == 'negative':
                response = f"I completely understand, and I appreciate you being honest with me. Many of my best customers felt the same way initially. What specifically concerns you most?"
            else:
                response = f"No problem at all! I respect your time. Just curious - what would need to change for this to be worth a conversation?"
                
        elif intent == 'information_request':
            response = f"Absolutely! I'd love to explain that. Let me break it down in a way that makes sense for your situation. What specific aspect would be most helpful to understand first?"
            
        elif intent == 'positive_response':
            response = f"Perfect! I love your enthusiasm. Let me make sure I give you exactly what you need. What's the next step that would be most valuable for you?"
            
        else:  # general
            if sentiment == 'positive':
                response = f"I appreciate you sharing that with me. Based on what you're telling me, I think you'd really benefit from what I have to offer. Would you like me to explain how this could help you specifically?"
            elif sentiment == 'negative':
                response = f"I hear you, and I want to make sure I'm being helpful, not pushy. Help me understand - what would make this conversation valuable for you?"
            else:
                response = f"Thank you for that. I want to make sure I'm addressing what matters most to you. Could you help me understand your biggest priority right now?"
        
        return response
        
    except Exception as e:
        logger.error(f"Response generation error: {str(e)}")
        return "I understand. Could you tell me more about what's important to you?"


@method_decorator(csrf_exempt, name='dispatch')
@api_view(['POST'])
@permission_classes([AllowAny])
def hume_ai_status_callback(request):
    """
    HumeAI session status updates
    Session ki status changes track karta hai
    """
    try:
        status_data = json.loads(request.body) if request.body else {}
        
        session_id = status_data.get('session_id')
        status = status_data.get('status')
        
        logger.info(f"🎭 HumeAI Status Update - Session: {session_id}, Status: {status}")
        
        # Update call session status if needed
        from .models import CallSession
        if session_id:
            call_sessions = CallSession.objects.filter(
                notes__icontains=session_id
            ).first()
            
            if call_sessions:
                if status == 'connected':
                    call_sessions.status = 'answered'
                elif status == 'ended':
                    call_sessions.status = 'completed'
                elif status == 'failed':
                    call_sessions.status = 'failed'
                
                call_sessions.save()
        
        return JsonResponse({'status': 'received'})
        
    except Exception as e:
        logger.error(f"HumeAI status callback error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def hume_ai_config_test(request):
    """
    HumeAI configuration test endpoint
    Configuration test karne ke liye
    """
    try:
        config_data = {
            'hume_ai_config': {
                'api_key': 'mb5K22hbrOAvddJfkP4ZlScpMVHItgw0jfyxj0F1byGJ7j1w',
                'config_id': '13624648-658a-49b1-81cb-a0f2e2b05de5',
                'webhook_url': request.build_absolute_uri('/api/calls/hume-webhook/'),
                'status_callback_url': request.build_absolute_uri('/api/calls/hume-status/'),
                'features': {
                    'real_time_emotion': True,
                    'dynamic_responses': True,
                    'conversation_memory': True,
                    'intent_recognition': True
                }
            },
            'twilio_integration': {
                'webhook_url': request.build_absolute_uri('/api/calls/auto-voice-webhook/'),
                'status_callback': request.build_absolute_uri('/api/calls/status-callback/'),
                'connect_to_hume': True
            },
            'system_status': 'ready',
            'timestamp': str(timezone.now())
        }
        
        return JsonResponse(config_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)