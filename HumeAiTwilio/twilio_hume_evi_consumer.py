"""
COMPLETE WEBSOCKET IMPLEMENTATION
Real-time Twilio + HumeAI EVI Integration
"""

import json
import base64
import asyncio
import logging
import audioop
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import websockets
from decouple import config

logger = logging.getLogger(__name__)

# HumeAI Configuration - Support both variable names
HUME_AI_API_KEY = config('HUME_AI_API_KEY', default=config('HUME_API_KEY', default=''))
HUME_SECRET_KEY = config('HUME_SECRET_KEY', default='')


class TwilioHumeEVIConsumer(AsyncWebsocketConsumer):
    """
    Complete WebSocket bridge: Twilio ←→ HumeAI EVI
    Real-time voice conversation with emotion detection
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_sid = None
        self.stream_sid = None
        self.hume_ws = None
        self.agent = None
        self.call = None
        self.running = False
        self.audio_buffer = []
    
    async def connect(self):
        """Accept Twilio WebSocket connection"""
        self.call_sid = self.scope['url_route']['kwargs'].get('call_sid')
        
        logger.info(f"📞 Incoming Twilio stream for call: {self.call_sid}")
        
        # Accept WebSocket
        await self.accept()
        
        # Load call details
        await self.load_call_details()
        
        # Connect to HumeAI
        if self.agent:
            await self.connect_to_hume_evi()
        
        logger.info(f"✅ Bridge established: Twilio ←→ HumeAI EVI")
    
    async def disconnect(self, close_code):
        """Handle disconnection"""
        logger.info(f"📴 Disconnecting: {self.call_sid} (code: {close_code})")
        
        self.running = False
        
        # Close HumeAI
        if self.hume_ws:
            try:
                await self.hume_ws.close()
                logger.info("✅ HumeAI connection closed")
            except:
                pass
        
        # Update call status
        await self.update_call_status('completed')
    
    async def receive(self, text_data):
        """Receive messages from Twilio"""
        try:
            data = json.loads(text_data)
            event = data.get('event')
            
            if event == 'connected':
                logger.info("📞 Twilio call connected")
                await self.log_message('system', 'Call connected')
            
            elif event == 'start':
                start_data = data.get('start', {})
                self.stream_sid = start_data.get('streamSid')
                logger.info(f"🎙️  Stream started: {self.stream_sid}")
                await self.log_message('system', f'Stream: {self.stream_sid}')
            
            elif event == 'media':
                # Audio from caller (mulaw, base64 encoded)
                media = data.get('media', {})
                payload = media.get('payload')  # base64 string
                
                if payload and self.hume_ws and self.running:
                    # Forward to HumeAI
                    await self.send_audio_to_hume(payload)
            
            elif event == 'stop':
                logger.info(f"⏹️  Stream stopped: {self.stream_sid}")
                await self.log_message('system', 'Call ended')
                self.running = False
            
            elif event == 'mark':
                # Mark event (for timing)
                pass
            
        except Exception as e:
            logger.error(f"❌ Error receiving from Twilio: {e}")
            import traceback
            traceback.print_exc()
    
    @database_sync_to_async
    def load_call_details(self):
        """Load call and agent from database"""
        from .models import TwilioCall
        
        try:
            self.call = TwilioCall.objects.select_related('agent').get(
                twilio_call_sid=self.call_sid
            )
            self.agent = self.call.agent
            logger.info(f"✅ Agent loaded: {self.agent.name}")
        except TwilioCall.DoesNotExist:
            logger.warning(f"⚠️  Call not found: {self.call_sid}")
            self.call = None
            self.agent = None
    
    async def connect_to_hume_evi(self):
        """Connect to HumeAI EVI (Empathic Voice Interface)"""
        try:
            # HumeAI EVI WebSocket URL
            url = f"wss://api.hume.ai/v0/assistant/chat"
            
            # Headers
            headers = {
                "X-Hume-Api-Key": HUME_AI_API_KEY,
            }
            
            # Query params
            params = {
                "apiKey": HUME_AI_API_KEY,
            }
            
            if self.agent.hume_config_id:
                params["configId"] = self.agent.hume_config_id
            
            # Build URL with params
            param_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{param_string}"
            
            logger.info(f"🔌 Connecting to HumeAI EVI...")
            
            # Connect
            self.hume_ws = await websockets.connect(
                full_url,
                extra_headers=headers
            )
            
            logger.info("✅ Connected to HumeAI EVI")
            
            # Configure audio settings
            # HumeAI EVI requires linear16 encoding, not mulaw
            # We'll need to convert Twilio's mulaw to linear16
            config_msg = {
                "type": "session_settings",
                "audio": {
                    "encoding": "linear16",  # HumeAI requires linear16
                    "sample_rate": 8000,  # 8kHz sample rate
                    "channels": 1
                }
            }
            
            await self.hume_ws.send(json.dumps(config_msg))
            logger.info("✅ Audio settings configured (linear16, 8kHz)")
            
            # Start listening to HumeAI
            self.running = True
            asyncio.create_task(self.listen_to_hume())
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to HumeAI: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_audio_to_hume(self, audio_base64):
        """Send audio to HumeAI (convert mulaw to linear16)"""
        try:
            # Decode base64 mulaw audio from Twilio
            mulaw_data = base64.b64decode(audio_base64)
            
            # Convert mulaw to linear16 (PCM)
            linear_data = audioop.ulaw2lin(mulaw_data, 2)  # 2 = 16-bit samples
            
            # Encode back to base64
            linear_base64 = base64.b64encode(linear_data).decode('utf-8')
            
            # Send to HumeAI
            message = {
                "type": "audio_input",
                "data": linear_base64
            }
            await self.hume_ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"❌ Error sending audio to HumeAI: {e}")
    
    async def listen_to_hume(self):
        """Listen for responses from HumeAI"""
        try:
            async for message in self.hume_ws:
                if not self.running:
                    break
                
                await self.handle_hume_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 HumeAI connection closed")
        except Exception as e:
            logger.error(f"❌ Error listening to HumeAI: {e}")
            import traceback
            traceback.print_exc()
    
    async def handle_hume_message(self, message):
        """Handle messages from HumeAI EVI"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            logger.debug(f"📥 HumeAI message: {msg_type}")
            
            if msg_type == 'user_message':
                # User's transcribed speech
                msg_data = data.get('message', {})
                content = msg_data.get('content', '')
                
                logger.info(f"👤 User: {content}")
                await self.log_message('user', content)
            
            elif msg_type == 'assistant_message':
                # AI's text response
                msg_data = data.get('message', {})
                content = msg_data.get('content', '')
                
                logger.info(f"🤖 Agent: {content}")
                await self.log_message('agent', content)
            
            elif msg_type == 'audio_output':
                # AI's voice output - send to Twilio
                audio_data = data.get('data', '')
                
                if audio_data and self.stream_sid:
                    await self.send_audio_to_twilio(audio_data)
            
            elif msg_type == 'user_interruption':
                # User interrupted AI
                logger.info("🤚 User interrupted")
            
            elif msg_type == 'error':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"❌ HumeAI error: {error_msg}")
            
            else:
                # Other message types
                logger.debug(f"📨 HumeAI: {msg_type}")
                
        except Exception as e:
            logger.error(f"❌ Error handling HumeAI message: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_audio_to_twilio(self, audio_base64):
        """Send audio to Twilio caller (convert linear16 to mulaw)"""
        try:
            # Decode base64 linear16 audio from HumeAI
            linear_data = base64.b64decode(audio_base64)
            
            # Convert linear16 to mulaw for Twilio
            mulaw_data = audioop.lin2ulaw(linear_data, 2)  # 2 = 16-bit samples
            
            # Encode back to base64
            mulaw_base64 = base64.b64encode(mulaw_data).decode('utf-8')
            
            # Send to Twilio
            media_msg = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": mulaw_base64
                }
            }
            
            await self.send(text_data=json.dumps(media_msg))
            logger.debug(f"📤 Sent audio to Twilio")
            
        except Exception as e:
            logger.error(f"❌ Error sending to Twilio: {e}")
    
    @database_sync_to_async
    def log_message(self, speaker, message):
        """Log conversation to database"""
        from .models import ConversationLog
        
        try:
            if self.call:
                ConversationLog.objects.create(
                    call=self.call,
                    speaker=speaker,
                    message=message,
                    timestamp=0
                )
        except Exception as e:
            logger.error(f"⚠️  Error logging: {e}")
    
    @database_sync_to_async
    def update_call_status(self, status):
        """Update call status"""
        try:
            if self.call:
                self.call.status = status
                self.call.save()
                logger.info(f"✅ Call status updated: {status}")
        except Exception as e:
            logger.error(f"⚠️  Error updating status: {e}")
