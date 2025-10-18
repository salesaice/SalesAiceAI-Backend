"""
WebSocket Consumer for real-time audio streaming
Handles bidirectional audio between Twilio and HumeAI
"""

import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import TwilioCall, ConversationLog
from .services import HumeAIService

logger = logging.getLogger(__name__)


class HumeTwilioStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming audio between Twilio and HumeAI
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Accept connection
            await self.accept()
            
            logger.info("WebSocket connection established")
            
            # Initialize variables
            self.call_sid = None
            self.call = None
            self.hume_service = HumeAIService()
            self.hume_session = None
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"WebSocket disconnected with code: {close_code}")
        
        # Clean up HumeAI session
        if self.hume_session:
            # Close HumeAI session
            pass
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Receive data from Twilio
        """
        try:
            if text_data:
                data = json.loads(text_data)
                event_type = data.get('event')
                
                if event_type == 'start':
                    await self.handle_start(data)
                elif event_type == 'media':
                    await self.handle_media(data)
                elif event_type == 'stop':
                    await self.handle_stop(data)
            
        except Exception as e:
            logger.error(f"WebSocket receive error: {str(e)}")
    
    async def handle_start(self, data):
        """Handle stream start event"""
        try:
            # Get call information
            self.call_sid = data.get('start', {}).get('callSid')
            
            if self.call_sid:
                # Find call in database
                from channels.db import database_sync_to_async
                
                @database_sync_to_async
                def get_call():
                    return TwilioCall.objects.filter(call_sid=self.call_sid).first()
                
                self.call = await get_call()
                
                if self.call and self.call.agent:
                    # Create HumeAI session
                    self.hume_session = await self.hume_service.create_session(self.call.agent)
                    logger.info(f"HumeAI session created for call: {self.call_sid}")
        
        except Exception as e:
            logger.error(f"Handle start error: {str(e)}")
    
    async def handle_media(self, data):
        """Handle audio media from Twilio"""
        try:
            # Get audio payload
            media = data.get('media', {})
            payload = media.get('payload')  # Base64 encoded audio
            
            if payload and self.hume_session:
                # Send audio to HumeAI for processing
                # This is where you'd integrate with HumeAI's audio streaming API
                
                # For now, we'll just log it
                logger.debug(f"Received audio chunk for call: {self.call_sid}")
                
                # HumeAI will process the audio and return:
                # 1. Transcription
                # 2. Emotion analysis
                # 3. AI response
                
                # You would then send the AI response back to Twilio
                # await self.send_audio_to_twilio(ai_response_audio)
        
        except Exception as e:
            logger.error(f"Handle media error: {str(e)}")
    
    async def handle_stop(self, data):
        """Handle stream stop event"""
        try:
            logger.info(f"Stream stopped for call: {self.call_sid}")
            
            # Update call status
            if self.call:
                from channels.db import database_sync_to_async
                
                @database_sync_to_async
                def update_call():
                    self.call.status = 'completed'
                    self.call.save()
                
                await update_call()
        
        except Exception as e:
            logger.error(f"Handle stop error: {str(e)}")
    
    async def send_audio_to_twilio(self, audio_data):
        """Send audio data to Twilio"""
        try:
            message = {
                'event': 'media',
                'media': {
                    'payload': audio_data  # Base64 encoded audio
                }
            }
            
            await self.send(text_data=json.dumps(message))
        
        except Exception as e:
            logger.error(f"Send audio error: {str(e)}")
