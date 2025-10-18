"""
Service layer for HumeAI + Twilio Integration
Handles all business logic and external API calls
"""

import os
import json
import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

# Try to import decouple for .env loading
try:
    from decouple import config
    def get_env(key, default=None):
        return config(key, default=default or os.getenv(key))
except ImportError:
    def get_env(key, default=None):
        return os.getenv(key, default)

from .models import (
    HumeAgent, TwilioCall, ConversationLog,
    CallAnalytics, WebhookLog
)

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for Twilio API operations"""
    
    def __init__(self):
        self.account_sid = get_env('TWILIO_ACCOUNT_SID')
        self.auth_token = get_env('TWILIO_AUTH_TOKEN')
        self.phone_number = get_env('TWILIO_PHONE_NUMBER')
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            raise ValueError("Twilio credentials not configured properly")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def initiate_call(
        self, 
        to_number: str, 
        agent: HumeAgent,
        callback_url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call
        
        Args:
            to_number: Customer's phone number
            agent: HumeAgent instance to use
            callback_url: URL for Twilio webhooks
            **kwargs: Additional parameters
        
        Returns:
            Dict with call details
        """
        try:
            # Create TwiML for the call
            twiml_url = callback_url + "/twiml"
            
            # Make the call
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=twiml_url,
                status_callback=callback_url + "/status",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                record=True,
                recording_status_callback=callback_url + "/recording"
            )
            
            logger.info(f"Call initiated: {call.sid} to {to_number}")
            
            return {
                'success': True,
                'call_sid': call.sid,
                'status': call.status,
                'to': to_number,
                'from': self.phone_number
            }
        
        except Exception as e:
            logger.error(f"Failed to initiate call: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_twiml_response(
        self, 
        agent: HumeAgent,
        websocket_url: str
    ) -> str:
        """
        Generate TwiML response for connecting call to WebSocket
        
        Args:
            agent: HumeAgent instance
            websocket_url: WebSocket URL for streaming
        
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        # Play greeting (optional)
        if agent.greeting_message:
            response.say(agent.greeting_message, voice='Polly.Joanna')
        
        # Connect to WebSocket for real-time streaming
        connect = Connect()
        stream = Stream(url=websocket_url)
        connect.append(stream)
        response.append(connect)
        
        return str(response)
    
    def get_call_details(self, call_sid: str) -> Dict[str, Any]:
        """Get call details from Twilio"""
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'sid': call.sid,
                'status': call.status,
                'duration': call.duration,
                'from': call.from_,
                'to': call.to,
                'price': call.price,
                'direction': call.direction
            }
        except Exception as e:
            logger.error(f"Failed to fetch call details: {str(e)}")
            return {}
    
    def terminate_call(self, call_sid: str) -> bool:
        """Terminate an active call"""
        try:
            self.client.calls(call_sid).update(status='completed')
            logger.info(f"Call terminated: {call_sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to terminate call: {str(e)}")
            return False


class HumeAIService:
    """Service for HumeAI API operations"""
    
    def __init__(self):
        self.api_key = get_env('HUME_AI_API_KEY') or get_env('HUME_API_KEY')
        self.secret_key = get_env('HUME_SECRET_KEY') or get_env('HUME_AI_SECRET_KEY')
        self.config_id = get_env('HUME_CONFIG_ID')
        
        if not self.api_key:
            raise ValueError("HumeAI credentials not configured properly")
    
    async def create_session(self, agent: HumeAgent) -> Dict[str, Any]:
        """
        Create a new HumeAI session
        
        Args:
            agent: HumeAgent instance
        
        Returns:
            Dict with session details
        """
        try:
            # Note: This is a placeholder. Actual implementation depends on HumeAI SDK
            # You'll need to install and import HumeAI SDK
            
            session_config = {
                'config_id': agent.hume_config_id or self.config_id,
                'api_key': self.api_key,
                'system_prompt': agent.system_prompt,
                'voice': agent.voice_name,
                'language': agent.language
            }
            
            logger.info(f"HumeAI session created for agent: {agent.name}")
            
            return {
                'success': True,
                'session_id': 'hume_session_' + str(agent.id),
                'config': session_config
            }
        
        except Exception as e:
            logger.error(f"Failed to create HumeAI session: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def send_message(
        self, 
        session_id: str, 
        message: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send message to HumeAI and get response"""
        try:
            # Placeholder for actual HumeAI API call
            logger.info(f"Sending message to HumeAI session: {session_id}")
            
            return {
                'success': True,
                'response': "AI response placeholder",
                'emotion_scores': {},
                'sentiment': 'neutral'
            }
        
        except Exception as e:
            logger.error(f"Failed to send message to HumeAI: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_emotion(self, audio_data: bytes) -> Dict[str, Any]:
        """Analyze emotion from audio data"""
        try:
            # Placeholder for emotion analysis
            return {
                'emotions': {
                    'happiness': 0.7,
                    'sadness': 0.1,
                    'anger': 0.05,
                    'neutral': 0.15
                },
                'dominant_emotion': 'happiness',
                'confidence': 0.85
            }
        except Exception as e:
            logger.error(f"Emotion analysis failed: {str(e)}")
            return {}


class ConversationService:
    """Service for managing conversations"""
    
    @staticmethod
    def log_message(
        call: TwilioCall,
        role: str,
        message: str,
        emotion_scores: Optional[Dict] = None,
        sentiment: Optional[str] = None,
        confidence: float = 0.0
    ) -> ConversationLog:
        """Log a conversation message"""
        return ConversationLog.objects.create(
            call=call,
            role=role,
            message=message,
            emotion_scores=emotion_scores,
            sentiment=sentiment,
            confidence=confidence
        )
    
    @staticmethod
    def get_conversation_history(call: TwilioCall) -> List[ConversationLog]:
        """Get all messages from a conversation"""
        return list(call.conversation_logs.all())
    
    @staticmethod
    def generate_conversation_summary(call: TwilioCall) -> str:
        """Generate a summary of the conversation"""
        logs = call.conversation_logs.all()
        
        if not logs.exists():
            return "No conversation data available"
        
        total_messages = logs.count()
        user_messages = logs.filter(role='user').count()
        agent_messages = logs.filter(role='assistant').count()
        
        summary = f"Conversation with {total_messages} messages "
        summary += f"({user_messages} from customer, {agent_messages} from AI agent)"
        
        return summary


class AnalyticsService:
    """Service for call analytics"""
    
    @staticmethod
    def calculate_analytics(call: TwilioCall) -> CallAnalytics:
        """Calculate analytics for a call"""
        logs = call.conversation_logs.all()
        
        total_messages = logs.count()
        user_messages = logs.filter(role='user').count()
        agent_messages = logs.filter(role='assistant').count()
        
        # Calculate sentiment scores
        sentiments = logs.exclude(sentiment__isnull=True).values_list('sentiment', flat=True)
        positive_count = sum(1 for s in sentiments if s == 'positive')
        negative_count = sum(1 for s in sentiments if s == 'negative')
        neutral_count = sum(1 for s in sentiments if s == 'neutral')
        
        total_sentiments = len(sentiments)
        positive_score = (positive_count / total_sentiments * 100) if total_sentiments > 0 else 0
        negative_score = (negative_count / total_sentiments * 100) if total_sentiments > 0 else 0
        neutral_score = (neutral_count / total_sentiments * 100) if total_sentiments > 0 else 0
        
        # Determine overall sentiment
        if positive_score > negative_score and positive_score > neutral_score:
            overall_sentiment = 'positive'
        elif negative_score > positive_score and negative_score > neutral_score:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'neutral'
        
        # Generate summary
        summary = ConversationService.generate_conversation_summary(call)
        
        # Create or update analytics
        analytics, created = CallAnalytics.objects.update_or_create(
            call=call,
            defaults={
                'total_messages': total_messages,
                'user_messages': user_messages,
                'agent_messages': agent_messages,
                'overall_sentiment': overall_sentiment,
                'positive_score': positive_score,
                'negative_score': negative_score,
                'neutral_score': neutral_score,
                'summary': summary
            }
        )
        
        return analytics
    
    @staticmethod
    def get_agent_performance(agent: HumeAgent, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for an agent"""
        start_date = timezone.now() - timedelta(days=days)
        calls = TwilioCall.objects.filter(
            agent=agent,
            created_at__gte=start_date
        )
        
        total_calls = calls.count()
        completed_calls = calls.filter(status='completed').count()
        total_duration = sum(call.duration for call in calls)
        
        return {
            'agent_name': agent.name,
            'total_calls': total_calls,
            'completed_calls': completed_calls,
            'completion_rate': (completed_calls / total_calls * 100) if total_calls > 0 else 0,
            'total_duration': total_duration,
            'avg_duration': (total_duration / completed_calls) if completed_calls > 0 else 0,
            'period_days': days
        }


class WebhookService:
    """Service for handling webhooks"""
    
    @staticmethod
    def log_webhook(
        source: str,
        event_type: str,
        payload: Dict,
        headers: Optional[Dict] = None,
        call: Optional[TwilioCall] = None
    ) -> WebhookLog:
        """Log a webhook event"""
        return WebhookLog.objects.create(
            source=source,
            event_type=event_type,
            payload=payload,
            headers=headers,
            call=call
        )
    
    @staticmethod
    def process_twilio_webhook(payload: Dict) -> Dict[str, Any]:
        """Process Twilio webhook"""
        try:
            call_sid = payload.get('CallSid')
            call_status = payload.get('CallStatus')
            
            if not call_sid:
                return {'success': False, 'error': 'Missing CallSid'}
            
            # Update call status
            call = TwilioCall.objects.filter(call_sid=call_sid).first()
            if call:
                call.status = call_status
                call.duration = int(payload.get('CallDuration', 0))
                
                if call_status == 'in-progress' and not call.started_at:
                    call.started_at = timezone.now()
                elif call_status in ['completed', 'failed', 'busy', 'no-answer']:
                    call.ended_at = timezone.now()
                
                call.save()
                
                # Calculate analytics if call completed
                if call_status == 'completed':
                    AnalyticsService.calculate_analytics(call)
            
            return {'success': True, 'call_sid': call_sid}
        
        except Exception as e:
            logger.error(f"Error processing Twilio webhook: {str(e)}")
            return {'success': False, 'error': str(e)}
