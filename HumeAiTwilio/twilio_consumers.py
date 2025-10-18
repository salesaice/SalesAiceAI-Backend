"""
🔄 TWILIO-HUMEAI WEBSOCKET BRIDGE
Real-time audio streaming between Twilio calls and HumeAI agents
"""

import json
import base64
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import websockets
from decouple import config

logger = logging.getLogger(__name__)

HUME_API_KEY = config('HUME_API_KEY', default='')


class TwilioHumeStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that bridges Twilio Media Streams with HumeAI EVI
    
    Flow:
    1. Twilio calls → sends audio via WebSocket
    2. This consumer receives Twilio audio
    3. Forwards to HumeAI EVI
    4. Receives HumeAI response
    5. Sends back to Twilio
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_sid = None
        self.hume_ws = None
        self.twilio_stream_sid = None
        self.agent = None
        self.call = None
        self.running = False
    
    async def connect(self):
        """Handle WebSocket connection from Twilio"""
        # Get call SID from URL
        self.call_sid = self.scope['url_route']['kwargs'].get('call_sid')
        
        logger.info(f"📞 Twilio stream connecting for call: {self.call_sid}")
        
        # Accept connection
        await self.accept()
        
        # Load agent and call from database
        await self.load_call_info()
        
        # Connect to HumeAI
        await self.connect_to_hume()
        
        logger.info(f"✅ Twilio-HumeAI bridge established for {self.call_sid}")
    
    async def disconnect(self, close_code):
        """Handle disconnection"""
        logger.info(f"📴 Disconnecting call {self.call_sid}")
        
        self.running = False
        
        # Close HumeAI connection
        if self.hume_ws:
            await self.hume_ws.close()
        
        # Update call status
        if self.call:
            from channels.db import database_sync_to_async
            await database_sync_to_async(self.update_call_status)('completed')
    
    async def receive(self, text_data):
        """Receive audio from Twilio and forward to HumeAI"""
        try:
            data = json.loads(text_data)
            event = data.get('event')
            
            if event == 'start':
                # Stream started
                self.twilio_stream_sid = data.get('streamSid')
                logger.info(f"📡 Twilio stream started: {self.twilio_stream_sid}")
            
            elif event == 'media':
                # Audio data from caller
                media = data.get('media', {})
                payload = media.get('payload')  # base64 encoded audio
                
                if payload and self.hume_ws:
                    # Forward to HumeAI
                    hume_message = {
                        'type': 'audio_input',
                        'data': payload
                    }
                    await self.hume_ws.send(json.dumps(hume_message))
            
            elif event == 'stop':
                # Stream stopped
                logger.info(f"⏹️ Twilio stream stopped: {self.twilio_stream_sid}")
                self.running = False
        
        except Exception as e:
            logger.error(f"❌ Error receiving Twilio data: {e}")
    
    async def load_call_info(self):
        """Load call and agent info from database"""
        from channels.db import database_sync_to_async
        from .models import TwilioCall
        
        @database_sync_to_async
        def get_call():
            try:
                call = TwilioCall.objects.select_related('agent').get(call_sid=self.call_sid)
                return call
            except TwilioCall.DoesNotExist:
                logger.warning(f"⚠️ Call {self.call_sid} not found in database")
                return None
        
        self.call = await get_call()
        if self.call:
            self.agent = self.call.agent
            logger.info(f"✅ Loaded agent: {self.agent.name}")
    
    async def connect_to_hume(self):
        """Establish WebSocket connection to HumeAI EVI"""
        if not self.agent:
            logger.error("❌ No agent found, cannot connect to HumeAI")
            return
        
        # Build HumeAI WebSocket URL
        hume_url = f"wss://api.hume.ai/v0/assistant/chat?apiKey={HUME_API_KEY}"
        
        if self.agent.hume_config_id:
            hume_url += f"&configId={self.agent.hume_config_id}"
        
        try:
            # Connect to HumeAI
            self.hume_ws = await websockets.connect(hume_url)
            logger.info(f"✅ Connected to HumeAI for agent: {self.agent.name}")
            
            # Send session settings
            session_settings = {
                'type': 'session_settings',
                'audio': {
                    'encoding': 'mulaw',  # Twilio uses mulaw encoding
                    'sample_rate': 8000,  # Twilio sample rate
                    'channels': 1
                }
            }
            await self.hume_ws.send(json.dumps(session_settings))
            
            # Start receiving from HumeAI
            self.running = True
            asyncio.create_task(self.receive_from_hume())
        
        except Exception as e:
            logger.error(f"❌ Failed to connect to HumeAI: {e}")
    
    async def receive_from_hume(self):
        """Receive responses from HumeAI and send to Twilio"""
        try:
            async for message in self.hume_ws:
                if not self.running:
                    break
                
                data = json.loads(message)
                msg_type = data.get('type')
                
                if msg_type == 'user_message':
                    # User's transcribed speech
                    content = data.get('message', {}).get('content', '')
                    logger.info(f"👤 User said: {content}")
                    await self.log_conversation('user', content)
                
                elif msg_type == 'assistant_message':
                    # Agent's text response
                    content = data.get('message', {}).get('content', '')
                    logger.info(f"🤖 Agent said: {content}")
                    await self.log_conversation('assistant', content)
                
                elif msg_type == 'audio_output':
                    # Agent's voice audio - send to Twilio
                    audio_data = data.get('data', '')
                    if audio_data:
                        # Send to Twilio
                        await self.send_audio_to_twilio(audio_data)
        
        except Exception as e:
            logger.error(f"❌ Error receiving from HumeAI: {e}")
    
    async def send_audio_to_twilio(self, audio_b64):
        """Send audio back to Twilio caller"""
        media_message = {
            'event': 'media',
            'streamSid': self.twilio_stream_sid,
            'media': {
                'payload': audio_b64
            }
        }
        await self.send(text_data=json.dumps(media_message))
    
    async def log_conversation(self, role, message):
        """Log conversation to database"""
        if not self.call:
            return
        
        from channels.db import database_sync_to_async
        from .models import ConversationLog
        from django.utils import timezone
        
        @database_sync_to_async
        def create_log():
            ConversationLog.objects.create(
                call=self.call,
                role=role,
                message=message,
                timestamp=timezone.now()
            )
        
        await create_log()
    
    def update_call_status(self, status):
        """Update call status in database (sync)"""
        if self.call:
            self.call.status = status
            self.call.save()
