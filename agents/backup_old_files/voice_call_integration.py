from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Agent
from .ai_agent_models import AIAgent, CustomerProfile
from .campaign_models import Campaign, CampaignContact, BusinessKnowledge
from .homeai_integration import HomeAIService
from .twilio_service import TwilioCallService
from calls.models import CallSession
import json

User = get_user_model()


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def agent_voice_configuration(request, agent_id):
    """
    Configure voice settings for AI agents using HomeAI API
    Voice tone, personality, and AI response configuration
    """
    user = request.user
    
    try:
        ai_agent = AIAgent.objects.get(id=agent_id, client=user)
    except AIAgent.DoesNotExist:
        return Response({'error': 'AI Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    
    homeai_service = HomeAIService()
    
    if request.method == 'GET':
        # Get current voice configuration
        voice_config = {
            'agent_id': str(ai_agent.id),
            'agent_name': ai_agent.name,
            'current_settings': {
                'voice_model': ai_agent.voice_model,
                'personality_type': ai_agent.personality_type,
                'response_speed': 'fast',
                'language': 'en-US'
            },
            'available_voices': [
                {'id': 'en-US-female-1', 'name': 'Sarah (Professional Female)', 'accent': 'American'},
                {'id': 'en-US-female-2', 'name': 'Emma (Friendly Female)', 'accent': 'American'},
                {'id': 'en-US-male-1', 'name': 'John (Professional Male)', 'accent': 'American'},
                {'id': 'en-US-male-2', 'name': 'Mike (Casual Male)', 'accent': 'American'},
                {'id': 'en-GB-female-1', 'name': 'Elizabeth (British Female)', 'accent': 'British'},
                {'id': 'en-GB-male-1', 'name': 'James (British Male)', 'accent': 'British'}
            ],
            'personality_options': [
                {'id': 'friendly', 'name': 'Friendly & Casual', 'description': 'Warm and approachable tone'},
                {'id': 'professional', 'name': 'Professional & Formal', 'description': 'Business-focused communication'},
                {'id': 'persuasive', 'name': 'Sales Focused', 'description': 'Compelling and convincing'},
                {'id': 'supportive', 'name': 'Customer Support', 'description': 'Helpful and patient'},
                {'id': 'custom', 'name': 'Custom Trained', 'description': 'Personalized configuration'}
            ],
            'homeai_status': 'connected' if homeai_service.api_key else 'not_configured'
        }
        
        return Response(voice_config, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Update voice configuration
        data = request.data
        
        # Update AI agent settings
        if 'voice_model' in data:
            ai_agent.voice_model = data['voice_model']
        
        if 'personality_type' in data:
            ai_agent.personality_type = data['personality_type']
        
        ai_agent.save()
        
        # Create/Update HomeAI persona
        agent_config = {
            'name': ai_agent.name,
            'personality_type': ai_agent.personality_type,
            'voice_model': ai_agent.voice_model,
            'conversation_style': data.get('conversation_style', 'conversational'),
            'business_knowledge': ai_agent.conversation_memory.get('business_knowledge', {}),
            'sales_script': ai_agent.sales_script
        }
        
        persona_result = homeai_service.create_agent_persona(agent_config)
        
        if persona_result:
            # Store HomeAI persona ID in agent memory
            ai_agent.conversation_memory['homeai_persona_id'] = persona_result.get('persona_id')
            ai_agent.save()
            
            return Response({
                'message': 'Voice configuration updated successfully',
                'homeai_persona_id': persona_result.get('persona_id'),
                'voice_model': ai_agent.voice_model,
                'personality_type': ai_agent.personality_type
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to configure HomeAI voice settings',
                'local_settings_updated': True
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def twilio_call_configuration(request, agent_id):
    """
    Configure Twilio calling settings for agents
    Phone number, recording, and call routing configuration
    """
    user = request.user
    
    try:
        # Try AI agent first
        try:
            agent = AIAgent.objects.get(id=agent_id, client=user)
            agent_type = 'ai'
        except AIAgent.DoesNotExist:
            # Try human agent
            agent = Agent.objects.get(id=agent_id, user=user)
            agent_type = 'human'
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    
    twilio_service = TwilioCallService()
    
    if request.method == 'GET':
        # Get current Twilio configuration
        twilio_config = {
            'agent_id': str(agent.id),
            'agent_name': agent.name if agent_type == 'ai' else agent.user.get_full_name(),
            'agent_type': agent_type,
            'call_settings': {
                'auto_answer_inbound': agent_type == 'ai',  # AI agents auto-answer
                'enable_call_recording': True,
                'call_timeout': 30,  # seconds
                'max_call_duration': 1800,  # 30 minutes
                'enable_voicemail': True,
                'caller_id_number': twilio_service.phone_number
            },
            'twilio_features': {
                'machine_detection': True,
                'call_screening': agent_type == 'human',
                'call_forwarding': agent_type == 'human',
                'conference_calls': False,
                'call_queuing': True
            },
            'phone_numbers': [
                {'number': twilio_service.phone_number, 'type': 'main', 'active': True}
            ],
            'twilio_status': 'connected' if twilio_service.client else 'not_configured'
        }
        
        return Response(twilio_config, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Update Twilio configuration
        data = request.data
        
        # Update agent-specific Twilio settings in conversation memory or agent profile
        twilio_settings = data.get('call_settings', {})
        
        if agent_type == 'ai':
            # Store Twilio settings in AI agent's conversation memory
            if 'twilio_settings' not in agent.conversation_memory:
                agent.conversation_memory['twilio_settings'] = {}
            
            agent.conversation_memory['twilio_settings'].update(twilio_settings)
            agent.save()
        else:
            # For human agents, you might want to store in a separate model
            # For now, we'll just acknowledge the update
            pass
        
        return Response({
            'message': 'Twilio call configuration updated successfully',
            'settings_applied': twilio_settings
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_agent_voice(request, agent_id):
    """
    Test agent voice configuration with HomeAI
    Sample conversation to test voice and personality
    """
    user = request.user
    
    try:
        ai_agent = AIAgent.objects.get(id=agent_id, client=user)
    except AIAgent.DoesNotExist:
        return Response({'error': 'AI Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    
    homeai_service = HomeAIService()
    
    test_message = request.data.get('test_message', 'Hello, this is a test of my voice and personality.')
    
    # Generate test response using HomeAI
    conversation_context = {
        'agent_id': str(ai_agent.id),
        'agent_name': ai_agent.name,
        'personality': ai_agent.personality_type,
        'voice_model': ai_agent.voice_model,
        'business_context': ai_agent.conversation_memory.get('business_knowledge', {}),
        'test_mode': True
    }
    
    try:
        response = homeai_service.generate_response(
            message=test_message,
            context=conversation_context
        )
        
        if response:
            return Response({
                'test_successful': True,
                'agent_response': response.get('text', ''),
                'voice_url': response.get('audio_url', ''),
                'personality_detected': response.get('personality_analysis', {}),
                'response_time_ms': response.get('processing_time', 0)
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'test_successful': False,
                'error': 'Failed to generate test response'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'test_successful': False,
            'error': f'HomeAI test failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_agent_call(request, agent_id):
    """
    Test agent calling capability with Twilio
    Make a test call to verify configuration
    """
    user = request.user
    
    try:
        # Try AI agent first
        try:
            agent = AIAgent.objects.get(id=agent_id, client=user)
            agent_type = 'ai'
        except AIAgent.DoesNotExist:
            agent = Agent.objects.get(id=agent_id, user=user)
            agent_type = 'human'
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    
    test_number = request.data.get('test_number')
    if not test_number:
        return Response({'error': 'Test phone number is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    twilio_service = TwilioCallService()
    
    # Configure test call settings
    agent_config = {
        'agent_id': str(agent.id),
        'agent_name': agent.name if agent_type == 'ai' else agent.user.get_full_name(),
        'agent_type': agent_type,
        'personality_type': agent.personality_type if agent_type == 'ai' else 'professional',
        'voice_model': agent.voice_model if agent_type == 'ai' else 'en-US-female-1',
        'test_mode': True
    }
    
    call_context = {
        'customer_name': 'Test Customer',
        'purpose': 'Configuration Test',
        'script': 'Hello, this is a test call to verify the agent configuration is working properly.',
        'test_call': True
    }
    
    try:
        call_result = twilio_service.initiate_call(
            to=test_number,
            agent_config=agent_config,
            call_context=call_context
        )
        
        if call_result.get('success'):
            # Create call session record
            call_session = CallSession.objects.create(
                user=user,
                agent=agent if agent_type == 'human' else None,
                call_type='outbound',
                caller_number=twilio_service.phone_number,
                callee_number=test_number,
                status='initiated',
                twilio_call_sid=call_result.get('call_sid'),
                notes='Test call for agent configuration'
            )
            
            return Response({
                'test_call_initiated': True,
                'call_sid': call_result.get('call_sid'),
                'call_session_id': str(call_session.id),
                'estimated_duration': '30 seconds',
                'message': f'Test call initiated to {test_number}'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'test_call_initiated': False,
                'error': call_result.get('error', 'Unknown error occurred')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'test_call_initiated': False,
            'error': f'Twilio test call failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_campaign_with_ai_voice(request):
    """
    Start campaign with integrated AI voice and Twilio calling
    Complete integration of HomeAI + Twilio for campaign execution
    """
    user = request.user
    data = request.data
    
    campaign_id = data.get('campaign_id')
    if not campaign_id:
        return Response({'error': 'Campaign ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        campaign = Campaign.objects.get(id=campaign_id, created_by=user)
    except Campaign.DoesNotExist:
        return Response({'error': 'Campaign not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get assigned AI agent
    if not campaign.assigned_agent_ai:
        return Response({'error': 'Campaign must have an AI agent assigned'}, status=status.HTTP_400_BAD_REQUEST)
    
    ai_agent = campaign.assigned_agent_ai
    homeai_service = HomeAIService()
    twilio_service = TwilioCallService()
    
    # Prepare AI agent configuration
    agent_config = {
        'agent_id': str(ai_agent.id),
        'agent_name': ai_agent.name,
        'personality_type': ai_agent.personality_type,
        'voice_model': ai_agent.voice_model,
        'homeai_persona_id': ai_agent.conversation_memory.get('homeai_persona_id'),
        'business_knowledge': ai_agent.conversation_memory.get('business_knowledge', {}),
        'sales_script': ai_agent.sales_script,
        'campaign_id': str(campaign.id)
    }
    
    # Get campaign contacts
    campaign_contacts = CampaignContact.objects.filter(
        campaign=campaign,
        call_status='pending'
    ).select_related('customer_profile')[:5]  # Start with first 5 contacts
    
    initiated_calls = []
    failed_calls = []
    
    for campaign_contact in campaign_contacts:
        customer = campaign_contact.customer_profile
        
        # Prepare call context with customer information
        call_context = {
            'customer_name': customer.name,
            'customer_phone': customer.phone_number,
            'customer_email': customer.email,
            'lead_status': customer.lead_status,
            'previous_notes': customer.notes,
            'campaign_name': campaign.name,
            'preferred_time': customer.contact_preferences.get('preferred_time', ''),
            'business_context': agent_config['business_knowledge']
        }
        
        try:
            # Initiate call using Twilio with HomeAI integration
            call_result = twilio_service.initiate_call(
                to=customer.phone_number,
                agent_config=agent_config,
                call_context=call_context
            )
            
            if call_result.get('success'):
                # Create call session
                call_session = CallSession.objects.create(
                    user=user,
                    call_type='outbound',
                    caller_number=twilio_service.phone_number,
                    callee_number=customer.phone_number,
                    caller_name=customer.name,
                    status='initiated',
                    twilio_call_sid=call_result.get('call_sid'),
                    notes=f'Campaign: {campaign.name}'
                )
                
                # Update campaign contact status
                campaign_contact.call_status = 'in_progress'
                campaign_contact.attempts_made += 1
                campaign_contact.last_attempt_at = timezone.now()
                campaign_contact.save()
                
                initiated_calls.append({
                    'customer_name': customer.name,
                    'phone_number': customer.phone_number,
                    'call_sid': call_result.get('call_sid'),
                    'call_session_id': str(call_session.id)
                })
            else:
                failed_calls.append({
                    'customer_name': customer.name,
                    'phone_number': customer.phone_number,
                    'error': call_result.get('error', 'Unknown error')
                })
                
                # Mark as failed
                campaign_contact.call_status = 'failed'
                campaign_contact.attempts_made += 1
                campaign_contact.last_attempt_at = timezone.now()
                campaign_contact.save()
                
        except Exception as e:
            failed_calls.append({
                'customer_name': customer.name,
                'phone_number': customer.phone_number,
                'error': str(e)
            })
    
    # Update campaign status
    if initiated_calls:
        campaign.status = 'active'
        if not campaign.started_at:
            campaign.started_at = timezone.now()
        campaign.contacts_called += len(initiated_calls)
        campaign.save()
    
    return Response({
        'campaign_started': len(initiated_calls) > 0,
        'campaign_id': str(campaign.id),
        'campaign_name': campaign.name,
        'ai_agent': ai_agent.name,
        'calls_initiated': len(initiated_calls),
        'calls_failed': len(failed_calls),
        'initiated_calls': initiated_calls,
        'failed_calls': failed_calls,
        'homeai_integrated': bool(agent_config.get('homeai_persona_id')),
        'twilio_integrated': bool(twilio_service.client)
    }, status=status.HTTP_200_OK)
