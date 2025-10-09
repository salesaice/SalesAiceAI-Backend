from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from django.conf import settings
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TwilioCallService:
    """
    Twilio integration for actual phone calls
    Real phone calls ke liye Twilio service
    """
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured, using mock service")
    
    def initiate_call(self, to: str, agent_config: Dict[str, Any], call_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initiate outbound call
        Outbound call start karta hai
        """
        if not self.client:
            return self._mock_call_response(to, 'outbound')
        
        try:
            # Create TwiML for AI-powered call
            twiml_url = self._generate_twiml_url(agent_config, call_context)
            
            call = self.client.calls.create(
                to=to,
                from_=self.phone_number,
                url=twiml_url,
                method='POST',
                record=True,  # Record conversation for learning
                timeout=30,
                machine_detection='Enable',
                machine_detection_timeout=10
            )
            
            return {
                'call_sid': call.sid,
                'status': call.status,
                'direction': call.direction,
                'to': call.to,
                'from': call.from_formatted,
                'initiated_at': call.date_created.isoformat() if call.date_created else None
            }
            
        except Exception as e:
            logger.error(f"Twilio call initiation failed: {str(e)}")
            return {
                'error': str(e),
                'call_sid': None,
                'status': 'failed'
            }
    
    def handle_inbound_call(self, call_sid: str, from_number: str, agent_config: Dict[str, Any]) -> VoiceResponse:
        """
        Handle inbound call with AI agent
        Inbound call ko AI agent handle karta hai
        """
        response = VoiceResponse()
        
        # Start with greeting
        greeting = self._generate_greeting(agent_config)
        response.say(greeting, voice='alice', language='en-US')
        
        # Gather customer response
        gather = response.gather(
            input='speech',
            timeout=10,
            action=f'/api/calls/twilio/process-speech/{call_sid}/',
            method='POST',
            speech_timeout='auto'
        )
        
        gather.say("Please tell me how I can help you today.", voice='alice')
        
        # If no input, try again
        response.say("I didn't hear anything. Please tell me how I can assist you.")
        response.redirect(f'/api/calls/twilio/handle-silence/{call_sid}/')
        
        return response
    
    def process_speech_input(self, call_sid: str, speech_result: str, agent_config: Dict[str, Any]) -> VoiceResponse:
        """
        Process customer speech and generate AI response
        Customer ki speech process kar ke AI response generate karta hai
        """
        response = VoiceResponse()
        
        # Here you would integrate with HomeAI to process speech
        # For now, simple rule-based responses
        
        if 'busy' in speech_result.lower():
            response.say("I understand you're busy. Would you like me to call you back at a better time?", voice='alice')
            
            gather = response.gather(
                input='speech',
                timeout=5,
                action=f'/api/calls/twilio/handle-callback-request/{call_sid}/',
                method='POST'
            )
            gather.say("Please say yes or no.")
            
        elif 'not interested' in speech_result.lower():
            response.say("I appreciate your honesty. May I ask what your main concern is?", voice='alice')
            
            gather = response.gather(
                input='speech',
                timeout=10,
                action=f'/api/calls/twilio/handle-objection/{call_sid}/',
                method='POST'
            )
            
        elif 'interested' in speech_result.lower():
            response.say("That's wonderful! Let me share how we can help you specifically.", voice='alice')
            response.say("What's your biggest challenge right now?", voice='alice')
            
            gather = response.gather(
                input='speech',
                timeout=15,
                action=f'/api/calls/twilio/continue-conversation/{call_sid}/',
                method='POST'
            )
            
        else:
            # Generic response
            response.say("Thank you for sharing that with me.", voice='alice')
            response.say("Let me ask you - what would be the ideal solution for your situation?", voice='alice')
            
            gather = response.gather(
                input='speech',
                timeout=15,
                action=f'/api/calls/twilio/continue-conversation/{call_sid}/',
                method='POST'
            )
        
        return response
    
    def handle_callback_request(self, call_sid: str, response_text: str) -> VoiceResponse:
        """
        Handle callback scheduling
        Callback scheduling handle karta hai
        """
        response = VoiceResponse()
        
        if 'yes' in response_text.lower():
            response.say("Perfect! What time would work best for you? Morning, afternoon, or evening?", voice='alice')
            
            gather = response.gather(
                input='speech',
                timeout=10,
                action=f'/api/calls/twilio/schedule-callback/{call_sid}/',
                method='POST'
            )
            
        else:
            response.say("No problem. Is there anything quick I can help you with right now?", voice='alice')
            
            gather = response.gather(
                input='speech',
                timeout=10,
                action=f'/api/calls/twilio/final-attempt/{call_sid}/',
                method='POST'
            )
        
        return response
    
    def schedule_callback_time(self, call_sid: str, time_preference: str) -> VoiceResponse:
        """
        Schedule specific callback time
        Specific callback time schedule karta hai
        """
        response = VoiceResponse()
        
        # Parse time preference and schedule
        if 'morning' in time_preference.lower():
            callback_time = "tomorrow morning between 9 and 12"
        elif 'afternoon' in time_preference.lower():
            callback_time = "tomorrow afternoon between 1 and 5"
        elif 'evening' in time_preference.lower():
            callback_time = "tomorrow evening between 5 and 7"
        else:
            callback_time = "tomorrow at a convenient time"
        
        response.say(f"Excellent! I'll call you back {callback_time}.", voice='alice')
        response.say("Thank you for your time today. Have a great day!", voice='alice')
        
        # Here you would create the scheduled callback in database
        
        response.hangup()
        return response
    
    def handle_objection(self, call_sid: str, objection_text: str) -> VoiceResponse:
        """
        Handle customer objections
        Customer ke objections handle karta hai
        """
        response = VoiceResponse()
        
        # Simple objection handling - in real app, use HomeAI
        if 'price' in objection_text.lower() or 'cost' in objection_text.lower():
            response.say("I understand cost is important. Let me share how our clients typically see a return on their investment.", voice='alice')
            response.say("What specific results would make this worthwhile for you?", voice='alice')
            
        elif 'time' in objection_text.lower():
            response.say("I appreciate that you're busy. That's exactly why our solution is designed to save you time.", voice='alice')
            response.say("What's taking up most of your time right now?", voice='alice')
            
        else:
            response.say("I completely understand your concern. Many clients had similar thoughts initially.", voice='alice')
            response.say("What would need to change for this to be a perfect fit for you?", voice='alice')
        
        gather = response.gather(
            input='speech',
            timeout=15,
            action=f'/api/calls/twilio/continue-conversation/{call_sid}/',
            method='POST'
        )
        
        return response
    
    def end_call_positively(self, call_sid: str, outcome: str) -> VoiceResponse:
        """
        End call with positive message
        Call ko positive note pe end karta hai
        """
        response = VoiceResponse()
        
        if outcome == 'converted':
            response.say("Fantastic! Thank you so much for your business. You'll receive confirmation details shortly.", voice='alice')
            response.say("We're excited to work with you!", voice='alice')
        elif outcome == 'callback_scheduled':
            response.say("Perfect! I have you scheduled for a callback. Looking forward to speaking with you again.", voice='alice')
        elif outcome == 'interested':
            response.say("Thank you for your time today. I'll send you some additional information.", voice='alice')
            response.say("Feel free to call us if you have any questions!", voice='alice')
        else:
            response.say("Thank you for your time today. Have a wonderful day!", voice='alice')
        
        response.hangup()
        return response
    
    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """
        Get call status and details
        Call ka status aur details get karta hai
        """
        if not self.client:
            return self._mock_call_status(call_sid)
        
        try:
            call = self.client.calls(call_sid).fetch()
            
            return {
                'call_sid': call.sid,
                'status': call.status,
                'direction': call.direction,
                'duration': call.duration,
                'start_time': call.start_time.isoformat() if call.start_time else None,
                'end_time': call.end_time.isoformat() if call.end_time else None,
                'price': call.price,
                'answered_by': call.answered_by
            }
            
        except Exception as e:
            logger.error(f"Failed to get call status: {str(e)}")
            return {
                'error': str(e),
                'call_sid': call_sid,
                'status': 'unknown'
            }
    
    def get_call_recording(self, call_sid: str) -> Optional[str]:
        """
        Get call recording URL
        Call recording ka URL get karta hai
        """
        if not self.client:
            return f"https://demo-recordings.com/{call_sid}.mp3"
        
        try:
            recordings = self.client.recordings.list(call_sid=call_sid)
            
            if recordings:
                recording = recordings[0]
                return f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get call recording: {str(e)}")
            return None
    
    def _generate_greeting(self, agent_config: Dict[str, Any]) -> str:
        """Generate personalized greeting"""
        agent_name = agent_config.get('name', 'Sales Assistant')
        business_info = agent_config.get('conversation_memory', {}).get('business_info', {})
        company_name = business_info.get('company_name', 'our company')
        
        return f"Hello! This is {agent_name} from {company_name}. How are you doing today?"
    
    def _generate_twiml_url(self, agent_config: Dict[str, Any], call_context: Dict[str, Any]) -> str:
        """Generate TwiML webhook URL"""
        # This would be your server's webhook URL
        base_url = getattr(settings, 'BASE_URL', 'https://yourdomain.com')
        agent_id = agent_config.get('id', 'default')
        return f"{base_url}/api/calls/twilio/handle-call/{agent_id}/"
    
    def _mock_call_response(self, to: str, direction: str) -> Dict[str, Any]:
        """Mock call response for development"""
        return {
            'call_sid': f"mock_call_{to}_{direction}",
            'status': 'queued',
            'direction': direction,
            'to': to,
            'from': self.phone_number or '+1234567890',
            'initiated_at': '2025-10-01T12:00:00Z'
        }
    
    def _mock_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Mock call status for development"""
        return {
            'call_sid': call_sid,
            'status': 'completed',
            'direction': 'outbound',
            'duration': 180,  # 3 minutes
            'start_time': '2025-10-01T12:00:00Z',
            'end_time': '2025-10-01T12:03:00Z',
            'price': '-0.015',
            'answered_by': 'human'
        }
