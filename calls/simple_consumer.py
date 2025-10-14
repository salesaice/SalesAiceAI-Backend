import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SimpleCallsConsumer(AsyncWebsocketConsumer):
    """Simplified WebSocket consumer for testing"""
    
    async def connect(self):
        """Accept all connections for testing"""
        try:
            # Get token from query string
            query_string = self.scope['query_string'].decode()
            query_params = parse_qs(query_string)
            token = query_params.get('token', [None])[0]
            
            if token:
                # Try to validate token
                try:
                    self.user = await self.get_user_from_token(token)
                    if self.user:
                        logger.info(f"User {self.user.email} connected to WebSocket")
                    else:
                        logger.warning("Invalid token provided")
                        self.user = None
                except Exception as e:
                    logger.error(f"Token validation error: {e}")
                    self.user = None
            else:
                logger.warning("No token provided")
                self.user = None
            
            # Accept connection regardless of auth status for testing
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to calls WebSocket',
                'authenticated': self.user is not None,
                'user_id': str(self.user.id) if self.user else None,
                'user_role': self.user.role if self.user else None
            }))
            
            logger.info("WebSocket connection established")
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'connection_error',
                'message': f'Connection error: {str(e)}'
            }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect"""
        logger.info(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')
            
            logger.info(f"Received WebSocket message: {message_type}")
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp'),
                    'message': 'Pong received!'
                }))
            else:
                # Echo the message back
                await self.send(text_data=json.dumps({
                    'type': 'echo',
                    'original_message': data,
                    'server_timestamp': json.loads(json.dumps({}, default=str))
                }))
                
        except json.JSONDecodeError as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Invalid JSON: {str(e)}'
            }))
        except Exception as e:
            logger.error(f"Receive error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Server error: {str(e)}'
            }))

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get user from JWT token"""
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
            return user
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return None