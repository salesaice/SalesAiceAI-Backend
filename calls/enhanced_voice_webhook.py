"""
ENHANCED AUTO VOICE WEBHOOK WITH REAL-TIME CUSTOMER LISTENING
Complete customer conversation handling with HumeAI integration
Customer ki har baat sun kar intelligent response deta hai
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.utils import timezone
from twilio.twiml.voice_response import VoiceResponse, Gather
import json
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class EnhancedAutoVoiceWebhookView(APIView):
    """
    Enhanced Auto Voice Webhook with Real-time Customer Listening
    Customer ke har message ko sun kar intelligent response deta hai
    """
    permission_classes = [permissions.AllowAny]  # Twilio webhook
    
    def post(self, request):
        """Main webhook handler for customer conversations"""
        try:
            logger.info(f"🎭 Enhanced Auto Voice Webhook Called")
            logger.info(f"   Request Data: {dict(request.POST)}")
            
            # Extract Twilio data
            call_sid = request.POST.get('CallSid')
            call_status = request.POST.get('CallStatus', 'in-progress')
            customer_speech = request.POST.get('SpeechResult', '')  # Customer ne kya bola
            customer_confidence = request.POST.get('Confidence', '0.0')
            from_number = request.POST.get('From')
            to_number = request.POST.get('To')
            
            logger.info(f"   Call SID: {call_sid}")
            logger.info(f"   Customer Speech: '{customer_speech}'")
            logger.info(f"   Speech Confidence: {customer_confidence}")
            
            # Find call session
            from .models import CallSession
            call_session = CallSession.objects.filter(twilio_call_sid=call_sid).first()
            
            if not call_session:
                logger.warning(f"Call session not found for SID: {call_sid}")
                return self.create_basic_response("Thank you for calling. Please hold.")
            
            # Get agent
            agent = call_session.agent
            if not agent:
                logger.warning(f"No agent assigned to call: {call_sid}")
                return self.create_basic_response("Thank you for calling. One moment please.")
            
            # Handle different call scenarios
            if customer_speech:
                # Customer ne kuch bola hai - Process karo
                return self.handle_customer_speech(
                    customer_speech=customer_speech,
                    agent=agent,
                    call_session=call_session,
                    confidence=float(customer_confidence) if customer_confidence else 0.0
                )
            else:
                # Pehli baar call connect hui hai - Opening response do
                return self.create_opening_response(agent, call_session)
                
        except Exception as e:
            logger.error(f"Enhanced webhook error: {str(e)}")
            return self.create_error_response()
    
    def handle_customer_speech(self, customer_speech, agent, call_session, confidence):
        """
        Customer ke speech ko process kar ke intelligent response deta hai
        Real-time conversation handling
        """
        try:
            logger.info(f"🎤 Processing customer speech: '{customer_speech}'")
            logger.info(f"   Agent: {agent.name}")
            logger.info(f"   Confidence: {confidence}")
            
            # Log conversation
            self.log_conversation(call_session, "customer", customer_speech)
            
            # Generate intelligent response based on customer speech
            agent_response = self.generate_intelligent_response(
                customer_speech=customer_speech,
                agent=agent,
                call_session=call_session,
                confidence=confidence
            )
            
            # Log agent response
            self.log_conversation(call_session, "agent", agent_response)
            
            # Create TwiML response with continued listening
            response = VoiceResponse()
            
            # Agent responds to customer
            response.say(agent_response, voice='alice', language='en-US')
            
            # Continue listening for customer response
            gather = response.gather(
                input='speech',
                timeout=15,  # Longer timeout for customer to think
                action='/api/calls/enhanced-voice-webhook/',
                method='POST',
                speech_timeout='auto',
                partial_result_callback='/api/calls/speech-partial/',  # For real-time processing
                enhanced=True  # Enable enhanced speech recognition
            )
            
            # Prompt for more conversation
            gather.say("What are your thoughts on that?", voice='alice')
            
            # If no response, keep conversation going
            response.say("I'd love to hear more from you. What questions do you have?", voice='alice')
            
            # Redirect back to continue conversation
            response.redirect('/api/calls/enhanced-voice-webhook/')
            
            logger.info(f"✅ Intelligent response sent: {agent_response[:50]}...")
            
            return Response(str(response), content_type='application/xml')
            
        except Exception as e:
            logger.error(f"Customer speech handling error: {str(e)}")
            return self.create_recovery_response(customer_speech)
    
    def generate_intelligent_response(self, customer_speech, agent, call_session, confidence):
        """
        Customer ke speech ke base par intelligent response generate karta hai
        Sales conversation ke liye optimized
        """
        try:
            speech_lower = customer_speech.lower().strip()
            customer_name = call_session.caller_name or ""
            
            # Analyze customer intent and sentiment
            intent = self.analyze_customer_intent(speech_lower)
            sentiment = self.analyze_customer_sentiment(speech_lower)
            
            logger.info(f"   Intent: {intent}, Sentiment: {sentiment}")
            
            # Generate response based on intent and sentiment
            if intent == 'positive_interest':
                if sentiment == 'excited':
                    response = f"I love your enthusiasm! You're exactly the type of person who gets the most value from this. {customer_name if customer_name else 'Let me'} tell you specifically how this works for people like you. What's your biggest goal right now?"
                else:
                    response = f"That's fantastic to hear! I can tell you're someone who recognizes a good opportunity. Based on what you're telling me, I think you'd really benefit from this. What specific results are you looking for?"
            
            elif intent == 'pricing_question':
                response = f"Great question about the investment! The value you get far exceeds the cost, and I'll show you exactly how. But first, help me understand - what would this need to do for you to make it a no-brainer decision?"
            
            elif intent == 'skepticism':
                if sentiment == 'concerned':
                    response = f"I completely understand your concerns, and honestly, I'd be skeptical too if I were in your shoes. Many of my best customers felt exactly the same way. What specific aspect worries you most? I'd rather address it directly."
                else:
                    response = f"I appreciate you being honest with me. That shows you're someone who thinks things through carefully. What would need to happen for this to make sense for you?"
            
            elif intent == 'information_request':
                response = f"Absolutely! I'd love to explain that in detail. Let me break it down in a way that makes sense for your specific situation. Based on what you've told me, here's what's most important for you to know..."
            
            elif intent == 'objection':
                response = f"I hear you, and I want to make sure I'm not wasting your time. Help me understand - what would need to change for this to be worth exploring? I'd rather know now than keep going if it's not a fit."
            
            elif intent == 'ready_to_move_forward':
                response = f"Perfect! I love working with people who can make decisions quickly. Let me make sure I have everything I need to get you started. What's the best way to move forward from here?"
            
            else:  # general conversation
                if sentiment == 'positive':
                    response = f"I really appreciate you sharing that with me. It helps me understand exactly how to help you. Based on what you're telling me, I think you're going to love what I have to show you. What's most important to you right now?"
                elif sentiment == 'neutral':
                    response = f"Thank you for that insight. I want to make sure I'm focusing on what matters most to you. Help me understand - what would make the biggest difference in your situation right now?"
                else:  # negative sentiment
                    response = f"I can hear that this might not be the right timing, and I respect that. Help me understand what's going on so I can either help or get out of your way. What's your biggest challenge right now?"
            
            # Add agent's personality touch
            if hasattr(agent, 'voice_tone'):
                if agent.voice_tone == 'friendly':
                    response = response.replace("I think", "I really think").replace("That's", "That's really")
                elif agent.voice_tone == 'professional':
                    response = response.replace("I love", "I appreciate").replace("fantastic", "excellent")
            
            return response
            
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            return f"Thank you for sharing that with me. I want to make sure I understand - could you tell me more about what's most important to you?"
    
    def analyze_customer_intent(self, speech_lower):
        """Customer ke intent ko analyze karta hai"""
        if any(word in speech_lower for word in ['yes', 'interested', 'sounds good', 'tell me more', 'sounds great']):
            return 'positive_interest'
        elif any(word in speech_lower for word in ['price', 'cost', 'expensive', 'how much', 'money']):
            return 'pricing_question'
        elif any(word in speech_lower for word in ['scam', 'doubt', 'suspicious', 'not sure', 'skeptical']):
            return 'skepticism'
        elif any(word in speech_lower for word in ['explain', 'how does', 'what is', 'tell me about']):
            return 'information_request'
        elif any(word in speech_lower for word in ['no', 'not interested', 'busy', 'not now', 'later']):
            return 'objection'
        elif any(word in speech_lower for word in ['ready', 'let\\'s do it', 'sign me up', 'start', 'proceed']):
            return 'ready_to_move_forward'
        else:
            return 'general'
    
    def analyze_customer_sentiment(self, speech_lower):
        """Customer ke sentiment ko analyze karta hai"""
        if any(word in speech_lower for word in ['excited', 'amazing', 'perfect', 'fantastic', 'love it']):
            return 'excited'
        elif any(word in speech_lower for word in ['good', 'nice', 'okay', 'sure', 'fine']):
            return 'positive'
        elif any(word in speech_lower for word in ['concerned', 'worried', 'problem', 'issue']):
            return 'concerned'
        elif any(word in speech_lower for word in ['angry', 'frustrated', 'annoyed', 'upset']):
            return 'negative'
        else:
            return 'neutral'
    
    def create_opening_response(self, agent, call_session):
        """Opening response with sales script integration"""
        try:
            response = VoiceResponse()
            
            # Get customer name
            customer_name = call_session.caller_name or ""
            
            # Use agent's sales script if available
            if hasattr(agent, 'sales_script_text') and agent.sales_script_text:
                opening_message = agent.sales_script_text
                
                # Replace placeholders
                opening_message = opening_message.replace('[NAME]', customer_name if customer_name else 'there')
                
                if hasattr(agent, 'business_info') and agent.business_info:
                    company_name = agent.business_info.get('company_name', 'our company')
                    opening_message = opening_message.replace('[COMPANY]', company_name)
                    
                    product_name = agent.business_info.get('product_name', 'our solution')
                    opening_message = opening_message.replace('[PRODUCT]', product_name)
                
                # Add listening prompt
                opening_message += " I'd love to hear your thoughts on this. What interests you most?"
                
            else:
                # Default opening with listening
                if customer_name:
                    opening_message = f"Hello {customer_name}! This is {agent.name}. I'm calling because I have something that could really benefit you. But first, I'd love to hear from you - what's your biggest priority right now?"
                else:
                    opening_message = f"Hello! This is {agent.name}. Thank you for taking my call. I'd love to learn more about you first - what's most important to you these days?"
            
            # Agent speaks
            response.say(opening_message, voice='alice', language='en-US')
            
            # Listen for customer response
            gather = response.gather(
                input='speech',
                timeout=15,
                action='/api/calls/enhanced-voice-webhook/',
                method='POST',
                speech_timeout='auto',
                enhanced=True
            )
            
            # Encourage response
            gather.say("Please feel free to share your thoughts.", voice='alice')
            
            # If no response
            response.say("I'd love to hear from you. What questions do you have?", voice='alice')
            response.redirect('/api/calls/enhanced-voice-webhook/')
            
            logger.info(f"✅ Opening response sent for agent: {agent.name}")
            
            return Response(str(response), content_type='application/xml')
            
        except Exception as e:
            logger.error(f"Opening response error: {str(e)}")
            return self.create_basic_response(f"Hello! This is {agent.name if agent else 'your assistant'}. How can I help you today?")
    
    def log_conversation(self, call_session, speaker, message):
        """Conversation ko database mein log karta hai"""
        try:
            conversation_entry = {
                'timestamp': timezone.now().isoformat(),
                'speaker': speaker,
                'message': message,
                'call_sid': call_session.twilio_call_sid
            }
            
            # Add to call session notes
            current_notes = call_session.notes or ""
            conversation_log = f"{current_notes}\n[{conversation_entry['timestamp']}] {speaker.upper()}: {message}"
            call_session.notes = conversation_log
            call_session.save()
            
        except Exception as e:
            logger.error(f"Conversation logging error: {str(e)}")
    
    def create_basic_response(self, message):
        """Basic TwiML response"""
        response = VoiceResponse()
        response.say(message, voice='alice', language='en-US')
        return Response(str(response), content_type='application/xml')
    
    def create_recovery_response(self, customer_speech):
        """Recovery response when processing fails"""
        response = VoiceResponse()
        response.say("I understand what you're saying. Let me respond to that properly.", voice='alice')
        
        gather = response.gather(
            input='speech',
            timeout=10,
            action='/api/calls/enhanced-voice-webhook/',
            method='POST'
        )
        gather.say("Could you please repeat that? I want to make sure I address your question properly.", voice='alice')
        
        return Response(str(response), content_type='application/xml')
    
    def create_error_response(self):
        """Error response"""
        response = VoiceResponse()
        response.say("I apologize for the technical difficulty. Let me try again.", voice='alice')
        response.pause(length=1)
        response.say("How can I help you today?", voice='alice')
        return Response(str(response), content_type='application/xml')


# Add URL for enhanced webhook
enhanced_auto_voice_webhook_view = EnhancedAutoVoiceWebhookView.as_view()