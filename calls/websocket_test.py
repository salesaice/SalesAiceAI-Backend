from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .broadcasting import calls_broadcaster
from .models import CallSession


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_websocket_broadcast(request):
    """
    Test endpoint to broadcast WebSocket messages
    """
    message_type = request.data.get('type', 'test')
    message_data = request.data.get('data', {})
    
    if message_type == 'call_created':
        # Get a sample call or create test data
        call_id = request.data.get('call_id')
        if call_id:
            try:
                call_session = CallSession.objects.get(id=call_id)
                calls_broadcaster.broadcast_call_created(
                    call_session,
                    user_id=request.user.id
                )
                return Response({'message': 'Call created broadcast sent'})
            except CallSession.DoesNotExist:
                return Response({'error': 'Call not found'}, status=status.HTTP_404_NOT_FOUND)
    
    elif message_type == 'queue_update':
        queue_data = {
            'action': 'test_queue_update',
            'call_id': message_data.get('call_id', 'test-123'),
            'phone_number': message_data.get('phone_number', '+1234567890'),
            'priority': message_data.get('priority', 'medium'),
            'position_in_queue': message_data.get('position', 1)
        }
        calls_broadcaster.broadcast_queue_update(queue_data)
        return Response({'message': 'Queue update broadcast sent'})
    
    elif message_type == 'agent_status':
        agent_data = {
            'agent_id': message_data.get('agent_id', '1'),
            'user_id': str(request.user.id),
            'status': message_data.get('status', 'available'),
            'current_call_id': message_data.get('call_id', None)
        }
        calls_broadcaster.broadcast_agent_status_update(agent_data)
        return Response({'message': 'Agent status broadcast sent'})
    
    else:
        return Response({
            'error': 'Invalid message type',
            'available_types': ['call_created', 'queue_update', 'agent_status']
        }, status=status.HTTP_400_BAD_REQUEST)