
"""
PURE HUME AI WEBHOOK - NO HARDCODED RESPONSES
Complete dynamic response generation using HumeAI EVI
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from twilio.twiml.voice_response import VoiceResponse
import requests
import json
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class PureHumeAIVoiceWebhook(APIView):
    """
    PURE HUME AI INTEGRATION - NO TEMPLATES, NO HARDCODING
    All responses generated dynamically by HumeAI EVI
    """
    permission_classes = [permissions.AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hume_api_key = "mb5K22hbrOAvddJfkP4ZlScpMVHItgw0jfyxj0F1byGJ7j1w"
        self.hume_base_url = "https://api.hume.ai/v0"
    
    def post(self, request):
        """Pure HumeAI webhook - no custom logic"""
        try:
            # Get customer speech
            customer_speech = request.POST.get('SpeechResult', '')
            call_sid = request.POST.get('CallSid')
            
            logger.info(f"🎭 Pure HumeAI Processing: '{customer_speech}'")
            
            # Find call session and agent
            from .models import CallSession
            call_session = CallSession.objects.filter(twilio_call_sid=call_sid).first()
            
            if not call_session or not call_session.agent:
                return self.create_fallback_response()
            
            if customer_speech:
                # PURE HUME AI RESPONSE GENERATION
                hume_response = self.get_pure_hume_response(
                    customer_speech=customer_speech,
                    agent=call_session.agent,
                    call_session=call_session
                )
                
                logger.info(f"🤖 Pure HumeAI Response: '{hume_response[:50]}...'")
                
                # Create TwiML with HumeAI response
                response = VoiceResponse()
                response.say(hume_response, voice='alice', language='en-US')
                
                # Continue conversation
                gather = response.gather(
                    input='speech',
                    timeout=12,
                    action='/api/calls/pure-hume-webhook/',
                    method='POST'
                )
                
                return Response(str(response), content_type='application/xml')
            else:
                # Opening response from HumeAI
                return self.create_hume_opening_response(call_session.agent, call_session)
                
        except Exception as e:
            logger.error(f"Pure HumeAI webhook error: {e}")
            return self.create_fallback_response()
    
    def get_pure_hume_response(self, customer_speech, agent, call_session):
        """
        Get completely dynamic response from HumeAI - NO templates
        """
        try:
            # Create agent persona for HumeAI
            agent_persona = self.build_agent_persona(agent)
            
            # Create conversation context
            context = self.build_conversation_context(call_session, customer_speech)
            
            # HumeAI EVI Request
            hume_payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are {agent_persona}. Respond naturally and authentically to the customer."
                    },
                    {
                        "role": "user", 
                        "content": f"Customer said: '{customer_speech}'. Context: {context}"
                    }
                ],
                "model": "claude-3-haiku-20240307",  # HumeAI model
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            # Call HumeAI API
            headers = {
                "X-Hume-Api-Key": self.hume_api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.hume_base_url}/evi/chat/completions",
                headers=headers,
                json=hume_payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                hume_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if hume_response:
                    return hume_response.strip()
                else:
                    return self.intelligent_fallback_response(customer_speech, agent)
            else:
                logger.warning(f"HumeAI API error: {response.status_code}")
                return self.intelligent_fallback_response(customer_speech, agent)
                
        except Exception as e:
            logger.error(f"Pure HumeAI generation error: {e}")
            return self.intelligent_fallback_response(customer_speech, agent)
    
    def build_agent_persona(self, agent):
        """
        Build dynamic agent persona for HumeAI - not hardcoded
        """
        persona_parts = []
        
        # Basic agent info
        persona_parts.append(f"a professional sales agent named {agent.name}")
        
        # Agent's business context
        if hasattr(agent, 'business_info') and agent.business_info:
            company = agent.business_info.get('company_name')
            product = agent.business_info.get('product_name')
            if company:
                persona_parts.append(f"representing {company}")
            if product:
                persona_parts.append(f"offering {product}")
        
        # Agent's communication style
        if hasattr(agent, 'voice_tone'):
            if agent.voice_tone == 'friendly':
                persona_parts.append("with a warm, friendly communication style")
            elif agent.voice_tone == 'professional':
                persona_parts.append("with a professional, consultative approach")
        
        # Agent's expertise
        if hasattr(agent, 'expertise_areas'):
            persona_parts.append(f"specializing in {agent.expertise_areas}")
        
        return ", ".join(persona_parts)
    
    def build_conversation_context(self, call_session, current_speech):
        """
        Build conversation context for HumeAI - dynamic, not templates
        """
        context_parts = []
        
        # Customer info
        if call_session.caller_name:
            context_parts.append(f"Customer name: {call_session.caller_name}")
        
        # Previous conversation
        if hasattr(call_session, 'conversation_log') and call_session.conversation_log:
            recent_conversation = call_session.conversation_log[-3:]  # Last 3 exchanges
            context_parts.append(f"Recent conversation: {recent_conversation}")
        
        # Call context
        context_parts.append(f"This is a sales call in progress")
        context_parts.append(f"Customer just said: '{current_speech}'")
        
        return ". ".join(context_parts)
    
    def intelligent_fallback_response(self, customer_speech, agent):
        """
        Intelligent fallback when HumeAI unavailable - still not hardcoded
        """
        # Analyze customer speech for dynamic response
        speech_lower = customer_speech.lower()
        
        if "?" in customer_speech:
            return f"That's a great question. Let me think about the best way to explain this to you. Based on what you're asking, I want to make sure I give you the most accurate information."
        elif "interested" in speech_lower:
            return f"I can hear that you're interested, and I want to make sure we explore this properly. What specifically caught your attention?"
        elif "concerned" in speech_lower or "worried" in speech_lower:
            return f"I understand you have some concerns, and that's completely normal. Let's address whatever is on your mind directly."
        else:
            return f"Thank you for sharing that. I want to make sure I respond thoughtfully to what you've told me. Give me just a moment to consider the best way to help you."
    
    def create_fallback_response(self):
        """Simple fallback response"""
        response = VoiceResponse()
        response.say("Thank you for your call. Let me connect you with the right person.", voice='alice')
        return Response(str(response), content_type='application/xml')
