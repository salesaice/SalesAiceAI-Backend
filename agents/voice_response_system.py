"""
AI Agent Voice Response System
Agent ko voice main responses dene ke liye complete system
"""

import pyttsx3
import threading
import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from .models import Agent
from .ai_conversation_system import hume_ai_webhook
import requests

logger = logging.getLogger(__name__)

class AgentVoiceResponseSystem:
    """
    Complete AI Agent Voice Response System
    Agents ko voice responses generate karne ke liye
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.agent = None
        self.tts_engine = None
        self.voice_settings = {}
        self.setup_voice_system()
        
    def setup_voice_system(self):
        """Voice system setup karta hai"""
        try:
            # Get agent details
            self.agent = Agent.objects.get(id=self.agent_id)
            
            # Initialize TTS Engine
            self.tts_engine = pyttsx3.init()
            
            # Configure voice based on agent settings
            self.configure_agent_voice()
            
            logger.info(f"Voice system initialized for agent: {self.agent.name}")
            
        except Exception as e:
            logger.error(f"Voice system setup error: {str(e)}")
            raise
    
    def configure_agent_voice(self):
        """Agent ke voice settings configure karta hai"""
        try:
            # Get available voices
            voices = self.tts_engine.getProperty('voices')
            
            # Agent ki voice model ke according setup
            voice_model = getattr(self.agent, 'voice_model', 'en-US-female-1')
            voice_tone = getattr(self.agent, 'voice_tone', 'friendly')
            tone_settings = getattr(self.agent, 'tone_settings', {})
            
            # Voice selection logic
            selected_voice = None
            
            if 'female' in voice_model.lower():
                # Female voice find karo
                for voice in voices:
                    if any(keyword in voice.name.lower() for keyword in ['female', 'zira', 'eva', 'samantha']):
                        selected_voice = voice.id
                        break
            elif 'male' in voice_model.lower():
                # Male voice find karo
                for voice in voices:
                    if any(keyword in voice.name.lower() for keyword in ['male', 'david', 'mark', 'tom']):
                        selected_voice = voice.id
                        break
            
            if selected_voice:
                self.tts_engine.setProperty('voice', selected_voice)
            
            # Voice tone ke according rate aur volume set karo
            rate_settings = {
                'friendly': 160,
                'professional': 140,
                'enthusiastic': 180,
                'calm': 120,
                'confident': 150
            }
            
            volume_settings = {
                'friendly': 0.9,
                'professional': 0.8,
                'enthusiastic': 1.0,
                'calm': 0.7,
                'confident': 0.85
            }
            
            # Set voice properties
            self.tts_engine.setProperty('rate', rate_settings.get(voice_tone, 150))
            self.tts_engine.setProperty('volume', volume_settings.get(voice_tone, 0.8))
            
            # Store voice settings
            self.voice_settings = {
                'voice_model': voice_model,
                'voice_tone': voice_tone,
                'rate': rate_settings.get(voice_tone, 150),
                'volume': volume_settings.get(voice_tone, 0.8),
                'custom_settings': tone_settings
            }
            
            logger.info(f"Voice configured for {self.agent.name}: {voice_tone} tone at {self.voice_settings['rate']} rate")
            
        except Exception as e:
            logger.error(f"Voice configuration error: {str(e)}")
    
    def generate_voice_response(self, customer_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Customer message ke liye AI response generate karta hai aur voice main speak karta hai
        """
        try:
            # Generate text response first
            text_response = self.generate_text_response(customer_message, context)
            
            # Convert to voice
            voice_output = self.speak_response(text_response['response_text'])
            
            return {
                'success': True,
                'text_response': text_response['response_text'],
                'voice_output': voice_output,
                'emotion_detected': text_response.get('customer_emotion'),
                'response_strategy': text_response.get('strategy'),
                'agent_voice_settings': self.voice_settings,
                'timestamp': text_response.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Voice response generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback_response': "I apologize, but I'm having technical difficulties. Let me try again."
            }
    
    def generate_text_response(self, customer_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Customer message ke liye intelligent text response generate karta hai"""
        try:
            from datetime import datetime
            
            # Emotion detection (Hume AI integration)
            emotion_data = self.detect_customer_emotion(customer_message)
            
            # Response generation based on emotion and context
            response_text = self.create_contextual_response(customer_message, emotion_data, context)
            
            # Response strategy
            strategy = self.determine_response_strategy(emotion_data, customer_message)
            
            return {
                'response_text': response_text,
                'customer_emotion': emotion_data,
                'strategy': strategy,
                'confidence': emotion_data.get('confidence', 0.7),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Text response generation error: {str(e)}")
            return {
                'response_text': "Thank you for your message. How can I help you today?",
                'customer_emotion': {'primary_emotion': 'neutral', 'confidence': 0.5},
                'strategy': 'fallback'
            }
    
    def detect_customer_emotion(self, message: str) -> Dict[str, Any]:
        """Customer message main emotion detect karta hai"""
        try:
            # Simple emotion detection (can be enhanced with Hume AI)
            positive_words = ['good', 'great', 'excellent', 'love', 'interested', 'yes', 'perfect']
            negative_words = ['bad', 'terrible', 'hate', 'no', 'disappointed', 'angry', 'frustrated']
            question_words = ['how', 'what', 'when', 'where', 'why', 'can you', 'could you']
            
            message_lower = message.lower()
            
            # Emotion scoring
            positive_score = sum(1 for word in positive_words if word in message_lower)
            negative_score = sum(1 for word in negative_words if word in message_lower)
            question_score = sum(1 for word in question_words if word in message_lower)
            
            # Determine primary emotion
            if positive_score > negative_score:
                primary_emotion = 'interest' if question_score > 0 else 'satisfaction'
                confidence = min(0.9, 0.6 + (positive_score * 0.1))
            elif negative_score > positive_score:
                primary_emotion = 'frustration'
                confidence = min(0.9, 0.6 + (negative_score * 0.1))
            elif question_score > 0:
                primary_emotion = 'curiosity'
                confidence = 0.7
            else:
                primary_emotion = 'neutral'
                confidence = 0.6
            
            return {
                'primary_emotion': primary_emotion,
                'confidence': confidence,
                'sentiment_indicators': {
                    'positive_score': positive_score,
                    'negative_score': negative_score,
                    'question_score': question_score
                }
            }
            
        except Exception as e:
            logger.error(f"Emotion detection error: {str(e)}")
            return {'primary_emotion': 'neutral', 'confidence': 0.5}
    
    def create_contextual_response(self, message: str, emotion_data: Dict, context: Dict = None) -> str:
        """Context aur emotion ke according response create karta hai"""
        try:
            emotion = emotion_data['primary_emotion']
            agent_name = self.agent.name
            
            # Response templates based on emotion
            response_templates = {
                'interest': [
                    f"Hi, this is {agent_name}! I can hear you're interested, and that's fantastic!",
                    f"Hello! {agent_name} here, and I love your enthusiasm!",
                    f"Great to connect with you! This is {agent_name}, and your interest tells me you're looking for the right solution."
                ],
                'satisfaction': [
                    f"Hello! This is {agent_name}, and I'm delighted to hear your positive response!",
                    f"Hi there! {agent_name} speaking, and your satisfaction means everything to us!",
                    f"Wonderful! This is {agent_name}, and I'm thrilled you're happy with our conversation."
                ],
                'frustration': [
                    f"Hi, this is {agent_name}. I understand your concern, and I'm here to help resolve this.",
                    f"Hello, {agent_name} here. I can sense your frustration, and I want to address that immediately.",
                    f"This is {agent_name}, and I hear your concern. Let me help you with that right away."
                ],
                'curiosity': [
                    f"Hello! This is {agent_name}, and I love that you're asking the right questions!",
                    f"Hi there! {agent_name} speaking, and your curiosity shows you're thinking this through carefully.",
                    f"Great question! This is {agent_name}, and I'm excited to provide you with all the details."
                ],
                'neutral': [
                    f"Hello! This is {agent_name}. How can I help you today?",
                    f"Hi there! {agent_name} speaking. What can I assist you with?",
                    f"Good day! This is {agent_name}. I'm here to help you with any questions you have."
                ]
            }
            
            # Select appropriate response
            if emotion in response_templates:
                import random
                base_response = random.choice(response_templates[emotion])
            else:
                base_response = f"Hello! This is {agent_name}. Thank you for your message."
            
            # Add context-specific information if available
            if context:
                if context.get('product_interest'):
                    base_response += " I understand you're interested in our products. Let me share the perfect solution for you."
                elif context.get('pricing_question'):
                    base_response += " Regarding pricing, let me explain our value proposition and flexible options."
                elif context.get('service_inquiry'):
                    base_response += " About our services, let me show you exactly how we can benefit you."
            
            return base_response
            
        except Exception as e:
            logger.error(f"Response creation error: {str(e)}")
            return f"Hello! This is {getattr(self.agent, 'name', 'your AI assistant')}. How can I help you today?"
    
    def determine_response_strategy(self, emotion_data: Dict, message: str) -> str:
        """Response strategy determine karta hai"""
        emotion = emotion_data['primary_emotion']
        confidence = emotion_data['confidence']
        
        if emotion == 'frustration' and confidence > 0.7:
            return 'empathy_first'
        elif emotion in ['interest', 'curiosity'] and confidence > 0.6:
            return 'engagement_focused'
        elif emotion == 'satisfaction':
            return 'momentum_building'
        else:
            return 'information_gathering'
    
    def speak_response(self, text: str) -> Dict[str, Any]:
        """Text ko voice main convert karke speak karta hai"""
        try:
            print(f"\n🤖 {self.agent.name} (Voice): {text}")
            print("🔊 Agent speaking...")
            
            # Voice output in separate thread
            def speak_async():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as e:
                    logger.error(f"TTS error: {str(e)}")
            
            # Start voice output
            voice_thread = threading.Thread(target=speak_async)
            voice_thread.start()
            voice_thread.join(timeout=30)  # 30 second timeout
            
            return {
                'status': 'completed',
                'text_spoken': text,
                'voice_settings': self.voice_settings,
                'duration_estimate': len(text.split()) * 0.6  # Approximate speaking time
            }
            
        except Exception as e:
            logger.error(f"Voice speaking error: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'text_spoken': text
            }
    
    def update_voice_settings(self, new_settings: Dict[str, Any]):
        """Agent ke voice settings update karta hai"""
        try:
            if 'voice_tone' in new_settings:
                self.agent.voice_tone = new_settings['voice_tone']
            
            if 'voice_model' in new_settings:
                self.agent.voice_model = new_settings['voice_model']
            
            if 'tone_settings' in new_settings:
                current_settings = getattr(self.agent, 'tone_settings', {})
                current_settings.update(new_settings['tone_settings'])
                self.agent.tone_settings = current_settings
            
            # Save agent updates
            self.agent.save()
            
            # Reconfigure voice
            self.configure_agent_voice()
            
            logger.info(f"Voice settings updated for agent: {self.agent.name}")
            
            return {
                'success': True,
                'updated_settings': self.voice_settings,
                'message': 'Voice settings updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Voice settings update error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Helper Functions for Easy Integration

def get_agent_voice_response(agent_id: str, customer_message: str, context: Dict = None) -> Dict[str, Any]:
    """
    Simple function to get voice response from agent
    Usage: response = get_agent_voice_response("agent-uuid", "Hello, how are you?")
    """
    try:
        voice_system = AgentVoiceResponseSystem(agent_id)
        return voice_system.generate_voice_response(customer_message, context)
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'fallback_response': "I'm sorry, I'm having technical difficulties. Please try again."
        }

def setup_agent_voice(agent_id: str, voice_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent ke voice setup karne ke liye
    Usage: setup_agent_voice("agent-uuid", {"voice_tone": "professional", "voice_model": "en-US-female-1"})
    """
    try:
        voice_system = AgentVoiceResponseSystem(agent_id)
        return voice_system.update_voice_settings(voice_settings)
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def test_agent_voice(agent_id: str, test_message: str = "Hello! This is a voice test.") -> Dict[str, Any]:
    """
    Agent ki voice test karne ke liye
    Usage: test_agent_voice("agent-uuid")
    """
    try:
        voice_system = AgentVoiceResponseSystem(agent_id)
        return voice_system.speak_response(test_message)
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }