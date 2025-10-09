import requests
import json
from django.conf import settings
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class HomeAIService:
    """
    HomeAI integration for AI-powered calling
    Real-time conversation handling with AI
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'HOMEAI_API_KEY', '')
        self.base_url = getattr(settings, 'HOMEAI_BASE_URL', 'https://api.homeai.com/v1')
        self.model = getattr(settings, 'HOMEAI_MODEL', 'gpt-4-voice')
        
    def create_agent_persona(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create AI persona based on agent configuration
        Agent ki personality aur behavior define karta hai
        """
        persona_prompt = self._build_persona_prompt(agent_config)
        
        try:
            response = requests.post(
                f"{self.base_url}/personas",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'name': agent_config.get('name', 'AI Sales Agent'),
                    'personality_type': agent_config.get('personality_type', 'friendly'),
                    'voice_model': agent_config.get('voice_model', 'en-US-female-1'),
                    'system_prompt': persona_prompt,
                    'conversation_style': agent_config.get('conversation_style', 'conversational'),
                    'language': 'en-US',
                    'response_speed': 'fast'
                }
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"HomeAI persona creation failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"HomeAI API error: {str(e)}")
            return None
    
    def start_conversation(self, persona_id: str, customer_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start AI conversation with customer
        Customer ke saath conversation start karta hai
        """
        try:
            conversation_context = self._build_conversation_context(customer_context)
            
            response = requests.post(
                f"{self.base_url}/conversations",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'persona_id': persona_id,
                    'context': conversation_context,
                    'customer_info': {
                        'phone_number': customer_context.get('phone_number'),
                        'name': customer_context.get('name'),
                        'previous_interactions': customer_context.get('previous_calls', 0),
                        'interest_level': customer_context.get('interest_level', 'warm'),
                        'preferences': customer_context.get('preferences', {})
                    },
                    'call_objective': customer_context.get('call_objective', 'sales'),
                    'max_duration': 1800  # 30 minutes max
                }
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"HomeAI conversation start failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"HomeAI conversation error: {str(e)}")
            return None
    
    def process_customer_response(self, conversation_id: str, customer_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process customer response and generate AI reply
        Customer ka response process kar ke AI ka reply generate karta hai
        """
        try:
            response = requests.post(
                f"{self.base_url}/conversations/{conversation_id}/respond",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'customer_input': customer_input,
                    'context_update': context or {},
                    'analyze_sentiment': True,
                    'detect_intent': True,
                    'generate_insights': True
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"HomeAI response processing failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"HomeAI response processing error: {str(e)}")
            return None
    
    def handle_objection(self, conversation_id: str, objection_text: str, customer_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle customer objections intelligently
        Customer ke objections ko handle karta hai
        """
        try:
            response = requests.post(
                f"{self.base_url}/conversations/{conversation_id}/handle-objection",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'objection': objection_text,
                    'customer_profile': customer_context,
                    'response_strategy': 'empathetic_solution_focused',
                    'maintain_rapport': True,
                    'provide_alternatives': True
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"HomeAI objection handling failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"HomeAI objection handling error: {str(e)}")
            return None
    
    def schedule_callback_intelligent(self, conversation_id: str, customer_preference: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently schedule callback based on customer preference
        Customer ki preference ke according callback schedule karta hai
        """
        try:
            response = requests.post(
                f"{self.base_url}/conversations/{conversation_id}/schedule-callback",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'customer_availability': customer_preference.get('availability', {}),
                    'urgency_level': customer_preference.get('urgency', 'medium'),
                    'preferred_time': customer_preference.get('preferred_time'),
                    'timezone': customer_preference.get('timezone', 'UTC'),
                    'callback_reason': customer_preference.get('reason', 'Follow-up discussion'),
                    'auto_suggest_times': True
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"HomeAI callback scheduling failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"HomeAI callback scheduling error: {str(e)}")
            return None
    
    def analyze_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Analyze complete conversation for insights
        Conversation analyze kar ke insights nikalta hai
        """
        try:
            response = requests.get(
                f"{self.base_url}/conversations/{conversation_id}/analysis",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                params={
                    'include_sentiment': True,
                    'include_intent': True,
                    'include_satisfaction': True,
                    'include_conversion_probability': True,
                    'include_objections': True,
                    'include_improvement_suggestions': True
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"HomeAI conversation analysis failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"HomeAI conversation analysis error: {str(e)}")
            return None
    
    def update_agent_learning(self, persona_id: str, conversation_outcomes: list) -> bool:
        """
        Update AI agent learning from conversation outcomes
        AI agent ko conversation outcomes se sikhata hai
        """
        try:
            response = requests.post(
                f"{self.base_url}/personas/{persona_id}/learn",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'learning_data': conversation_outcomes,
                    'learning_type': 'conversation_outcomes',
                    'update_strategy': 'incremental',
                    'preserve_personality': True
                }
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"HomeAI learning update error: {str(e)}")
            return False
    
    def _build_persona_prompt(self, agent_config: Dict[str, Any]) -> str:
        """Build system prompt for AI persona"""
        business_info = agent_config.get('conversation_memory', {}).get('business_info', {})
        personality = agent_config.get('personality_type', 'friendly')
        
        base_prompt = f"""
You are {agent_config.get('name', 'AI Sales Assistant')}, a professional {personality} sales representative.

BUSINESS CONTEXT:
- Company: {business_info.get('company_name', 'Our Company')}
- Product/Service: {business_info.get('product_description', 'Our premium services')}
- Value Proposition: {business_info.get('value_proposition', 'Best solution for your needs')}

PERSONALITY TRAITS:
- {personality.title()} and approachable
- Professional yet conversational
- Empathetic listener
- Solution-focused
- Patient with objections

CONVERSATION GUIDELINES:
1. Always greet warmly and introduce yourself
2. Listen actively to customer needs
3. Ask relevant qualifying questions
4. Present solutions based on their specific needs
5. Handle objections with empathy
6. Guide towards a positive outcome
7. If customer is busy, offer to schedule callback
8. Maintain professional tone throughout

OBJECTIVES:
- Understand customer needs
- Present relevant solutions
- Address concerns and objections
- Move towards conversion
- Schedule follow-ups when needed
- Maintain positive customer experience

Remember: You're representing a real business with real solutions. Be authentic, helpful, and focused on genuinely helping the customer.
        """
        
        return base_prompt.strip()
    
    def _build_conversation_context(self, customer_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build conversation context for AI"""
        return {
            'call_type': customer_context.get('call_type', 'outbound'),
            'customer_history': {
                'previous_calls': customer_context.get('previous_calls', 0),
                'last_interaction': customer_context.get('last_interaction'),
                'interest_level': customer_context.get('interest_level', 'warm'),
                'previous_objections': customer_context.get('previous_objections', [])
            },
            'call_objective': customer_context.get('call_objective', 'sales_qualification'),
            'expected_duration': customer_context.get('expected_duration', '10-15 minutes'),
            'priority_level': customer_context.get('priority_level', 'medium')
        }
    
    def generate_response(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate AI response for testing or real-time conversation
        Test ke liye ya real conversation ke liye AI response generate karta hai
        """
        if not self.api_key:
            # Mock response for testing when API key is not configured
            return {
                'text': f"Hello! I received your message: '{message}'. This is a test response from your AI agent with {context.get('personality', 'friendly')} personality using {context.get('voice_model', 'default')} voice model.",
                'audio_url': 'https://example.com/mock-audio.mp3',
                'personality_analysis': {
                    'detected_tone': context.get('personality', 'friendly'),
                    'confidence': 95,
                    'emotion': 'positive'
                },
                'processing_time': 150,
                'success': True
            }
        
        try:
            response = requests.post(
                f"{self.base_url}/generate",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'message': message,
                    'context': context or {},
                    'voice_model': context.get('voice_model', 'en-US-female-1'),
                    'personality': context.get('personality', 'friendly'),
                    'response_format': 'text_and_audio',
                    'max_response_length': 200
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"HomeAI generate response failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"HomeAI generate response error: {str(e)}")
            return None

# Demo/Mock service for development
class MockHomeAIService(HomeAIService):
    """
    Mock HomeAI service for development and testing
    Real HomeAI nahi hai to demo responses deta hai
    """
    
    def create_agent_persona(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'persona_id': f"mock_persona_{agent_config.get('name', 'agent').lower()}",
            'name': agent_config.get('name', 'AI Sales Agent'),
            'status': 'active',
            'created_at': '2025-10-01T12:00:00Z'
        }
    
    def start_conversation(self, persona_id: str, customer_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'conversation_id': f"mock_conv_{customer_context.get('phone_number', '123')}",
            'status': 'active',
            'initial_message': f"Hello! This is {persona_id.replace('mock_persona_', '').title()}, how are you today?",
            'started_at': '2025-10-01T12:00:00Z'
        }
    
    def process_customer_response(self, conversation_id: str, customer_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        # Simple mock responses based on customer input
        if 'busy' in customer_input.lower():
            return {
                'ai_response': "I understand you're busy. Would you prefer if I call you back at a more convenient time?",
                'sentiment': 'neutral',
                'intent': 'reschedule',
                'suggested_action': 'schedule_callback'
            }
        elif 'not interested' in customer_input.lower():
            return {
                'ai_response': "I appreciate your honesty. May I ask what your main concern is? Perhaps I can address it briefly.",
                'sentiment': 'negative',
                'intent': 'objection',
                'suggested_action': 'handle_objection'
            }
        elif 'interested' in customer_input.lower():
            return {
                'ai_response': "That's wonderful! Let me share how our solution can specifically help you. What's your biggest challenge right now?",
                'sentiment': 'positive',
                'intent': 'interest',
                'suggested_action': 'qualify_further'
            }
        else:
            return {
                'ai_response': "I understand. Let me ask you this - what would be the ideal solution for your current situation?",
                'sentiment': 'neutral',
                'intent': 'information_gathering',
                'suggested_action': 'continue_conversation'
            }
    
    def handle_objection(self, conversation_id: str, objection_text: str, customer_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'objection_response': "I completely understand your concern. Many of our clients had similar thoughts initially. Let me share how we've helped others in your situation...",
            'objection_type': 'price_concern',
            'response_strategy': 'value_demonstration',
            'follow_up_question': "What specific results would make this investment worthwhile for you?"
        }
    
    def schedule_callback_intelligent(self, conversation_id: str, customer_preference: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'callback_scheduled': True,
            'suggested_times': [
                '2025-10-02T10:00:00Z',
                '2025-10-02T14:00:00Z',
                '2025-10-02T16:00:00Z'
            ],
            'message': "Perfect! I'll call you back tomorrow. What time works best for you?"
        }
    
    def analyze_conversation(self, conversation_id: str) -> Dict[str, Any]:
        return {
            'overall_sentiment': 'positive',
            'customer_satisfaction': 7,
            'conversion_probability': 65,
            'key_insights': [
                'Customer showed interest in premium features',
                'Price was a minor concern',
                'Prefers callback in the afternoon'
            ],
            'improvement_suggestions': [
                'Address pricing earlier in conversation',
                'Emphasize ROI benefits more'
            ],
            'objections_raised': ['pricing', 'timing'],
            'positive_indicators': ['asked detailed questions', 'requested follow-up']
        }
    
    def update_agent_learning(self, persona_id: str, conversation_outcomes: list) -> bool:
        return True
