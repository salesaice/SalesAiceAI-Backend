from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope['type'] == 'websocket':
            # Get token from query string
            query_string = scope['query_string'].decode()
            query_params = parse_qs(query_string)
            token = query_params.get('token', [None])[0]

            if token:
                try:
                    # Validate token and get user
                    user = await self.get_user_from_token(token)
                    scope['user'] = user
                except Exception as e:
                    logger.error(f"JWT Auth error: {e}")
                    scope['user'] = AnonymousUser()
            else:
                scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)

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
            return AnonymousUser()


def JWTAuthMiddlewareStack(inner):
    """
    Convenience function to create the JWT auth middleware stack
    """
    return JWTAuthMiddleware(inner)