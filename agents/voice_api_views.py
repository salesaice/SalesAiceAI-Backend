"""
Voice Response API Endpoints
Agent voice responses ke liye API endpoints
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

from .voice_response_system import (
    AgentVoiceResponseSystem,
    get_agent_voice_response,
    setup_agent_voice,
    test_agent_voice
)
from .models import Agent

logger = logging.getLogger(__name__)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['agent_id', 'customer_message'],
        properties={
            'agent_id': openapi.Schema(type=openapi.TYPE_STRING, description='Agent UUID'),
            'customer_message': openapi.Schema(type=openapi.TYPE_STRING, description='Customer ka message'),
            'context': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Additional context for response generation',
                properties={
                    'product_interest': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'pricing_question': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'service_inquiry': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'customer_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'call_type': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        }
    ),
    responses={
        200: openapi.Response(
            description='Voice response generated successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'text_response': openapi.Schema(type=openapi.TYPE_STRING),
                    'voice_output': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'emotion_detected': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'response_strategy': openapi.Schema(type=openapi.TYPE_STRING),
                    'agent_voice_settings': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    operation_description="Generate voice response for customer message",
    tags=['Agent Voice System']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_agent_voice_response(request):
    """
    Customer message ke liye agent voice response generate karta hai
    
    Example usage:
    {
        \"agent_id\": \"uuid-here\",
        \"customer_message\": \"Hello, I'm interested in your product\",
        \"context\": {
            \"product_interest\": true,
            \"customer_name\": \"John\"
        }
    }
    """
    try:
        agent_id = request.data.get('agent_id')
        customer_message = request.data.get('customer_message')
        context = request.data.get('context', {})
        
        if not agent_id or not customer_message:
            return Response({
                'error': 'Missing required fields',
                'required': ['agent_id', 'customer_message']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if agent exists and belongs to user
        try:
            agent = Agent.objects.get(id=agent_id, user=request.user)
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if agent is active
        if agent.status != 'active':
            return Response({
                'error': 'Agent is not active',
                'agent_status': agent.status,
                'message': 'Agent must be active to generate voice responses'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate voice response
        voice_response = get_agent_voice_response(agent_id, customer_message, context)
        
        if voice_response['success']:
            return Response({
                'success': True,
                'agent_name': agent.name,
                'agent_voice_tone': agent.voice_tone,
                'response_data': voice_response,
                'message': 'Voice response generated successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': voice_response.get('error'),
                'fallback_response': voice_response.get('fallback_response')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Voice response API error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['agent_id'],
        properties={
            'agent_id': openapi.Schema(type=openapi.TYPE_STRING, description='Agent UUID'),
            'voice_settings': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Voice settings to update',
                properties={
                    'voice_tone': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        enum=['friendly', 'professional', 'enthusiastic', 'calm', 'confident'],
                        description='Voice tone'
                    ),
                    'voice_model': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        enum=['en-US-female-1', 'en-US-male-1', 'en-US-female-2', 'en-US-male-2'],
                        description='Voice model'
                    ),
                    'tone_settings': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        description='Custom tone settings',
                        properties={
                            'speaking_speed': openapi.Schema(type=openapi.TYPE_STRING),
                            'emotion_level': openapi.Schema(type=openapi.TYPE_STRING),
                            'formality': openapi.Schema(type=openapi.TYPE_STRING)
                        }
                    )
                }
            )
        }
    ),
    responses={
        200: openapi.Response(
            description='Voice settings updated successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'updated_settings': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    operation_description="Update agent voice settings",
    tags=['Agent Voice System']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_agent_voice_settings(request):
    """
    Agent ke voice settings update karta hai
    
    Example usage:
    {
        \"agent_id\": \"uuid-here\",
        \"voice_settings\": {
            \"voice_tone\": \"professional\",
            \"voice_model\": \"en-US-female-1\",
            \"tone_settings\": {
                \"speaking_speed\": \"normal\",
                \"emotion_level\": \"moderate\"
            }
        }
    }
    """
    try:
        agent_id = request.data.get('agent_id')
        voice_settings = request.data.get('voice_settings', {})
        
        if not agent_id:
            return Response({
                'error': 'Missing agent_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if agent exists and belongs to user
        try:
            agent = Agent.objects.get(id=agent_id, user=request.user)
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update voice settings
        update_result = setup_agent_voice(agent_id, voice_settings)
        
        if update_result['success']:
            return Response({
                'success': True,
                'agent_name': agent.name,
                'updated_settings': update_result['updated_settings'],
                'message': 'Voice settings updated successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': update_result.get('error')
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Voice settings update API error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['agent_id'],
        properties={
            'agent_id': openapi.Schema(type=openapi.TYPE_STRING, description='Agent UUID'),
            'test_message': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Test message to speak (optional)',
                default='Hello! This is a voice test from your AI agent.'
            )
        }
    ),
    responses={
        200: openapi.Response(
            description='Voice test completed',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'test_result': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    operation_description="Test agent voice output",
    tags=['Agent Voice System']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_agent_voice_output(request):
    """
    Agent ki voice test karta hai
    
    Example usage:
    {
        \"agent_id\": \"uuid-here\",
        \"test_message\": \"Hello! This is a custom test message.\"
    }
    """
    try:
        agent_id = request.data.get('agent_id')
        test_message = request.data.get('test_message', 'Hello! This is a voice test from your AI agent.')
        
        if not agent_id:
            return Response({
                'error': 'Missing agent_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if agent exists and belongs to user
        try:
            agent = Agent.objects.get(id=agent_id, user=request.user)
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Test voice output
        test_result = test_agent_voice(agent_id, test_message)
        
        if test_result['success']:
            return Response({
                'success': True,
                'agent_name': agent.name,
                'agent_voice_tone': agent.voice_tone,
                'test_result': test_result,
                'message': 'Voice test completed successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': test_result.get('error'),
                'agent_name': agent.name
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Voice test API error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='Agent voice settings retrieved',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'agent_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'agent_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'voice_settings': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'available_options': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    operation_description="Get agent voice settings and available options",
    tags=['Agent Voice System']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_agent_voice_settings(request, agent_id):
    """
    Agent ke current voice settings get karta hai
    
    URL: /api/agents/{agent_id}/voice-settings/
    """
    try:
        # Check if agent exists and belongs to user
        try:
            agent = Agent.objects.get(id=agent_id, user=request.user)
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get current voice settings
        current_settings = {
            'voice_model': getattr(agent, 'voice_model', 'en-US-female-1'),
            'voice_tone': getattr(agent, 'voice_tone', 'friendly'),
            'tone_settings': getattr(agent, 'tone_settings', {})
        }
        
        # Available options
        available_options = {
            'voice_tones': ['friendly', 'professional', 'enthusiastic', 'calm', 'confident'],
            'voice_models': ['en-US-female-1', 'en-US-male-1', 'en-US-female-2', 'en-US-male-2'],
            'tone_settings_options': {
                'speaking_speed': ['slow', 'normal', 'fast'],
                'emotion_level': ['low', 'moderate', 'high'],
                'formality': ['casual', 'professional', 'formal']
            }
        }
        
        return Response({
            'success': True,
            'agent_id': str(agent.id),
            'agent_name': agent.name,
            'voice_settings': current_settings,
            'available_options': available_options,
            'message': 'Voice settings retrieved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get voice settings API error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['customer_message'],
        properties={
            'customer_message': openapi.Schema(type=openapi.TYPE_STRING, description='Customer message'),
            'context': openapi.Schema(type=openapi.TYPE_OBJECT, description='Call context')
        }
    ),
    responses={
        200: openapi.Response(
            description='Live conversation response',
            schema=openapi.Schema(type=openapi.TYPE_OBJECT)
        )
    },
    operation_description="Handle live conversation with voice response",
    tags=['Agent Voice System']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def live_voice_conversation(request, agent_id):
    """
    Live conversation handler with voice response
    Real-time conversation ke liye use karo
    
    URL: /api/agents/{agent_id}/live-conversation/
    """
    try:
        customer_message = request.data.get('customer_message')
        context = request.data.get('context', {})
        
        if not customer_message:
            return Response({
                'error': 'Missing customer_message'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if agent exists and belongs to user
        try:
            agent = Agent.objects.get(id=agent_id, user=request.user)
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if agent is active
        if agent.status != 'active':
            return Response({
                'error': 'Agent is not active for conversations'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate voice response
        voice_response = get_agent_voice_response(str(agent.id), customer_message, context)
        
        # Log conversation for learning
        try:
            conversation_log = {
                'agent_id': str(agent.id),
                'customer_message': customer_message,
                'agent_response': voice_response.get('text_response', ''),
                'emotion_detected': voice_response.get('emotion_detected', {}),
                'timestamp': voice_response.get('timestamp'),
                'success': voice_response.get('success', False)
            }
            logger.info(f"Live conversation logged: {conversation_log}")
        except Exception as log_error:
            logger.error(f"Conversation logging error: {str(log_error)}")
        
        return Response({
            'success': voice_response.get('success', False),
            'agent_name': agent.name,
            'conversation_data': {
                'customer_message': customer_message,
                'agent_response': voice_response.get('text_response', ''),
                'emotion_analysis': voice_response.get('emotion_detected', {}),
                'response_strategy': voice_response.get('response_strategy', ''),
                'voice_output_status': voice_response.get('voice_output', {}).get('status', 'unknown')
            },
            'agent_voice_settings': voice_response.get('agent_voice_settings', {}),
            'message': 'Live conversation processed'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Live conversation API error: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)