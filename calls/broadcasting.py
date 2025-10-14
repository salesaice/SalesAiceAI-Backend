from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import logging

logger = logging.getLogger(__name__)


class CallsBroadcaster:
    """Utility class for broadcasting call-related updates via WebSocket"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def broadcast_call_created(self, call_session, user_id=None, agent_id=None):
        """Broadcast when a new call is created"""
        if not self.channel_layer:
            return
        
        call_data = {
            'id': str(call_session.id),
            'user_id': str(call_session.user.id) if call_session.user else None,
            'agent_id': str(call_session.agent.id) if call_session.agent else None,
            'status': call_session.status,
            'started_at': call_session.started_at.isoformat() if call_session.started_at else None,
            'phone_number': call_session.caller_number,  # Fixed: use caller_number field
            'call_type': call_session.call_type,
        }
        
        # Broadcast to general calls group
        async_to_sync(self.channel_layer.group_send)(
            'calls_updates',
            {
                'type': 'call_created',
                'data': call_data
            }
        )
        
        # Broadcast to admin group
        async_to_sync(self.channel_layer.group_send)(
            'admin_calls',
            {
                'type': 'call_created',
                'data': call_data
            }
        )
        
        # Broadcast to agent group
        async_to_sync(self.channel_layer.group_send)(
            'agent_calls',
            {
                'type': 'call_created',
                'data': call_data
            }
        )
        
        # Broadcast to specific user if provided
        if user_id:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{user_id}',
                {
                    'type': 'call_created',
                    'data': call_data
                }
            )
        
        # Broadcast to specific agent if provided
        if agent_id:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{agent_id}',
                {
                    'type': 'call_created',
                    'data': call_data
                }
            )
    
    def broadcast_call_status_update(self, call_session, user_id=None, agent_id=None):
        """Broadcast when call status is updated"""
        if not self.channel_layer:
            return
        
        call_data = {
            'id': str(call_session.id),
            'status': call_session.status,
            'updated_at': call_session.started_at.isoformat() if call_session.started_at else None,
            'duration': call_session.duration,
            'ended_at': call_session.ended_at.isoformat() if call_session.ended_at else None,
        }
        
        # Broadcast to call-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'call_{call_session.id}',
            {
                'type': 'call_status_update',
                'data': call_data
            }
        )
        
        # Broadcast to general calls group
        async_to_sync(self.channel_layer.group_send)(
            'calls_updates',
            {
                'type': 'call_status_update',
                'data': call_data
            }
        )
        
        # Broadcast to admin group
        async_to_sync(self.channel_layer.group_send)(
            'admin_calls',
            {
                'type': 'call_status_update',
                'data': call_data
            }
        )
        
        # Broadcast to specific user if provided
        if user_id:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{user_id}',
                {
                    'type': 'call_status_update',
                    'data': call_data
                }
            )
        
        # Broadcast to specific agent if provided
        if agent_id:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{agent_id}',
                {
                    'type': 'call_status_update',
                    'data': call_data
                }
            )
    
    def broadcast_call_ended(self, call_session, user_id=None, agent_id=None):
        """Broadcast when a call is ended"""
        if not self.channel_layer:
            return
        
        call_data = {
            'id': str(call_session.id),
            'status': call_session.status,
            'ended_at': call_session.ended_at.isoformat() if call_session.ended_at else None,
            'duration': call_session.duration,
            'call_summary': call_session.call_summary,
            'outcome': call_session.outcome,
        }
        
        # Broadcast to call-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'call_{call_session.id}',
            {
                'type': 'call_ended',
                'data': call_data
            }
        )
        
        # Broadcast to general calls group
        async_to_sync(self.channel_layer.group_send)(
            'calls_updates',
            {
                'type': 'call_ended',
                'data': call_data
            }
        )
        
        # Broadcast to admin group
        async_to_sync(self.channel_layer.group_send)(
            'admin_calls',
            {
                'type': 'call_ended',
                'data': call_data
            }
        )
        
        # Broadcast to specific user if provided
        if user_id:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{user_id}',
                {
                    'type': 'call_ended',
                    'data': call_data
                }
            )
        
        # Broadcast to specific agent if provided
        if agent_id:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{agent_id}',
                {
                    'type': 'call_ended',
                    'data': call_data
                }
            )
    
    def broadcast_queue_update(self, queue_data):
        """Broadcast call queue updates"""
        if not self.channel_layer:
            return
        
        # Broadcast to general calls group
        async_to_sync(self.channel_layer.group_send)(
            'calls_updates',
            {
                'type': 'call_queue_update',
                'data': queue_data
            }
        )
        
        # Broadcast to admin group
        async_to_sync(self.channel_layer.group_send)(
            'admin_calls',
            {
                'type': 'call_queue_update',
                'data': queue_data
            }
        )
        
        # Broadcast to agent group
        async_to_sync(self.channel_layer.group_send)(
            'agent_calls',
            {
                'type': 'call_queue_update',
                'data': queue_data
            }
        )
    
    def broadcast_agent_status_update(self, agent_data):
        """Broadcast agent status updates"""
        if not self.channel_layer:
            return
        
        # Broadcast to general calls group
        async_to_sync(self.channel_layer.group_send)(
            'calls_updates',
            {
                'type': 'agent_status_update',
                'data': agent_data
            }
        )
        
        # Broadcast to admin group
        async_to_sync(self.channel_layer.group_send)(
            'admin_calls',
            {
                'type': 'agent_status_update',
                'data': agent_data
            }
        )
        
        # Broadcast to specific agent
        async_to_sync(self.channel_layer.group_send)(
            f'user_{agent_data.get("agent_id")}',
            {
                'type': 'agent_status_update',
                'data': agent_data
            }
        )

    def broadcast_transcript_update(self, call_session, transcript_data):
        """Broadcast real-time transcript updates"""
        if not self.channel_layer:
            return
            
        # Broadcast to call-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'call_{call_session.id}',
            {
                'type': 'transcript_update',
                'data': transcript_data
            }
        )
        
        # Broadcast to user and agent
        if call_session.user:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{call_session.user.id}',
                {
                    'type': 'transcript_update', 
                    'data': transcript_data
                }
            )
            
        if call_session.agent:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{call_session.agent.owner.id}',
                {
                    'type': 'transcript_update',
                    'data': transcript_data  
                }
            )

    def broadcast_emotion_update(self, call_session, emotion_data):
        """Broadcast real-time emotion analysis updates"""
        if not self.channel_layer:
            return
            
        # Broadcast to call-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'call_{call_session.id}',
            {
                'type': 'emotion_update',
                'data': emotion_data
            }
        )
        
        # Broadcast to user and agent
        if call_session.user:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{call_session.user.id}',
                {
                    'type': 'emotion_update',
                    'data': emotion_data
                }
            )
            
        if call_session.agent:
            async_to_sync(self.channel_layer.group_send)(
                f'user_{call_session.agent.owner.id}',
                {
                    'type': 'emotion_update', 
                    'data': emotion_data
                }
            )

    def broadcast_call_data_complete(self, call_session, call_data):
        """Broadcast complete call data update"""
        if not self.channel_layer:
            return
            
        # Broadcast to general groups
        async_to_sync(self.channel_layer.group_send)(
            'calls_updates',
            {
                'type': 'call_data_update',
                'data': call_data
            }
        )
        
        # Broadcast to call-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'call_{call_session.id}',
            {
                'type': 'call_data_update',
                'data': call_data
            }
        )

    def broadcast_live_call_update(self, call_id, update_type, data):
        """Broadcast live updates during active call"""
        if not self.channel_layer:
            return
            
        update_data = {
            'call_id': str(call_id),
            'update_type': update_type,
            'data': data,
            'timestamp': data.get('timestamp') or None
        }
        
        # Broadcast to call-specific group
        async_to_sync(self.channel_layer.group_send)(
            f'call_{call_id}',
            {
                'type': 'live_call_update',
                'data': update_data
            }
        )


# Global instance
calls_broadcaster = CallsBroadcaster()