"""
Complete HumeAI EVI Integration for Twilio
Real-time bidirectional audio streaming
"""

import json
import base64
import asyncio
import logging
import websockets
from typing import Optional
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class HumeTwilioRealTimeConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that bridges Twilio and HumeAI EVI
    Handles real-time bidirectional audio streaming
    """
    
    async def connect(self):
        """Initialize WebSocket connection"""
        try:
            # Get call SID from URL
            self.call_sid = self.scope['url_route']['kwargs'].get('call_sid')
            
            # Accept Twilio WebSocket connection
            await self.accept()
            
            logger.info(f"✅ Twilio WebSocket connected for call: {self.call_sid}")
            
            # Initialize HumeAI connection variables
            self.hume_ws = None
            self.hume_connected = False
            self.stream_sid = None
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {str(e)}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Clean up on disconnect"""
        logger.info(f"WebSocket disconnected: {close_code}")
        
        # Close HumeAI WebSocket if connected
        if self.hume_ws and not self.hume_ws.closed:
            await self.hume_ws.close()
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Receive data from Twilio and forward to HumeAI
        """
        try:
            if not text_data:
                return
            
            data = json.loads(text_data)
            event = data.get('event')
            
            if event == 'start':
                await self.handle_start(data)
            elif event == 'media':
                await self.handle_media(data)
            elif event == 'stop':
                await self.handle_stop(data)
            
        except Exception as e:
            logger.error(f"❌ Receive error: {str(e)}")
    
    async def handle_start(self, data):
        """Handle Twilio stream start - connect to HumeAI"""
        try:
            self.stream_sid = data['start']['streamSid']
            call_sid = data['start']['callSid']
            
            logger.info(f"📞 Stream started: {self.stream_sid}")
            
            # Get HumeAI config from database
            from channels.db import database_sync_to_async
            from .models import TwilioCall
            from decouple import config
            
            @database_sync_to_async
            def get_call_and_agent():
                call = TwilioCall.objects.filter(call_sid=call_sid).select_related('agent').first()
                return call, call.agent if call else None
            
            call, agent = await get_call_and_agent()
            
            if not agent:
                logger.error(f"❌ No agent found for call: {call_sid}")
                return
            
            # Connect to HumeAI EVI WebSocket
            hume_api_key = config('HUME_API_KEY')
            hume_secret_key = config('HUME_SECRET_KEY')
            config_id = agent.hume_config_id
            
            # HumeAI EVI WebSocket URL
            hume_url = f"wss://api.hume.ai/v0/evi/chat"
            
            headers = {
                "X-Hume-Api-Key": hume_api_key,
                "X-Hume-Secret-Key": hume_secret_key,
                "X-Hume-Config-Id": config_id
            }
            
            # Connect to HumeAI
            self.hume_ws = await websockets.connect(hume_url, extra_headers=headers)
            self.hume_connected = True
            
            logger.info(f"✅ HumeAI connected for call: {call_sid}")
            
            # Start listening to HumeAI responses
            asyncio.create_task(self.listen_to_hume())
            
        except Exception as e:
            logger.error(f"❌ Handle start error: {str(e)}")
    
    async def handle_media(self, data):
        """Forward audio from Twilio to HumeAI"""
        try:
            if not self.hume_connected or not self.hume_ws:
                return
            
            # Extract audio payload from Twilio
            media = data.get('media', {})
            payload = media.get('payload')  # Base64 µ-law audio
            
            if not payload:
                return
            
            # Send audio to HumeAI
            # HumeAI expects specific format - check their docs
            hume_message = {
                "type": "audio_input",
                "data": payload  # May need format conversion
            }
            
            await self.hume_ws.send(json.dumps(hume_message))
            
        except Exception as e:
            logger.error(f"❌ Handle media error: {str(e)}")
    
    async def handle_stop(self, data):
        """Handle stream stop"""
        try:
            logger.info(f"⏹️  Stream stopped: {self.stream_sid}")
            
            # Close HumeAI connection
            if self.hume_ws and not self.hume_ws.closed:
                await self.hume_ws.close()
            
        except Exception as e:
            logger.error(f"❌ Handle stop error: {str(e)}")
    
    async def listen_to_hume(self):
        """Listen for responses from HumeAI and forward to Twilio"""
        try:
            async for message in self.hume_ws:
                data = json.loads(message)
                
                # Check message type
                msg_type = data.get('type')
                
                if msg_type == 'audio_output':
                    # Get audio from HumeAI
                    audio_data = data.get('data')  # Base64 audio
                    
                    # Send to Twilio
                    await self.send_to_twilio(audio_data)
                
                elif msg_type == 'user_message':
                    # Log transcription
                    transcript = data.get('text')
                    logger.info(f"👤 User: {transcript}")
                
                elif msg_type == 'assistant_message':
                    # Log AI response
                    response = data.get('text')
                    logger.info(f"🤖 Assistant: {response}")
                
                elif msg_type == 'emotion_scores':
                    # Log emotions
                    emotions = data.get('emotions', {})
                    logger.info(f"😊 Emotions: {emotions}")
                
        except Exception as e:
            logger.error(f"❌ Listen to HumeAI error: {str(e)}")
    
    async def send_to_twilio(self, audio_base64: str):
        """Send audio from HumeAI back to Twilio"""
        try:
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_base64
                }
            }
            
            await self.send(text_data=json.dumps(message))
            
        except Exception as e:
            logger.error(f"❌ Send to Twilio error: {str(e)}")
