import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import DenyConnection
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CallsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Connect to the WebSocket
        """
        # Get the user from JWT token
        try:
            token = self.get_token_from_query()
            if not token:
                logger.error("No token provided in WebSocket connection")
                await self.close(code=4001)
                return
                
            self.user = await self.get_user_from_token(token)
            
            if not self.user:
                logger.error("Invalid token or user not found")
                await self.close(code=4001)
                return
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await self.close(code=4001)
            return

        # Join user-specific group
        self.user_group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # Join role-based groups
        if self.user.role == 'admin':
            self.admin_group_name = 'admin_calls'
            await self.channel_layer.group_add(
                self.admin_group_name,
                self.channel_name
            )
        elif self.user.role == 'agent':
            self.agent_group_name = 'agent_calls'
            await self.channel_layer.group_add(
                self.agent_group_name,
                self.channel_name
            )
        
        # Join general calls group for broadcasting
        self.calls_group_name = 'calls_updates'
        await self.channel_layer.group_add(
            self.calls_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to calls WebSocket',
            'user_id': self.user.id,
            'user_role': self.user.role
        }))

    async def disconnect(self, close_code):
        """
        Disconnect from the WebSocket
        """
        # Leave groups
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'admin_group_name'):
            await self.channel_layer.group_discard(
                self.admin_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'agent_group_name'):
            await self.channel_layer.group_discard(
                self.agent_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'calls_group_name'):
            await self.channel_layer.group_discard(
                self.calls_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
            
            elif message_type == 'subscribe_to_call':
                call_id = text_data_json.get('call_id')
                if call_id:
                    # Join call-specific group
                    call_group = f'call_{call_id}'
                    await self.channel_layer.group_add(
                        call_group,
                        self.channel_name
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'subscribed_to_call',
                        'call_id': call_id
                    }))
            
            elif message_type == 'unsubscribe_from_call':
                call_id = text_data_json.get('call_id')
                if call_id:
                    # Leave call-specific group
                    call_group = f'call_{call_id}'
                    await self.channel_layer.group_discard(
                        call_group,
                        self.channel_name
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'unsubscribed_from_call',
                        'call_id': call_id
                    }))
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON data'
            }))

    # Broadcast message handlers
    async def call_status_update(self, event):
        """Send call status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'call_status_update',
            'data': event['data']
        }))
    
    async def call_created(self, event):
        """Send new call notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'call_created',
            'data': event['data']
        }))
    
    async def call_ended(self, event):
        """Send call ended notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'call_ended',
            'data': event['data']
        }))
    
    async def call_queue_update(self, event):
        """Send call queue update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'call_queue_update',
            'data': event['data']
        }))
    
    async def agent_status_update(self, event):
        """Send agent status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'agent_status_update',
            'data': event['data']
        }))
    
    async def transcript_update(self, event):
        """Send real-time transcript update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'transcript_update',
            'data': event['data']
        }))
    
    async def emotion_update(self, event):
        """Send real-time emotion update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'emotion_update', 
            'data': event['data']
        }))
    
    async def call_data_update(self, event):
        """Send complete call data update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'call_data_update',
            'data': event['data']
        }))
    
    async def live_call_update(self, event):
        """Send live call updates during active call"""
        await self.send(text_data=json.dumps({
            'type': 'live_call_update',
            'data': event['data']
        }))

    def get_token_from_query(self):
        """Extract JWT token from query string"""
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if not token:
            raise DenyConnection("No token provided")
        
        return token

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get user from JWT token"""
        try:
            # Validate the token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            # Get the user
            user = User.objects.get(id=user_id)
            return user
            
        except (InvalidToken, TokenError, User.DoesNotExist) as e:
            logger.error(f"Token validation error: {e}")
            return None