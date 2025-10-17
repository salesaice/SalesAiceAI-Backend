"""
COMPLETE AUTO VOICE SYSTEM INTEGRATION
calls/start-call API ko complete Hume AI voice system ke saath integrate karta hai
Ek API call se sara system automatically chal jata hai
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
import logging

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from .models import CallSession, CallQueue
from agents.models import Agent
import sys
import os

# Add path for Hume AI integration
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from live_hume_integration import LiveHumeAIIntegration
except ImportError:
    print("Warning: Using fallback Hume AI integration")
    LiveHumeAIIntegration = None

# Import HumeAI Voice Setup for dynamic agent configuration
try:
    from .hume_ai_voice_setup import HumeAIVoiceIntegration
except ImportError:
    HumeAIVoiceIntegration = None
    print("Warning: HumeAI Voice Setup not available")

logger = logging.getLogger(__name__)

class AutoVoiceCallSystem:
    """
    Complete auto voice call system
    Ek API call se sara system automatically start ho jata hai
    """
    
    def __init__(self):
        self.hume_integration = LiveHumeAIIntegration() if LiveHumeAIIntegration else None
        self.twilio_client = None
        self.setup_twilio()
        
    def setup_twilio(self):
        """Twilio client setup"""
        try:
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
            
            if account_sid and auth_token:
                self.twilio_client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
            else:
                logger.warning("Twilio credentials not found")
        except Exception as e:
            logger.error(f"Twilio setup error: {str(e)}")
    
    def start_complete_auto_call(self, user, phone_number, agent_id, call_context=None):
        """
        Complete auto call system - Ek call se sab kuch automatic
        """
        try:
            # Step 1: Validate and get agent
            agent = self.get_and_validate_agent(user, agent_id)
            if not agent:
                return {
                    "success": False,
                    "error": "Agent not found or not available",
                    "code": "AGENT_NOT_AVAILABLE"
                }
            
            # Step 2: Create call session with complete setup
            call_session = self.create_enhanced_call_session(user, phone_number, agent, call_context)
            
            # Step 3: Setup Hume AI EVI session
            hume_session = self.setup_hume_ai_session(agent, call_session, call_context)
            
            # Step 4: Configure agent for auto voice responses
            agent_config = self.configure_agent_for_auto_voice(agent, hume_session)
            
            # Step 5: Initiate Twilio call with complete integration
            twilio_result = self.initiate_auto_twilio_call(phone_number, agent_config, call_session)
            
            # Step 6: Update call session with all integration data
            self.update_call_session_with_integrations(call_session, hume_session, twilio_result)
            
            # Step 7: Start real-time monitoring
            self.start_real_time_monitoring(call_session, agent)
            
            logger.info(f"Auto voice call system started successfully: {call_session.id}")
            
            return {
                "success": True,
                "call_session_id": str(call_session.id),
                "agent_name": agent.name,
                "twilio_call_sid": twilio_result.get("call_sid"),
                "hume_session_id": hume_session.get("session_id") if hume_session else None,
                "status": "call_initiated",
                "message": "Complete auto voice call system started successfully",
                "integrations": {
                    "hume_ai": "active" if hume_session else "fallback",
                    "twilio": "active" if twilio_result.get("success") else "failed",
                    "voice_response": "enabled",
                    "real_time_learning": "active"
                },
                "estimated_connection_time": "10-15 seconds",
                "auto_features": [
                    "Hume AI emotion detection",
                    "Real-time voice responses", 
                    "Automatic agent learning",
                    "Call analytics and reporting",
                    "Performance tracking"
                ]
            }
            
        except Exception as e:
            logger.error(f"Auto voice call system error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": "SYSTEM_ERROR"
            }
    
    def get_and_validate_agent(self, user, agent_id):
        """Agent validate karta hai aur return karta hai"""
        try:
            agent = Agent.objects.get(
                id=agent_id,
                owner=user,  # Fixed: Use owner instead of user
                status='active'
            )
            
            # Agent ko busy status set karo
            agent.status = 'on_call'
            agent.save()
            
            return agent
            
        except Agent.DoesNotExist:
            logger.error(f"Agent not found: {agent_id}")
            return None
        except Exception as e:
            logger.error(f"Agent validation error: {str(e)}")
            return None
    
    def create_enhanced_call_session(self, user, phone_number, agent, call_context):
        """Enhanced call session create karta hai"""
        try:
            # Enhanced call session with all required fields
            call_session = CallSession.objects.create(
                user=user,
                caller_number=getattr(settings, 'TWILIO_PHONE_NUMBER', '+12295152040'),
                callee_number=phone_number,
                caller_name=call_context.get('receiver_name', '') if call_context else '',
                call_type='outbound_auto_voice',
                status='initiated',
                agent=agent,
                ai_summary='Auto voice call initiated with Hume AI integration',
                ai_sentiment='neutral',
                notes=f'Auto call started with agent {agent.name} using Hume AI voice system'
            )
            
            logger.info(f"Enhanced call session created: {call_session.id}")
            return call_session
            
        except Exception as e:
            logger.error(f"Call session creation error: {str(e)}")
            raise
    
    def setup_hume_ai_session(self, agent, call_session, call_context):
        """Hume AI EVI session setup karta hai"""
        try:
            if not self.hume_integration:
                logger.warning("Hume AI integration not available, using fallback")
                return {
                    "session_id": "fallback-session-id",
                    "status": "fallback",
                    "message": "Using fallback voice system"
                }
            
            # NEW: Get agent database content
            sales_script = agent.sales_script_text if agent.sales_script_text else "Hello! How can I help you today?"
            
            # Build knowledge base from agent files
            knowledge_content = ""
            if hasattr(agent, 'knowledge_files') and agent.knowledge_files:
                for file_info in agent.knowledge_files:
                    if 'content' in file_info:
                        knowledge_content += f"{file_info.get('filename', 'Knowledge')}: {file_info['content']}\n\n"
            
            # Business context from agent
            business_info = agent.business_info if hasattr(agent, 'business_info') and agent.business_info else {}
            company_name = business_info.get('name', 'AI Voice Solutions')
            
            # Hume AI session context with AGENT DATABASE CONTENT
            session_context = {
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "call_session_id": str(call_session.id),
                "call_type": "auto_outbound_sales",
                "sales_script": sales_script,  # NEW: From database
                "knowledge_base": knowledge_content,  # NEW: From database
                "agent_personality": {
                    "tone": getattr(agent, 'voice_tone', 'professional'),
                    "approach": "database_driven_sales", 
                    "objectives": ["use_sales_script", "answer_from_knowledge", "learn_conversation"]
                },
                "business_context": {
                    "company": company_name,
                    "industry": business_info.get('industry', 'AI Voice Solutions'),
                    "mission": business_info.get('mission', 'Automated intelligent voice conversations'),
                    "website": getattr(agent, 'website_url', '') if hasattr(agent, 'website_url') else ''
                },
                "hume_config": {
                    "config_id": "e4157120-69f8-40dc-bb48-af6fe658f01e",  # NEW CONFIG ID
                    "use_database_content": True,
                    "learning_enabled": True
                }
            }
            
            if call_context:
                session_context.update(call_context)
            
            # Create Hume AI EVI session
            hume_session = self.hume_integration.create_evi_session(session_context)
            
            if hume_session:
                logger.info(f"Hume AI session created: {hume_session.get('id', 'unknown')}")
                return {
                    "session_id": hume_session.get("id"),
                    "status": "active",
                    "config_id": self.hume_integration.hume_evi_config_id,
                    "context": session_context
                }
            else:
                logger.error("Hume AI session creation failed")
                return {
                    "session_id": "fallback-session-id",
                    "status": "fallback",
                    "message": "Hume AI session failed, using fallback"
                }
                
        except Exception as e:
            logger.error(f"Hume AI session setup error: {str(e)}")
            return {
                "session_id": "fallback-session-id",
                "status": "error",
                "error": str(e)
            }
    
    def configure_agent_for_auto_voice(self, agent, hume_session):
        """Agent ko auto voice responses ke liye configure karta hai"""
        try:
            # Get agent's content from database
            sales_script = agent.sales_script_text if agent.sales_script_text else f"Hello! This is {agent.name}. How can I help you today?"
            knowledge_files_count = len(agent.knowledge_files) if hasattr(agent, 'knowledge_files') and agent.knowledge_files else 0
            business_name = agent.business_info.get('name', agent.name) if hasattr(agent, 'business_info') and agent.business_info else agent.name
            
            # Agent configuration for auto voice with DATABASE CONTENT
            agent_config = {
                "agent_id": str(agent.id),
                "name": agent.name,
                "voice_tone": getattr(agent, 'voice_tone', 'professional'),
                "voice_model": getattr(agent, 'voice_model', 'en-US-female-1'),
                "hume_session_id": hume_session.get("session_id"),
                "hume_config_id": "e4157120-69f8-40dc-bb48-af6fe658f01e",  # NEW CONFIG
                "hume_integration_status": hume_session.get("status"),
                "auto_response_enabled": True,
                "real_time_learning": True,
                "emotion_detection": True,
                "database_content": {
                    "sales_script": sales_script,
                    "knowledge_files": knowledge_files_count,
                    "business_name": business_name,
                    "content_source": "agent_database"
                },
                "conversation_objectives": [
                    "Use sales script from database",
                    "Answer questions from knowledge files", 
                    "Learn from customer interactions",
                    "Provide business-specific responses",
                    "Adapt based on agent configuration"
                ],
                "fallback_responses": {
                    "connection_issue": f"Hi! This is {agent.name} from {business_name}. I'm experiencing a slight connection issue. Let me try again.",
                    "no_response": f"Hello! This is {agent.name} from {business_name}. Can you hear me clearly?",
                    "technical_error": f"Hi! This is {agent.name} from {business_name}. I apologize for any technical difficulties. How can I help you today?",
                    "no_sales_script": sales_script,  # Use database sales script
                    "knowledge_available": f"I have access to {knowledge_files_count} knowledge files to answer your questions."
                }
            }
            
            logger.info(f"Agent configured for auto voice: {agent.name}")
            return agent_config
            
        except Exception as e:
            logger.error(f"Agent configuration error: {str(e)}")
            return {
                "agent_id": str(agent.id),
                "name": agent.name,
                "auto_response_enabled": False,
                "error": str(e)
            }
    
    def get_or_create_hume_config(self, agent_config):
        """
        Use existing HumeAI configuration (no longer creates new)
        Returns: 14158840-3c40-40e6-84d3-43cb01c2f726
        """
        try:
            # Always use existing config
            existing_config_id = "14158840-3c40-40e6-84d3-43cb01c2f726"
            
            # Try to use HumeAIVoiceIntegration for caching
            if HumeAIVoiceIntegration:
                try:
                    hume_voice_integration = HumeAIVoiceIntegration()
                    
                    # Get agent from database
                    agent_name = agent_config.get('name', 'AI Agent')
                    agent = Agent.objects.filter(name=agent_name).first()
                    
                    if agent:
                        logger.info(f"Using existing HumeAI config for agent: {agent.name}")
                        result = hume_voice_integration.create_voice_agent(agent)
                        
                        if result and result.get('success'):
                            config_id = result['config_id']
                            logger.info(f"✅ Using HumeAI config: {config_id}")
                            return config_id
                except Exception as e:
                    logger.warning(f"Cache check failed: {e}, using default config")
            
            # Return existing config
            logger.info(f"Using default HumeAI config: {existing_config_id}")
            return existing_config_id
            
            # Try to get existing config or create new one
            agent_name = agent_config.get('name', 'AI Agent')
            voice_tone = agent_config.get('voice_tone', 'professional')
            
            # Create configuration for this specific agent
            config_data = {
                "name": f"{agent_name} Voice Config",
                "voice": {
                    "provider": "HUME_AI", 
                    "provider_id": "default"
                },
                "personality": {
                    "tone": voice_tone,
                    "approach": "conversational"
                }
            }
            
            # Use HumeAI integration to create config
            new_config = self.hume_integration.create_evi_config(config_data)
            
            if new_config and new_config.get('id'):
                logger.info(f"Created new HumeAI config: {new_config['id']}")
                return new_config['id']
            else:
                # Fallback to default config ID if creation fails
                logger.warning("Failed to create HumeAI config, using fallback")
                return "13624648-658a-49b1-81cb-a0f2e2b05de5"  # Your existing config
                
        except Exception as e:
            logger.error(f"HumeAI config creation error: {str(e)}")
            return "13624648-658a-49b1-81cb-a0f2e2b05de5"  # Fallback config

    def initiate_auto_twilio_call(self, phone_number, agent_config, call_session):
        """Enhanced Auto Twilio call with HYBRID HumeAI+Django integration"""
        try:
            if not self.twilio_client:
                logger.error("Twilio client not available")
                return {
                    "success": False,
                    "error": "Twilio not configured"
                }
            
            # HYBRID SYSTEM: Try HumeAI integration first, fallback to Django-only
            hume_config_id = self.get_or_create_hume_config(agent_config)
            
            if hume_config_id:
                # Use HumeAI for voice processing + Django for agent intelligence
                hume_webhook_url = f"https://api.hume.ai/v0/evi/twilio?config_id={hume_config_id}"
                
                call_params = {
                    "to": phone_number,
                    "from_": getattr(settings, 'TWILIO_PHONE_NUMBER', '+12295152040'),
                    "url": hume_webhook_url,
                    "method": "POST",
                    "status_callback": f"{getattr(settings, 'BASE_URL', 'https://aicegroup.pythonanywhere.com')}/api/calls/status-callback/",
                    "status_callback_event": ["initiated", "ringing", "answered", "completed"],
                    "record": True,
                    "recording_status_callback": f"{getattr(settings, 'BASE_URL', 'https://aicegroup.pythonanywhere.com')}/api/calls/recording-callback/",
                    "machine_detection": "Enable",
                    "machine_detection_timeout": 30,
                    "timeout": 60,
                }
                
                call = self.twilio_client.calls.create(**call_params)
                
                logger.info(f"🎭 HYBRID call initiated: {call.sid}")
                logger.info(f"🎯 HumeAI Webhook: {hume_webhook_url}")
                
                return {
                    "success": True,
                    "call_sid": call.sid,
                    "status": call.status,
                    "webhook_url": hume_webhook_url,
                    "agent_config": agent_config,
                    "hume_ai_integration": {
                        "listening_enabled": True,
                        "dynamic_responses": True,
                        "config_id": hume_config_id,
                        "real_time_processing": True,
                        "hybrid_system": True
                    }
                }
            else:
                # Fallback to Ultimate Production system
                base_url = getattr(settings, 'BASE_URL', 'https://aicegroup.pythonanywhere.com')
                fallback_webhook_url = f"{base_url}/api/calls/ultimate-production-webhook/"
                
                call_params = {
                    "to": phone_number,
                    "from_": getattr(settings, 'TWILIO_PHONE_NUMBER', '+12295152040'),
                    "url": fallback_webhook_url,
                    "method": "POST",
                    "status_callback": f"{base_url}/api/calls/status-callback/",
                    "status_callback_event": ["initiated", "ringing", "answered", "completed"],
                    "record": True,
                    "recording_status_callback": f"{base_url}/api/calls/recording-callback/",
                    "machine_detection": "Enable",
                    "machine_detection_timeout": 30,
                    "timeout": 60,
                }
                
                call = self.twilio_client.calls.create(**call_params)
                
                logger.info(f"🎭 Django-only call initiated: {call.sid}")
                logger.info(f"🎯 Django Webhook: {fallback_webhook_url}")
                
                return {
                    "success": True,
                    "call_sid": call.sid,
                    "status": call.status,
                    "webhook_url": fallback_webhook_url,
                    "agent_config": agent_config,
                    "hume_ai_integration": {
                        "listening_enabled": True,
                        "dynamic_responses": True,
                        "config_id": "django_fallback",
                        "real_time_processing": True,
                        "django_fallback": True
                    }
                }
            
        except Exception as e:
            logger.error(f"Enhanced Twilio call initiation error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_call_session_with_integrations(self, call_session, hume_session, twilio_result):
        """Call session ko sab integrations ke saath update karta hai"""
        try:
            # Update call session with all integration data
            if twilio_result.get("success"):
                call_session.twilio_call_sid = twilio_result["call_sid"]
                call_session.status = 'connecting'
                call_session.started_at = timezone.now()
            else:
                call_session.status = 'failed'
            
            # Add integration metadata
            integration_data = {
                "hume_ai": {
                    "session_id": hume_session.get("session_id"),
                    "status": hume_session.get("status"),
                    "config_id": hume_session.get("config_id")
                },
                "twilio": {
                    "call_sid": twilio_result.get("call_sid"),
                    "status": twilio_result.get("status"),
                    "webhook_configured": True
                },
                "auto_voice_system": {
                    "enabled": True,
                    "real_time_learning": True,
                    "emotion_detection": True,
                    "setup_timestamp": timezone.now().isoformat()
                }
            }
            
            # Store integration data in notes field (can be moved to JSON field)
            call_session.notes = f"{call_session.notes}\\n\\nIntegration Data: {json.dumps(integration_data, indent=2)}"
            call_session.save()
            
            logger.info(f"Call session updated with integrations: {call_session.id}")
            
        except Exception as e:
            logger.error(f"Call session update error: {str(e)}")
    
    def start_real_time_monitoring(self, call_session, agent):
        """Real-time monitoring start karta hai"""
        try:
            # Create monitoring entry
            monitoring_data = {
                "call_session_id": str(call_session.id),
                "agent_id": str(agent.id),
                "monitoring_start": timezone.now().isoformat(),
                "features": [
                    "emotion_tracking",
                    "response_effectiveness",
                    "conversation_flow",
                    "customer_satisfaction"
                ],
                "status": "active"
            }
            
            # Store monitoring data (can be extended to separate model)
            agent.learning_data = getattr(agent, 'learning_data', {})
            
            if 'active_call_monitoring' not in agent.learning_data:
                agent.learning_data['active_call_monitoring'] = []
            
            agent.learning_data['active_call_monitoring'].append(monitoring_data)
            agent.save()
            
            logger.info(f"Real-time monitoring started for call: {call_session.id}")
            
        except Exception as e:
            logger.error(f"Real-time monitoring setup error: {str(e)}")


# Auto Voice System Instance
auto_voice_system = AutoVoiceCallSystem()


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Customer phone number'),
            'agent_id': openapi.Schema(type=openapi.TYPE_STRING, description='Agent UUID'),
            'receiver_name': openapi.Schema(type=openapi.TYPE_STRING, description='Customer name (optional)'),
            'call_context': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Additional call context',
                properties={
                    'lead_source': openapi.Schema(type=openapi.TYPE_STRING),
                    'product_interest': openapi.Schema(type=openapi.TYPE_STRING),
                    'customer_notes': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        },
        required=['phone_number', 'agent_id']
    ),
    responses={
        200: openapi.Response(
            description='Auto voice call system started successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'call_session_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'agent_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'integrations': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'auto_features': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING)
        )
                }
            )
        )
    },
    operation_description="Start complete auto voice call with Hume AI integration - Ek API call se sara system automatic",
    tags=['Auto Voice Calls']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_complete_auto_voice_call(request):
    """
    COMPLETE AUTO VOICE CALL API
    Ek API call se complete voice system automatic start ho jata hai
    
    Features:
    - Hume AI EVI integration
    - Real-time voice responses
    - Automatic agent learning
    - Twilio call management
    - Emotion detection
    - Performance tracking
    """
    try:
        phone_number = request.data.get('phone_number')
        agent_id = request.data.get('agent_id')
        receiver_name = request.data.get('receiver_name', '')
        call_context = request.data.get('call_context', {})
        
        # Add receiver name to context
        if receiver_name:
            call_context['receiver_name'] = receiver_name
        
        # Validate required parameters
        if not phone_number or not agent_id:
            return Response({
                'success': False,
                'error': 'Missing required parameters',
                'required': ['phone_number', 'agent_id']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Start complete auto voice call system
        result = auto_voice_system.start_complete_auto_call(
            user=request.user,
            phone_number=phone_number,
            agent_id=agent_id,
            call_context=call_context
        )
        
        if result["success"]:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Auto voice call API error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([])  # Allow Twilio webhooks without authentication
def auto_voice_webhook_handler(request):
    """
    Auto voice webhook handler for Twilio calls
    Complete voice response system with Hume AI integration
    """
    try:
        # Get Twilio data
        call_sid = request.data.get('CallSid') or request.POST.get('CallSid')
        call_status = request.data.get('CallStatus') or request.POST.get('CallStatus')
        speech_result = request.data.get('SpeechResult') or request.POST.get('SpeechResult', '')
        
        logger.info(f"Auto voice webhook: CallSid={call_sid}, Status={call_status}, Speech={speech_result[:50] if speech_result else 'None'}")
        
        # Find call session
        try:
            call_session = CallSession.objects.get(twilio_call_sid=call_sid)
            agent = call_session.agent
        except CallSession.DoesNotExist:
            logger.error(f"Call session not found for CallSid: {call_sid}")
            return create_fallback_voice_response()
        
        # Handle different call states
        if call_status == 'in-progress' and not speech_result:
            # Call answered, send opening message
            return create_opening_voice_response(agent, call_session)
        elif call_status == 'in-progress' and speech_result:
            # Customer spoke, process with Hume AI
            return process_customer_speech_with_hume(agent, speech_result, call_session)
        elif call_status == 'completed':
            # Call ended, process learning
            return finalize_call_with_learning(agent, call_session)
        else:
            # Default response
            return create_default_voice_response(agent)
            
    except Exception as e:
        logger.error(f"Auto voice webhook error: {str(e)}")
        return create_fallback_voice_response()


def create_opening_voice_response(agent, call_session):
    """Opening voice response create karta hai with agent's sales script"""
    try:
        response = VoiceResponse()
        
        # Get customer name from call context
        customer_name = call_session.caller_name or ""
        
        # Get agent's sales script - PRIORITY 1
        opening_message = ""
        
        # Check if agent has sales script text
        if hasattr(agent, 'sales_script_text') and agent.sales_script_text:
            # Use agent's custom sales script
            sales_script = agent.sales_script_text.strip()
            
            # Replace placeholders with actual data
            if customer_name:
                sales_script = sales_script.replace("[NAME]", customer_name)
                sales_script = sales_script.replace("[Customer]", customer_name)
            else:
                sales_script = sales_script.replace("[NAME]", "")
                sales_script = sales_script.replace("[Customer]", "")
            
            # Replace company placeholders if business info exists
            if hasattr(agent, 'business_info') and agent.business_info:
                company_name = agent.business_info.get('company_name', 'our company')
                sales_script = sales_script.replace("[COMPANY]", company_name)
                
                product_name = agent.business_info.get('product_name', 'our solution')
                sales_script = sales_script.replace("[PRODUCT]", product_name)
            
            opening_message = sales_script
            logger.info(f"Using agent's custom sales script for {agent.name}")
            
        else:
            # Fallback to default script if no sales script
            if customer_name:
                opening_message = f"Hello {customer_name}! This is {agent.name}. Thank you for your time. I'm calling because I have something that could really benefit you. How are you doing today?"
            else:
                opening_message = f"Hello! This is {agent.name}. Thank you for taking my call. I'm reaching out because I have something that could really benefit you. How are you doing today?"
            
            logger.info(f"Using default script for agent {agent.name} - no custom sales script found")
        
        # Add voice response
        response.say(opening_message, voice='alice', language='en-US')
        
        # Gather customer response
        response.gather(
            input='speech',
            timeout=10,
            action='/api/calls/auto-voice-webhook/',
            method='POST',
            speech_timeout='auto'
        )
        
        # Fallback if no response
        response.say("I'm sorry, I didn't catch that. Could you please respond?", voice='alice')
        
        logger.info(f"Opening voice response sent for agent {agent.name}")
        
        return Response(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Opening voice response error: {str(e)}")
        return create_fallback_voice_response()


def process_customer_speech_with_hume(agent, customer_speech, call_session):
    """Customer speech ko Hume AI ke saath process karta hai"""
    try:
        # Process with Hume AI if available
        if auto_voice_system.hume_integration:
            # Extract Hume session ID from call session notes
            hume_session_id = extract_hume_session_id(call_session)
            
            if hume_session_id:
                # Send to Hume AI
                hume_response = auto_voice_system.hume_integration.send_message_to_evi(
                    hume_session_id, customer_speech
                )
                
                if hume_response:
                    # Create Twilio response with Hume AI output
                    response = VoiceResponse()
                    
                    # Use Hume AI response
                    agent_response = hume_response["text"]
                    
                    # Add agent personality
                    personalized_response = f"Thank you for sharing that. {agent_response}"
                    
                    response.say(personalized_response, voice='alice', language='en-US')
                    response.gather(
                        input='speech',
                        timeout=10,
                        action='/api/calls/auto-voice-webhook/',
                        method='POST'
                    )
                    
                    # Log for learning
                    log_conversation_for_learning(agent, customer_speech, personalized_response, hume_response)
                    
                    return Response(str(response), content_type='text/xml')
        
        # Fallback response if Hume AI not available
        return create_intelligent_fallback_response(agent, customer_speech)
        
    except Exception as e:
        logger.error(f"Customer speech processing error: {str(e)}")
        return create_fallback_voice_response()


def extract_hume_session_id(call_session):
    """Call session se Hume session ID extract karta hai"""
    try:
        if call_session.notes and "Integration Data:" in call_session.notes:
            # Extract JSON from notes
            notes_parts = call_session.notes.split("Integration Data:")
            if len(notes_parts) > 1:
                integration_data = json.loads(notes_parts[1].strip())
                return integration_data.get("hume_ai", {}).get("session_id")
        
        return "fallback-session-id"
        
    except Exception as e:
        logger.error(f"Hume session ID extraction error: {str(e)}")
        return "fallback-session-id"


def create_intelligent_fallback_response(agent, customer_speech):
    """Intelligent fallback response create karta hai"""
    try:
        response = VoiceResponse()
        
        # Simple keyword-based response
        speech_lower = customer_speech.lower()
        
        if "interested" in speech_lower:
            agent_response = f"That's wonderful! I'm excited that you're interested. Let me share exactly how this can benefit you."
        elif "not interested" in speech_lower:
            agent_response = f"I completely understand. Can I ask what specifically concerns you so I can address it?"
        elif "price" in speech_lower or "cost" in speech_lower:
            agent_response = f"Great question about pricing. Let me explain the value you'll receive and our flexible options."
        elif "busy" in speech_lower:
            agent_response = f"I appreciate your time. This will only take 2 minutes and could save you hours. May I quickly share?"
        else:
            agent_response = f"I hear you. Let me explain how this can specifically help your situation."
        
        response.say(agent_response, voice='alice', language='en-US')
        response.gather(
            input='speech',
            timeout=10,
            action='/api/calls/auto-voice-webhook/',
            method='POST'
        )
        
        return Response(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Intelligent fallback error: {str(e)}")
        return create_fallback_voice_response()


def log_conversation_for_learning(agent, customer_speech, agent_response, hume_response):
    """Conversation ko learning ke liye log karta hai"""
    try:
        learning_entry = {
            "timestamp": timezone.now().isoformat(),
            "customer_speech": customer_speech,
            "agent_response": agent_response,
            "hume_analysis": hume_response.get("emotion_analysis", {}),
            "confidence": hume_response.get("confidence", 0.5),
            "source": "auto_voice_call"
        }
        
        # Add to agent learning data
        agent.learning_data = getattr(agent, 'learning_data', {})
        
        if 'conversation_logs' not in agent.learning_data:
            agent.learning_data['conversation_logs'] = []
        
        agent.learning_data['conversation_logs'].append(learning_entry)
        
        # Keep only last 100 entries
        if len(agent.learning_data['conversation_logs']) > 100:
            agent.learning_data['conversation_logs'] = agent.learning_data['conversation_logs'][-100:]
        
        agent.save()
        
        logger.info(f"Conversation logged for learning: {agent.name}")
        
    except Exception as e:
        logger.error(f"Conversation logging error: {str(e)}")


def finalize_call_with_learning(agent, call_session):
    """Call finalize karta hai aur learning apply karta hai"""
    try:
        # Update call session
        call_session.status = 'completed'
        call_session.ended_at = timezone.now()
        call_session.save()
        
        # Update agent status
        agent.status = 'active'
        agent.save()
        
        # Apply final learning
        apply_final_call_learning(agent, call_session)
        
        logger.info(f"Call finalized with learning: {call_session.id}")
        
        # Return empty response for completed call
        response = VoiceResponse()
        return Response(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Call finalization error: {str(e)}")
        return Response("", content_type='text/xml')


def apply_final_call_learning(agent, call_session):
    """Final call learning apply karta hai"""
    try:
        # Calculate call metrics
        call_duration = (call_session.ended_at - call_session.started_at).total_seconds() if call_session.ended_at and call_session.started_at else 0
        
        # Analyze conversation logs
        conversation_logs = agent.learning_data.get('conversation_logs', [])
        recent_logs = [log for log in conversation_logs if 'auto_voice_call' in log.get('source', '')]
        
        # Determine call outcome
        positive_indicators = sum(1 for log in recent_logs 
                                if 'interested' in log.get('customer_speech', '').lower() or 
                                   'yes' in log.get('customer_speech', '').lower())
        
        call_outcome = 'successful' if positive_indicators > 0 else 'needs_improvement'
        
        # Update performance metrics
        performance_data = {
            "call_completion_time": timezone.now().isoformat(),
            "call_duration": call_duration,
            "conversation_turns": len(recent_logs),
            "outcome": call_outcome,
            "auto_voice_system_used": True,
            "hume_ai_integration": True
        }
        
        # Add to agent performance
        if 'performance_history' not in agent.learning_data:
            agent.learning_data['performance_history'] = []
        
        agent.learning_data['performance_history'].append(performance_data)
        agent.save()
        
        logger.info(f"Final learning applied for agent {agent.name}: {call_outcome}")
        
    except Exception as e:
        logger.error(f"Final learning error: {str(e)}")


def store_conversation_for_learning(call_session, agent, customer_speech, agent_response, emotion_analysis=None):
    """Store conversation data for agent learning"""
    try:
        # Ensure agent has learning_data
        if not hasattr(agent, 'learning_data') or not agent.learning_data:
            agent.learning_data = {}
        
        if 'conversation_logs' not in agent.learning_data:
            agent.learning_data['conversation_logs'] = []
        
        # Create conversation entry
        conversation_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "call_session_id": str(call_session.id),
            "customer_speech": customer_speech,
            "agent_response": agent_response,
            "emotion_analysis": emotion_analysis or {},
            "source": "auto_voice_system"
        }
        
        # Add to conversation logs
        agent.learning_data['conversation_logs'].append(conversation_entry)
        
        # Keep only last 100 conversations to prevent data bloat
        if len(agent.learning_data['conversation_logs']) > 100:
            agent.learning_data['conversation_logs'] = agent.learning_data['conversation_logs'][-100:]
        
        agent.save()
        logger.info(f"Conversation stored for agent {agent.name}")
        
    except Exception as e:
        logger.error(f"Store conversation error: {str(e)}")


def apply_final_agent_learning(call_session, agent, call_outcome):
    """Apply final learning when call completes"""
    try:
        # Ensure agent has learning_data
        if not hasattr(agent, 'learning_data') or not agent.learning_data:
            agent.learning_data = {}
        
        if 'performance_history' not in agent.learning_data:
            agent.learning_data['performance_history'] = []
        
        # Calculate call metrics
        call_duration = 0
        if call_session.started_at and call_session.ended_at:
            call_duration = (call_session.ended_at - call_session.started_at).total_seconds()
        
        # Create performance entry
        performance_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "call_session_id": str(call_session.id),
            "call_outcome": call_outcome,
            "call_duration": call_duration,
            "customer_phone": call_session.callee_number,
            "auto_voice_system": True,
            "learning_source": "final_call_analysis"
        }
        
        # Add performance data
        agent.learning_data['performance_history'].append(performance_data)
        agent.save()
        
        logger.info(f"Final learning applied for agent {agent.name}: {call_outcome}")
        
    except Exception as e:
        logger.error(f"Final learning error: {str(e)}")


def create_fallback_voice_response():
    """Basic fallback voice response"""
    response = VoiceResponse()
    response.say("Thank you for your call. We're experiencing technical difficulties. Please try again later.", voice='alice')
    response.hangup()
    
    return Response(str(response), content_type='text/xml')


def create_default_voice_response(agent):
    """Default voice response"""
    response = VoiceResponse()
    response.say(f"Hello, this is {agent.name}. How can I help you today?", voice='alice')
    response.gather(input='speech', timeout=10, action='/api/calls/auto-voice-webhook/', method='POST')
    
    return Response(str(response), content_type='text/xml')


@method_decorator(csrf_exempt, name='dispatch')
class AutoVoiceCallAPIView(APIView):
    """
    Auto Voice Call API View Class
    Complete auto voice call system with Hume AI integration
    """
    permission_classes = [permissions.AllowAny]  # Remove authentication for testing
    
    @swagger_auto_schema(
        operation_description="Start a complete auto voice call with AI agent",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone_number', 'agent_id'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Customer phone number with country code'),
                'agent_id': openapi.Schema(type=openapi.TYPE_STRING, description='UUID of the AI agent'),
                'receiver_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of the person being called'),
                'call_context': openapi.Schema(type=openapi.TYPE_OBJECT, description='Additional context for the call'),
            }
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'call_session_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'agent_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                    'twilio_call_sid': openapi.Schema(type=openapi.TYPE_STRING),
                    'hume_session_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'estimated_connection_time': openapi.Schema(type=openapi.TYPE_STRING),
                    'auto_features': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_STRING)
                    ),
                    'integrations': openapi.Schema(type=openapi.TYPE_OBJECT),
                }
            )
        }
    )
    def post(self, request):
        """Start auto voice call"""
        try:
            phone_number = request.data.get('phone_number')
            agent_id = request.data.get('agent_id')
            receiver_name = request.data.get('receiver_name', 'Customer')
            call_context = request.data.get('call_context', {})
            
            if not phone_number or not agent_id:
                return Response({
                    'success': False,
                    'error': 'phone_number and agent_id are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Start complete auto voice call
            result = auto_voice_system.start_complete_auto_call(
                phone_number=phone_number,
                agent_id=agent_id,
                receiver_name=receiver_name,
                call_context=call_context,
                user=request.user
            )
            
            if result["success"]:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Auto voice call API error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class AutoVoiceWebhookView(APIView):
    """
    Auto Voice Webhook View for handling Twilio voice responses
    CSRF exempt for Twilio webhook calls
    """
    permission_classes = []  # Allow Twilio webhooks without authentication
    
    def post(self, request):
        """Handle auto voice webhook from Twilio"""
        try:
            # Process webhook request
            call_sid = request.data.get('CallSid') or request.POST.get('CallSid')
            speech_result = request.data.get('SpeechResult') or request.POST.get('SpeechResult')
            call_status = request.data.get('CallStatus') or request.POST.get('CallStatus')
            
            # Find call session
            call_session = None
            if call_sid:
                call_session = CallSession.objects.filter(
                    twilio_call_sid=call_sid  # Fixed: Use twilio_call_sid instead of external_call_id
                ).first()
            
            if not call_session:
                logger.warning(f"Call session not found for SID: {call_sid}")
                return create_fallback_voice_response()
            
            # Get agent
            agent = call_session.agent
            if not agent:
                logger.warning(f"Agent not found for call session: {call_session.id}")
                return create_fallback_voice_response()
            
            # Process voice response based on call status
            if call_status == 'in-progress':
                if speech_result:
                    # Customer spoke - process with Hume AI and respond
                    return self.process_customer_speech(call_session, agent, speech_result)
                else:
                    # Initial call connection - start with greeting
                    return self.create_agent_greeting(agent, call_session)
            elif call_status == 'completed':
                # Call ended - apply final learning
                apply_final_agent_learning(call_session, agent, "completed")
                return Response("OK", status=status.HTTP_200_OK)
            else:
                # Other statuses - use default response
                return create_default_voice_response(agent)
                
        except Exception as e:
            logger.error(f"Auto voice webhook error: {str(e)}")
            return create_fallback_voice_response()
    
    def process_customer_speech(self, call_session, agent, speech_result):
        """Process customer speech with Hume AI and generate response"""
        try:
            # Send to Hume AI for processing
            hume_integration = auto_voice_system.hume_integration
            
            if hume_integration:
                # Get session ID from call session notes
                hume_session_id = None
                if call_session.notes and "hume_session_id" in call_session.notes:
                    try:
                        notes_data = json.loads(call_session.notes.split("Integration Data:")[1])
                        hume_session_id = notes_data.get("hume_ai", {}).get("session_id")
                    except:
                        pass
                
                if hume_session_id:
                    # Send message to Hume AI
                    hume_response = hume_integration.send_message_to_evi(
                        hume_session_id, 
                        speech_result
                    )
                    
                    if hume_response:
                        agent_response = hume_response.get('text', 'I understand. Please tell me more.')
                        emotion_analysis = hume_response.get('emotion_analysis', {})
                        
                        # Store conversation for learning
                        store_conversation_for_learning(call_session, agent, speech_result, agent_response, emotion_analysis)
                        
                        # Create voice response
                        return self.create_voice_response(agent_response, call_session)
            
            # Fallback response
            fallback_responses = [
                "I understand. Can you tell me more about that?",
                "That's interesting. How can I help you with that?",
                "Thank you for sharing that. What would you like to know more about?"
            ]
            
            import random
            response_text = random.choice(fallback_responses)
            return self.create_voice_response(response_text, call_session)
            
        except Exception as e:
            logger.error(f"Customer speech processing error: {str(e)}")
            return create_default_voice_response(agent)
    
    def create_agent_greeting(self, agent, call_session):
        """Create initial agent greeting using agent's sales script"""
        try:
            # Get customer name from call session
            customer_name = getattr(call_session, 'callee_name', 'there')
            
            # Check if agent has custom sales script - PRIORITY 1
            greeting = ""
            
            if hasattr(agent, 'sales_script_text') and agent.sales_script_text:
                # Use agent's custom sales script
                greeting = agent.sales_script_text.strip()
                
                # Replace placeholders with actual data
                if customer_name and customer_name != 'there':
                    greeting = greeting.replace("[NAME]", customer_name)
                    greeting = greeting.replace("[Customer]", customer_name)
                else:
                    greeting = greeting.replace("[NAME]", "")
                    greeting = greeting.replace("[Customer]", "")
                
                # Replace company/product placeholders
                if hasattr(agent, 'business_info') and agent.business_info:
                    company_name = agent.business_info.get('company_name', 'our company')
                    greeting = greeting.replace("[COMPANY]", company_name)
                    
                    product_name = agent.business_info.get('product_name', 'our solution')
                    greeting = greeting.replace("[PRODUCT]", product_name)
                
                logger.info(f"Using agent's sales script for greeting: {agent.name}")
                
            else:
                # Fallback to default greetings
                greetings = [
                    f"Hello {customer_name}, this is {agent.name}. Thank you for your interest in our AI solutions. How can I help you today?",
                    f"Hi {customer_name}, {agent.name} here. I'm excited to discuss how our AI agents can benefit your business. What would you like to know?",
                    f"Good day {customer_name}, this is {agent.name} from AI Voice Solutions. I'm here to answer any questions about our voice AI technology."
                ]
                
                import random
                greeting = random.choice(greetings)
                logger.info(f"Using default greeting for agent {agent.name} - no sales script found")
            
            import random
            greeting = random.choice(greetings)
            
            # Store initial interaction for learning
            store_conversation_for_learning(call_session, agent, "call_started", greeting, {"greeting": True})
            
            return self.create_voice_response(greeting, call_session)
            
        except Exception as e:
            logger.error(f"Agent greeting error: {str(e)}")
            return create_default_voice_response(agent)
    
    def create_voice_response(self, text, call_session):
        """Create Twilio voice response with speech gathering"""
        try:
            response = VoiceResponse()
            
            # Speak the response
            response.say(text, voice='alice', rate='medium')
            
            # Gather customer response
            gather = response.gather(
                input='speech',
                timeout=10,
                action='/api/calls/auto-voice-webhook/',
                method='POST',
                speech_timeout='auto'
            )
            
            # Add fallback if no response
            response.say("I didn't hear anything. Please call back when you're ready to chat!", voice='alice')
            response.hangup()
            
            return Response(str(response), content_type='text/xml')
            
        except Exception as e:
            logger.error(f"Voice response creation error: {str(e)}")
            return create_fallback_voice_response()