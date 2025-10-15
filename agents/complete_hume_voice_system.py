"""
COMPLETE HUME AI VOICE AGENT SYSTEM
Aapke existing Hume AI ke saath complete integration
Real-time live calls aur agent training ke liye
"""

import requests
import json
import logging
import sys
import os
from datetime import datetime
from django.conf import settings
from twilio.twiml.voice_response import VoiceResponse
from .models import Agent

# Import Hume AI integration from parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from live_hume_integration import LiveHumeAIIntegration
except ImportError:
    print("Warning: Using fallback Hume AI integration")
    
    class LiveHumeAIIntegration:
        def __init__(self):
            self.hume_api_key = 'mb5K22hbrOAvddJfkP4ZlScpMVHItgw0jfyxj0F1byGJ7j1w'
            self.hume_evi_config_id = '13624648-658a-49b1-81cb-a0f2e2b05de5'
            
        def create_evi_session(self, context=None):
            return {"id": "fallback-session-id"}
            
        def send_message_to_evi(self, session_id, message):
            return {
                "text": f"Thank you for your message. How can I help you today?",
                "emotion_analysis": {"primary_emotion": "neutral"},
                "confidence": 0.7
            }

logger = logging.getLogger(__name__)

class CompleteHumeVoiceAgent:
    """
    Complete Voice Agent System with Hume AI EVI Integration
    Real-time calls, learning, aur agent training
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.agent = None
        self.hume_integration = LiveHumeAIIntegration()
        self.current_session_id = None
        self.conversation_history = []
        self.setup_agent()
        
    def setup_agent(self):
        """Agent setup aur configuration"""
        try:
            self.agent = Agent.objects.get(id=self.agent_id)
            logger.info(f"Voice agent setup completed for: {self.agent.name}")
        except Agent.DoesNotExist:
            logger.error(f"Agent not found: {self.agent_id}")
            raise ValueError(f"Agent not found: {self.agent_id}")
    
    def start_live_call(self, customer_phone: str, call_context: dict = None):
        """
        Live call start karta hai with Hume AI EVI
        Real-time conversation ke liye
        """
        try:
            # Step 1: Create Hume AI EVI session
            session_context = {
                "agent_id": self.agent_id,
                "agent_name": self.agent.name,
                "customer_phone": customer_phone,
                "call_type": "live_sales_call",
                "agent_personality": {
                    "tone": getattr(self.agent, 'voice_tone', 'professional'),
                    "approach": "consultative_sales",
                    "objectives": ["build_rapport", "understand_needs", "present_solution"]
                }
            }
            
            if call_context:
                session_context.update(call_context)
            
            # Create EVI session
            session = self.hume_integration.create_evi_session(session_context)
            
            if session:
                self.current_session_id = session["id"]
                
                # Log call start
                call_log = {
                    "agent_id": self.agent_id,
                    "agent_name": self.agent.name,
                    "customer_phone": customer_phone,
                    "hume_session_id": self.current_session_id,
                    "call_start_time": datetime.now().isoformat(),
                    "status": "active"
                }
                
                logger.info(f"Live call started: {call_log}")
                
                return {
                    "success": True,
                    "session_id": self.current_session_id,
                    "agent_name": self.agent.name,
                    "message": "Live call session started with Hume AI EVI",
                    "call_log": call_log
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create Hume AI EVI session",
                    "fallback": "Using basic voice system"
                }
                
        except Exception as e:
            logger.error(f"Live call start error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_customer_speech(self, customer_speech: str, call_sid: str = None):
        """
        Customer speech ko Hume AI se process karta hai
        Real-time response generate karta hai
        """
        try:
            if not self.current_session_id:
                # Create new session if not exists
                session_result = self.start_live_call("unknown", {"emergency_session": True})
                if not session_result["success"]:
                    return self.create_fallback_response(customer_speech)
            
            # Step 1: Send to Hume AI EVI for processing
            evi_response = self.hume_integration.send_message_to_evi(
                self.current_session_id, 
                customer_speech
            )
            
            if evi_response:
                # Step 2: Create Twilio response with EVI output
                response = VoiceResponse()
                
                # Use EVI's intelligent response
                agent_response = evi_response["text"]
                
                # Add agent personality touch
                personalized_response = self.personalize_response(
                    agent_response, 
                    evi_response.get("emotion_analysis", {})
                )
                
                # Generate voice output
                response.say(
                    personalized_response,
                    voice=self.get_agent_voice_settings(),
                    language='en-US'
                )
                
                # Continue conversation
                response.gather(
                    input='speech',
                    timeout=10,
                    action=f'/agents/webhooks/twilio-continue/{call_sid}/' if call_sid else '/agents/webhooks/twilio/',
                    method='POST',
                    speech_timeout='auto'
                )
                
                # Step 3: Log conversation for learning
                conversation_turn = {
                    "timestamp": datetime.now().isoformat(),
                    "customer_speech": customer_speech,
                    "agent_response": personalized_response,
                    "emotion_analysis": evi_response.get("emotion_analysis", {}),
                    "confidence": evi_response.get("confidence", 0.5),
                    "hume_session_id": self.current_session_id
                }
                
                self.conversation_history.append(conversation_turn)
                
                # Step 4: Real-time learning
                self.apply_real_time_learning(conversation_turn)
                
                logger.info(f"Processed speech - Customer: {customer_speech[:50]}... Agent: {personalized_response[:50]}...")
                
                return {
                    "success": True,
                    "twiml_response": str(response),
                    "agent_response": personalized_response,
                    "emotion_analysis": evi_response.get("emotion_analysis", {}),
                    "conversation_turn": conversation_turn
                }
            else:
                # Fallback to basic response
                return self.create_fallback_response(customer_speech)
                
        except Exception as e:
            logger.error(f"Speech processing error: {str(e)}")
            return self.create_fallback_response(customer_speech)
    
    def personalize_response(self, evi_response: str, emotion_data: dict):
        """
        EVI response ko agent personality ke saath personalize karta hai
        """
        try:
            agent_name = self.agent.name
            voice_tone = getattr(self.agent, 'voice_tone', 'professional')
            
            # Add agent personality
            if not evi_response.startswith(agent_name):
                # Add name introduction if not present
                if emotion_data.get("primary_emotion") in ["interest", "curiosity"]:
                    personalized = f"Hi, this is {agent_name}! {evi_response}"
                elif emotion_data.get("primary_emotion") in ["frustration", "anger"]:
                    personalized = f"I'm {agent_name}, and {evi_response}"
                else:
                    personalized = f"This is {agent_name}. {evi_response}"
            else:
                personalized = evi_response
            
            # Adjust tone based on agent settings
            if voice_tone == "enthusiastic" and "!" not in personalized:
                personalized = personalized.replace(".", "!")
            elif voice_tone == "calm":
                personalized = personalized.replace("!", ".")
            
            return personalized
            
        except Exception as e:
            logger.error(f"Response personalization error: {str(e)}")
            return evi_response  # Return original if personalization fails
    
    def get_agent_voice_settings(self):
        """Agent ke voice settings return karta hai"""
        voice_model = getattr(self.agent, 'voice_model', 'alice')
        
        # Map voice models to Twilio voices
        voice_mapping = {
            'en-US-female-1': 'alice',
            'en-US-female-2': 'Polly.Joanna',
            'en-US-male-1': 'man',
            'en-US-male-2': 'Polly.Matthew'
        }
        
        return voice_mapping.get(voice_model, 'alice')
    
    def apply_real_time_learning(self, conversation_turn: dict):
        """
        Real-time conversation se agent learning apply karta hai
        """
        try:
            emotion = conversation_turn.get("emotion_analysis", {}).get("primary_emotion", "neutral")
            confidence = conversation_turn.get("confidence", 0.5)
            
            # High confidence positive emotions = successful interaction
            if confidence > 0.7 and emotion in ["interest", "satisfaction", "joy"]:
                learning_data = {
                    "interaction_type": "positive_engagement",
                    "customer_response": conversation_turn["customer_speech"],
                    "agent_response": conversation_turn["agent_response"],
                    "emotion_detected": emotion,
                    "confidence": confidence,
                    "timestamp": conversation_turn["timestamp"],
                    "learning_source": "real_time_hume_evi"
                }
                
                # Apply learning to agent (extend existing agent learning)
                self.agent.learning_data = getattr(self.agent, 'learning_data', {})
                
                if 'successful_interactions' not in self.agent.learning_data:
                    self.agent.learning_data['successful_interactions'] = []
                
                self.agent.learning_data['successful_interactions'].append(learning_data)
                
                # Keep only last 50 interactions for performance
                if len(self.agent.learning_data['successful_interactions']) > 50:
                    self.agent.learning_data['successful_interactions'] = \
                        self.agent.learning_data['successful_interactions'][-50:]
                
                self.agent.save()
                
                logger.info(f"Real-time learning applied for positive interaction: {emotion}")
            
            # Track unsuccessful patterns for improvement
            elif confidence > 0.7 and emotion in ["frustration", "anger", "disappointment"]:
                improvement_data = {
                    "interaction_type": "needs_improvement",
                    "customer_response": conversation_turn["customer_speech"],
                    "agent_response": conversation_turn["agent_response"],
                    "emotion_detected": emotion,
                    "confidence": confidence,
                    "timestamp": conversation_turn["timestamp"]
                }
                
                self.agent.learning_data = getattr(self.agent, 'learning_data', {})
                
                if 'improvement_areas' not in self.agent.learning_data:
                    self.agent.learning_data['improvement_areas'] = []
                
                self.agent.learning_data['improvement_areas'].append(improvement_data)
                self.agent.save()
                
                logger.info(f"Improvement area identified: {emotion}")
                
        except Exception as e:
            logger.error(f"Real-time learning error: {str(e)}")
    
    def create_fallback_response(self, customer_speech: str):
        """
        Hume AI fail hone par fallback response
        """
        response = VoiceResponse()
        
        # Intelligent fallback based on keywords
        speech_lower = customer_speech.lower()
        agent_name = self.agent.name
        
        if "interested" in speech_lower:
            fallback_text = f"Hi, this is {agent_name}! I'm excited that you're interested. Let me share exactly how we can help you."
        elif "price" in speech_lower or "cost" in speech_lower:
            fallback_text = f"This is {agent_name}. I understand pricing is important. Let me show you the incredible value you'll receive."
        elif "not sure" in speech_lower or "hesit" in speech_lower:
            fallback_text = f"Hi, {agent_name} here. Your hesitation is completely understandable. Let me address your concerns directly."
        elif "angry" in speech_lower or "frustrat" in speech_lower:
            fallback_text = f"I'm {agent_name}, and I completely understand your frustration. Let me help resolve this immediately."
        else:
            fallback_text = f"Hello, this is {agent_name}. Thank you for sharing that with me. How can I best help you today?"
        
        response.say(fallback_text, voice=self.get_agent_voice_settings(), language='en-US')
        response.gather(input='speech', timeout=10, action='/agents/webhooks/twilio/', method='POST')
        
        return {
            "success": True,
            "twiml_response": str(response),
            "agent_response": fallback_text,
            "source": "fallback"
        }
    
    def end_call_and_analyze(self):
        """
        Call end karne par complete analysis aur learning
        """
        try:
            if not self.conversation_history:
                return {"message": "No conversation to analyze"}
            
            # Call analysis
            total_turns = len(self.conversation_history)
            emotions_detected = [turn.get("emotion_analysis", {}).get("primary_emotion", "neutral") 
                               for turn in self.conversation_history]
            
            positive_emotions = sum(1 for emotion in emotions_detected 
                                  if emotion in ["interest", "satisfaction", "joy"])
            negative_emotions = sum(1 for emotion in emotions_detected 
                                  if emotion in ["frustration", "anger", "disappointment"])
            
            # Determine call outcome
            call_outcome = "successful" if positive_emotions > negative_emotions else "needs_improvement"
            
            # Complete learning update
            call_analysis = {
                "call_end_time": datetime.now().isoformat(),
                "total_conversation_turns": total_turns,
                "emotions_detected": emotions_detected,
                "positive_interactions": positive_emotions,
                "negative_interactions": negative_emotions,
                "call_outcome": call_outcome,
                "hume_session_id": self.current_session_id,
                "conversation_history": self.conversation_history
            }
            
            # Update agent learning with complete call data
            self.agent.learning_data = getattr(self.agent, 'learning_data', {})
            
            if 'completed_calls' not in self.agent.learning_data:
                self.agent.learning_data['completed_calls'] = []
            
            self.agent.learning_data['completed_calls'].append(call_analysis)
            
            # Update agent performance metrics
            performance_update = {
                "calls_completed": len(self.agent.learning_data['completed_calls']),
                "success_rate": sum(1 for call in self.agent.learning_data['completed_calls'] 
                                  if call['call_outcome'] == 'successful') / len(self.agent.learning_data['completed_calls']),
                "last_updated": datetime.now().isoformat()
            }
            
            self.agent.learning_data['performance_metrics'] = performance_update
            self.agent.save()
            
            logger.info(f"Call analysis completed for agent {self.agent.name}: {call_outcome}")
            
            return {
                "success": True,
                "call_analysis": call_analysis,
                "performance_update": performance_update,
                "message": f"Call completed and analyzed. Outcome: {call_outcome}"
            }
            
        except Exception as e:
            logger.error(f"Call analysis error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Helper Functions for Easy Integration

def start_hume_voice_call(agent_id: str, customer_phone: str, context: dict = None):
    """
    Hume AI ke saath live voice call start karta hai
    Usage: start_hume_voice_call("agent-uuid", "+1234567890")
    """
    try:
        voice_agent = CompleteHumeVoiceAgent(agent_id)
        return voice_agent.start_live_call(customer_phone, context)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def process_live_speech(agent_id: str, customer_speech: str, call_sid: str = None):
    """
    Live call main customer speech process karta hai
    Usage: process_live_speech("agent-uuid", "Hello, I'm interested", "call-sid")
    """
    try:
        voice_agent = CompleteHumeVoiceAgent(agent_id)
        return voice_agent.process_customer_speech(customer_speech, call_sid)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "fallback_response": "I apologize, I'm having technical difficulties. Let me try again."
        }

def complete_call_analysis(agent_id: str):
    """
    Call complete hone par analysis aur learning apply karta hai
    Usage: complete_call_analysis("agent-uuid")
    """
    try:
        voice_agent = CompleteHumeVoiceAgent(agent_id)
        return voice_agent.end_call_and_analyze()
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }