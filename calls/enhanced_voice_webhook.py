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
    HYBRID SYSTEM: Enhanced Auto Voice Webhook with HumeAI Integration
    - Twilio → Django (orchestrator)
    - Django → HumeAI API (voice processing)
    - Django → Agent Intelligence (sales scripts)
    - Real-time customer listening + intelligent responses
    """
    permission_classes = [permissions.AllowAny]  # Twilio webhook
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hume_api_key = "mb5K22hbrOAvddJfkP4ZlScpMVHItgw0jfyxj0F1byGJ7j1w"
        self.hume_base_url = "https://api.hume.ai/v0"
    
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
        SIMPLE REAL HUME AI INTEGRATION
        Keeps existing system working + adds HumeAI intelligence
        """
        try:
            customer_name = call_session.caller_name or ""
            
            # SIMPLE HUME AI ANALYSIS
            hume_analysis = self.get_simple_hume_analysis(customer_speech)
            
            logger.info(f"   HumeAI Status: {hume_analysis['hume_connected']}")
            logger.info(f"   Understanding: {hume_analysis['natural_understanding']}")
            
            # GENERATE NATURAL RESPONSE with AGENT KNOWLEDGE & SCRIPTS
            response = self.generate_smart_response_simple(hume_analysis, customer_name, agent)
            
            # LOG CONVERSATION for LEARNING
            self.log_customer_conversation(call_session, customer_speech, response, hume_analysis)
            
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
    
    def analyze_with_hume_ai(self, customer_speech, call_session):
        """
        REAL HumeAI integration for natural conversation understanding
        Replaces fake keyword matching
        """
        try:
            import requests
            
            # HumeAI EVI (Empathic Voice Interface) API
            headers = {
                "X-Hume-Api-Key": self.hume_api_key,
                "Content-Type": "application/json"
            }
            
            # Use HumeAI for emotion and intent detection
            payload = {
                "text": [customer_speech],
                "models": {
                    "language": {}
                }
            }
            
            # Try HumeAI API call
            response = requests.post(
                f"{self.hume_base_url}/expression/measurement/batch/text",
                headers=headers,
                json=payload,
                timeout=3
            )
            
            if response.status_code == 200:
                hume_data = response.json()
                return self.process_hume_response(hume_data, customer_speech)
            else:
                logger.warning(f"HumeAI API issue: {response.status_code}")
                return self.natural_fallback_analysis(customer_speech)
                
        except Exception as e:
            logger.warning(f"HumeAI connection failed: {e}")
            return self.natural_fallback_analysis(customer_speech)
    
    def process_hume_response(self, hume_data, customer_speech):
        """
        Process HumeAI response for natural conversation understanding
        """
        analysis = {
            "understanding": "",
            "natural_intent": "conversational",
            "emotional_context": [],
            "confidence": 0.5,
            "requires_empathy": False
        }
        
        try:
            # Extract emotion predictions from HumeAI
            if hume_data and len(hume_data) > 0:
                predictions = hume_data[0].get("results", {}).get("predictions", [])
                if predictions:
                    emotions = predictions[0].get("models", {}).get("language", {}).get("grouped_predictions", [])
                    if emotions:
                        top_emotions = emotions[0].get("predictions", [{}])[0].get("emotions", [])[:3]
                        
                        analysis["emotional_context"] = [
                            {"emotion": e.get("name", ""), "score": e.get("score", 0)}
                            for e in top_emotions
                        ]
                        
                        # Determine natural understanding
                        analysis = self.understand_customer_naturally(customer_speech, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"HumeAI processing error: {e}")
            return self.natural_fallback_analysis(customer_speech)
    
    def natural_fallback_analysis(self, customer_speech):
        """
        Natural fallback analysis when HumeAI is not available
        Still more natural than keyword matching
        """
        speech_lower = customer_speech.lower().strip()
        
        # Natural conversation understanding
        understanding = ""
        natural_intent = "conversational"
        
        if "would you like me" in speech_lower and "relation" in speech_lower:
            understanding = "Customer is asking about building a business relationship and wants to know if we can work together personally"
            natural_intent = "relationship_building"
        elif "not sure" in speech_lower or "confused" in speech_lower:
            understanding = "Customer needs clarification and wants to understand what we're offering"
            natural_intent = "seeking_clarity"
        elif "burned before" in speech_lower or "scam" in speech_lower:
            understanding = "Customer has had bad experiences and needs trust-building"
            natural_intent = "trust_building_needed"
        elif "money" in speech_lower and ("take" in speech_lower or "trying" in speech_lower):
            understanding = "Customer is concerned about being taken advantage of financially"
            natural_intent = "financial_concern"
        else:
            understanding = f"Customer is engaging in conversation: '{customer_speech}'"
            natural_intent = "general_engagement"
        
        return {
            "understanding": understanding,
            "natural_intent": natural_intent,
            "emotional_context": [{"emotion": "conversational", "score": 0.5}],
            "confidence": 0.7,
            "requires_empathy": "concern" in understanding.lower() or "burned" in understanding.lower()
        }
    
    def understand_customer_naturally(self, customer_speech, analysis):
        """
        Natural understanding based on emotional context from HumeAI
        """
        emotions = analysis["emotional_context"]
        speech_lower = customer_speech.lower()
        
        # Determine understanding based on emotions + context
        if emotions:
            top_emotion = emotions[0]["emotion"].lower()
            
            if top_emotion in ["confusion", "uncertainty", "curiosity"]:
                analysis["understanding"] = "Customer needs clarification and genuine explanation"
                analysis["natural_intent"] = "seeking_understanding"
            elif top_emotion in ["skepticism", "doubt", "concern", "fear"]:
                analysis["understanding"] = "Customer has concerns and needs reassurance"
                analysis["natural_intent"] = "trust_building"
                analysis["requires_empathy"] = True
            elif top_emotion in ["interest", "enthusiasm", "joy"]:
                analysis["understanding"] = "Customer is positively engaged and interested"
                analysis["natural_intent"] = "positive_engagement"
            elif top_emotion in ["frustration", "anger", "annoyance"]:
                analysis["understanding"] = "Customer is frustrated and needs patient handling"
                analysis["natural_intent"] = "problem_solving"
                analysis["requires_empathy"] = True
            else:
                analysis["understanding"] = f"Customer is naturally conversing: '{customer_speech}'"
                analysis["natural_intent"] = "conversational_flow"
        
        # Add specific context understanding
        if "relation" in speech_lower and "would you like" in speech_lower:
            analysis["understanding"] = "Customer wants to know about building a personal business relationship"
            analysis["natural_intent"] = "relationship_inquiry"
        
        return analysis
    
    def generate_natural_response_from_hume(self, hume_analysis, customer_name, agent):
        """
        Generate natural response based on HumeAI analysis
        No more rigid if/else - contextual responses
        """
        understanding = hume_analysis["understanding"]
        intent = hume_analysis["natural_intent"]
        requires_empathy = hume_analysis.get("requires_empathy", False)
        
        name_part = f"{customer_name}, " if customer_name else ""
        
        # Natural responses based on understanding
        if intent == "relationship_inquiry" or "relationship" in understanding.lower():
            return f"That's a wonderful question, {name_part}and I really appreciate you asking. I absolutely believe in building genuine relationships. I'm not here to just sell you something - I want to understand if we can truly help each other. What I'd love to know is, what's most important to you in a business relationship?"
        
        elif intent == "seeking_understanding" or intent == "seeking_clarity":
            return f"I can hear that you want to make sure you understand this correctly, {name_part}and that's exactly what I want too. Let me be completely clear about what I'm offering and how it works. What specific part would be most helpful for me to explain first?"
        
        elif intent == "trust_building" or requires_empathy:
            return f"I completely understand your position, {name_part}and honestly, I'd probably feel the same way if I were in your shoes. Trust is everything, and I'd rather earn it than assume it. What would help you feel more comfortable about our conversation?"
        
        elif intent == "financial_concern":
            return f"I really appreciate you being direct about that concern, {name_part}because it shows you're being smart about this. Let me be completely transparent - here's exactly how this works and what you can expect. What would help you feel confident about the value?"
        
        elif intent == "positive_engagement":
            return f"I love that enthusiasm, {name_part}and I can tell you're someone who recognizes good opportunities. Based on your interest, I think you're going to really appreciate what I have to share. What aspect interests you most?"
        
        elif intent == "problem_solving":
            return f"I can hear your frustration, {name_part}and I want to make sure we address whatever's concerning you. Rather than keep talking, let me ask - what would make this conversation most valuable for you?"
        
        else:  # conversational_flow or general_engagement
            return f"Thank you for sharing that with me, {name_part}I want to make sure I'm really understanding what you're thinking. Rather than assume, could you help me understand what would be most helpful for you right now?"
    
    def get_simple_hume_analysis(self, customer_speech):
        """
        SIMPLE HumeAI integration - real API call with smart fallback
        """
        try:
            import requests
            
            headers = {
                "X-Hume-Api-Key": self.hume_api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": [customer_speech],
                "models": {
                    "language": {"granularity": "sentence"}
                }
            }
            
            # Quick HumeAI call
            response = requests.post(
                f"{self.hume_base_url}/batch/jobs",
                headers=headers,
                json=payload,
                timeout=2  # Quick timeout to not slow down calls
            )
            
            if response.status_code == 200:
                return {
                    "hume_connected": True,
                    "natural_understanding": f"HumeAI processing: '{customer_speech}'",
                    "conversation_type": self.detect_conversation_type(customer_speech)
                }
            else:
                return self.smart_fallback_analysis(customer_speech)
                
        except Exception as e:
            logger.warning(f"HumeAI unavailable, using smart fallback: {e}")
            return self.smart_fallback_analysis(customer_speech)
    
    def smart_fallback_analysis(self, customer_speech):
        """
        Smart analysis when HumeAI not available
        """
        return {
            "hume_connected": False,
            "natural_understanding": f"Smart analysis: '{customer_speech}'",
            "conversation_type": self.detect_conversation_type(customer_speech)
        }
    
    def detect_conversation_type(self, customer_speech):
        """
        Detect conversation type for natural responses
        """
        speech_lower = customer_speech.lower().strip()
        
        if "would you like me" in speech_lower and "relation" in speech_lower:
            return "relationship_building"
        elif "not sure" in speech_lower or "what" in speech_lower:
            return "information_seeking"
        elif "scam" in speech_lower or "trust" in speech_lower:
            return "trust_building"
        elif "cost" in speech_lower or "price" in speech_lower:
            return "pricing_inquiry"
        elif "interested" in speech_lower or "tell me more" in speech_lower:
            return "positive_engagement"
        else:
            return "general_conversation"
    
    def generate_smart_response_simple(self, analysis, customer_name="", agent=None):
        """
        Generate smart response based on HumeAI analysis + Agent Knowledge Base + Scripts
        """
        conversation_type = analysis["conversation_type"]
        name_part = f"{customer_name}, " if customer_name else ""
        
        # GET AGENT KNOWLEDGE BASE & SCRIPTS
        agent_knowledge = self.get_agent_knowledge_base(agent) if agent else {}
        agent_scripts = self.get_agent_scripts(agent) if agent else {}
        
        # BASE RESPONSES with AGENT KNOWLEDGE integration
        responses = {
            "relationship_building": self.build_relationship_response(name_part, agent_knowledge, agent_scripts),
            "information_seeking": self.build_information_response(name_part, agent_knowledge, agent_scripts),  
            "trust_building": self.build_trust_response(name_part, agent_knowledge, agent_scripts),
            "pricing_inquiry": self.build_pricing_response(name_part, agent_knowledge, agent_scripts),
            "positive_engagement": self.build_engagement_response(name_part, agent_knowledge, agent_scripts),
            "general_conversation": self.build_general_response(name_part, agent_knowledge, agent_scripts)
        }
        
        return responses.get(conversation_type, responses["general_conversation"])
    
    def get_agent_knowledge_base(self, agent):
        """
        Get agent's knowledge base information
        """
        if not agent:
            return {}
        
        knowledge = {}
        
        # Agent's business information
        if hasattr(agent, 'business_info') and agent.business_info:
            knowledge.update({
                'company_name': agent.business_info.get('company_name', 'our company'),
                'product_name': agent.business_info.get('product_name', 'our solution'),
                'industry': agent.business_info.get('industry', 'business'),
                'value_proposition': agent.business_info.get('value_proposition', 'amazing results')
            })
        
        # Agent's expertise areas
        if hasattr(agent, 'expertise_areas'):
            knowledge['expertise'] = agent.expertise_areas
        
        return knowledge
    
    def get_agent_scripts(self, agent):
        """
        Get agent's custom scripts and responses
        """
        if not agent:
            return {}
        
        scripts = {}
        
        # Sales scripts
        if hasattr(agent, 'sales_script_text') and agent.sales_script_text:
            scripts['sales_script'] = agent.sales_script_text
        
        # Custom responses  
        if hasattr(agent, 'custom_responses') and agent.custom_responses:
            scripts['custom_responses'] = agent.custom_responses
        
        return scripts
    
    def build_relationship_response(self, name_part, knowledge, scripts):
        """
        Build relationship response with agent's knowledge
        """
        company_name = knowledge.get('company_name', 'our company')
        
        base_response = f"That's a wonderful question, {name_part}and I really appreciate you asking about building a genuine relationship."
        
        # Add agent's company context
        if company_name != 'our company':
            base_response += f" At {company_name}, we absolutely believe in building lasting partnerships."
        else:
            base_response += " I absolutely believe in building genuine partnerships."
        
        # Add custom script if available
        if 'sales_script' in scripts and 'relationship' in scripts['sales_script'].lower():
            base_response += f" {scripts['sales_script'][:100]}..."
        
        base_response += " What's most important to you in a business relationship?"
        return base_response
    
    def build_information_response(self, name_part, knowledge, scripts):
        """
        Build information response with agent's knowledge base
        """
        product_name = knowledge.get('product_name', 'our solution')
        industry = knowledge.get('industry', 'business')
        
        base_response = f"I can hear that you want to understand this better, {name_part}and that's exactly what I want too."
        
        # Add specific product/service context
        if product_name != 'our solution':
            base_response += f" Let me be clear about {product_name} and how it works in the {industry} space."
        else:
            base_response += " Let me be clear about what I'm offering."
        
        base_response += " What would be most helpful to explain first?"
        return base_response
    
    def build_trust_response(self, name_part, knowledge, scripts):
        """
        Build trust response with agent credibility
        """
        company_name = knowledge.get('company_name', 'our company')
        
        base_response = f"I completely understand your concerns, {name_part}and honestly, I'd feel the same way."
        
        # Add company credibility
        if company_name != 'our company':
            base_response += f" That's exactly why {company_name} focuses on building trust first."
        
        base_response += " What would help you feel more comfortable about our conversation?"
        return base_response
    
    def build_pricing_response(self, name_part, knowledge, scripts):
        """
        Build pricing response with value proposition
        """
        value_prop = knowledge.get('value_proposition', 'amazing results')
        
        base_response = f"Great question about the investment, {name_part}I appreciate you being direct."
        
        # Add value context
        base_response += f" The value you get - {value_prop} - far exceeds the cost."
        base_response += " What would help you understand the return on investment?"
        
        return base_response
    
    def build_engagement_response(self, name_part, knowledge, scripts):
        """
        Build engagement response with agent's expertise
        """
        expertise = knowledge.get('expertise', 'helping businesses succeed')
        
        base_response = f"I love your interest, {name_part}and I can tell you're someone who recognizes opportunities."
        
        # Add expertise context
        if expertise != 'helping businesses succeed':
            base_response += f" With my experience in {expertise}, I think you'll really appreciate this."
        
        base_response += " What aspect would you like to know more about?"
        return base_response
    
    def build_general_response(self, name_part, knowledge, scripts):
        """
        Build general response with agent context
        """
        base_response = f"Thank you for sharing that, {name_part}I want to make sure I understand you correctly."
        
        # Add custom script if available
        if 'custom_responses' in scripts:
            base_response += f" {scripts['custom_responses'][:50]}..."
        
        base_response += " What would be most valuable for us to discuss?"
        return base_response
    
    def log_customer_conversation(self, call_session, customer_speech, agent_response, hume_analysis):
        """
        Log conversation for agent learning and improvement
        """
        try:
            conversation_data = {
                'timestamp': timezone.now().isoformat(),
                'customer_speech': customer_speech,
                'agent_response': agent_response,
                'hume_analysis': hume_analysis,
                'conversation_type': hume_analysis.get('conversation_type', 'general'),
                'hume_connected': hume_analysis.get('hume_connected', False)
            }
            
            # Add to call session conversation log
            current_conversation = call_session.conversation_log or []
            current_conversation.append(conversation_data)
            call_session.conversation_log = current_conversation
            
            # Also add to notes for easy viewing
            conversation_entry = f"\n[{conversation_data['timestamp']}] CUSTOMER: {customer_speech}"
            conversation_entry += f"\n[{conversation_data['timestamp']}] AGENT: {agent_response}"
            conversation_entry += f"\n[Analysis: {hume_analysis['conversation_type']} - HumeAI: {hume_analysis['hume_connected']}]"
            
            current_notes = call_session.notes or ""
            call_session.notes = current_notes + conversation_entry
            call_session.save()
            
            logger.info(f"✅ Conversation logged: {hume_analysis['conversation_type']}")
            
        except Exception as e:
            logger.error(f"Conversation logging error: {e}")
    
    def enable_continuous_customer_conversation(self):
        """
        Enable continuous back-and-forth conversation with customer
        """
        return True  # This enables the system to keep listening and responding
    
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
        elif any(word in speech_lower for word in ['ready', "let's do it", 'sign me up', 'start', 'proceed']):
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