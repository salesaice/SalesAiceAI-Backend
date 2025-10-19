"""
Complete HumeAI EVI Integration for Twilio
Real-time bidirectional audio streaming
"""

import json
import base64
import asyncio
import logging
import websockets
import audioop  # For audio format conversion
from typing import Optional
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class HumeTwilioRealTimeConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that bridges Twilio and HumeAI EVI
    Handles real-time bidirectional audio streaming
    """
    
    def convert_mulaw_to_linear16(self, mulaw_b64: str) -> str:
        """Convert µ-law audio from Twilio to linear16 PCM for HumeAI"""
        try:
            # Decode base64 µ-law audio
            mulaw_data = base64.b64decode(mulaw_b64)
            
            # Convert µ-law to linear16 PCM
            linear_data = audioop.ulaw2lin(mulaw_data, 2)  # 2 bytes per sample (16-bit)
            
            # Encode back to base64
            linear_b64 = base64.b64encode(linear_data).decode('utf-8')
            
            return linear_b64
        except Exception as e:
            logger.error(f"❌ Audio conversion error: {e}")
            return mulaw_b64  # Return original if conversion fails
    
    def convert_linear16_to_mulaw(self, linear_b64: str) -> str:
        """Convert linear16 PCM from HumeAI to µ-law for Twilio"""
        try:
            # Decode base64 linear16 audio
            linear_data = base64.b64decode(linear_b64)
            
            # Convert linear16 PCM to µ-law
            mulaw_data = audioop.lin2ulaw(linear_data, 2)  # 2 bytes per sample (16-bit)
            
            # Encode back to base64
            mulaw_b64 = base64.b64encode(mulaw_data).decode('utf-8')
            
            return mulaw_b64
        except Exception as e:
            logger.error(f"❌ Audio conversion error: {e}")
            return linear_b64  # Return original if conversion fails

    async def connect(self):
        """Accept WebSocket connection from Twilio"""
        await self.accept()
        
        # Initialize connection state
        self.call_sid = None
        self.stream_sid = None
        self.hume_ws = None
        self.hume_connected = False
        
        logger.info(f"📱 WebSocket connection established")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"WebSocket disconnected: {close_code}")
        
        # Close HumeAI connection if open
        if self.hume_ws and not self.hume_ws.closed:
            await self.hume_ws.close()
            logger.info(f"🔌 HumeAI connection closed")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages from Twilio"""
        try:
            data = json.loads(text_data)
            event = data.get('event')
            
            if event == 'connected':
                await self.handle_connected(data)
            elif event == 'start':
                await self.handle_start(data)
            elif event == 'media':
                await self.handle_media(data)
            elif event == 'stop':
                await self.handle_stop(data)
            else:
                logger.warning(f"⚠️ Unknown event: {event}")
                
        except Exception as e:
            logger.error(f"❌ Receive error: {str(e)}")

    async def handle_connected(self, data):
        """Handle Twilio connection event"""
        logger.info(f"📞 Twilio connected: {data}")

    async def handle_start(self, data):
        """Handle stream start and connect to HumeAI"""
        try:
            # Extract stream info
            stream_data = data.get('start', {})
            self.call_sid = stream_data.get('callSid')
            self.stream_sid = stream_data.get('streamSid')
            
            logger.info(f"✅ Twilio WebSocket connected for call: {self.call_sid}")
            logger.info(f"📞 Stream started: {self.stream_sid}")
            
            # Connect to HumeAI
            await self.connect_to_hume()
            
        except Exception as e:
            logger.error(f"❌ Handle start error: {str(e)}")

    async def connect_to_hume(self):
        """Establish connection to HumeAI EVI"""
        try:
            from decouple import config
            
            # Get credentials from environment
            hume_api_key = config('HUME_AI_API_KEY', default=config('HUME_API_KEY', default=''))
            hume_secret_key = config('HUME_AI_SECRET_KEY', default=config('HUME_SECRET_KEY', default=''))
            config_id = config('HUME_CONFIG_ID')
            
            logger.info(f"🔧 Using HumeAI Config ID: {config_id}")
            
            if not hume_api_key:
                logger.error("❌ HUME_API_KEY is empty!")
                return
            if not hume_secret_key:
                logger.error("❌ HUME_SECRET_KEY is empty!")
                return
            if not config_id:
                logger.error("❌ HUME_CONFIG_ID is empty!")
                return
            
            logger.info(f"🔑 API Key: {hume_api_key[:20]}...")
            logger.info(f"🔑 Secret Key: {hume_secret_key[:20]}...")
            logger.info(f"🔑 Config ID: {config_id}")
            
            # Connect to HumeAI EVI
            logger.info(f"🔌 Connecting to HumeAI EVI...")
            hume_url = f"wss://api.hume.ai/v0/evi/chat?api_key={hume_api_key}&config_id={config_id}"
            logger.info(f"🌐 URL: {hume_url[:80]}...")
            
            # Add authentication headers
            headers = {
                'Authorization': f'Bearer {hume_secret_key}',
                'Content-Type': 'application/json'
            }
            
            self.hume_ws = await asyncio.wait_for(
                websockets.connect(hume_url, extra_headers=headers, ping_interval=20, ping_timeout=20),
                timeout=10.0
            )
            
            self.hume_connected = True
            logger.info(f"✅ HumeAI WebSocket connected successfully!")
            logger.info(f"✅ Ready for call: {self.call_sid}")
            
            # Send initial session configuration to HumeAI with audio settings
            session_config = {
                "type": "session_settings",
                "config_id": config_id,
                "audio": {
                    "encoding": "linear16",
                    "channels": 1,
                    "sample_rate": 8000  # Twilio µ-law sample rate
                }
            }
            await self.hume_ws.send(json.dumps(session_config))
            logger.info(f"📤 Sent session config to HumeAI with audio settings")
            
            # Start listening to HumeAI responses
            asyncio.create_task(self.listen_to_hume())
            
        except asyncio.TimeoutError:
            logger.error(f"❌ HumeAI connection timeout after 10 seconds")
            logger.error(f"   Check: 1) Internet connection 2) API credentials 3) HumeAI service status")
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"❌ HumeAI rejected connection: HTTP {e.status_code}")
            logger.error(f"   Check API credentials and config ID")
        except Exception as e:
            logger.error(f"❌ HumeAI connection error: {type(e).__name__}: {str(e)}")
            
            # Handle specific missing agent error
            if "agent" in str(e).lower() and config_id:
                logger.error(f"   → Config ID not found: {config_id}")
        except Exception as e:
            logger.error(f"❌ Handle start error: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def handle_media(self, data):
        """Forward audio from Twilio to HumeAI"""
        try:
            if not self.hume_connected or not self.hume_ws:
                logger.warning(f"⚠️ Media received but HumeAI not connected")
                return
            
            # Extract audio payload from Twilio
            media = data.get('media', {})
            payload = media.get('payload')  # Base64 µ-law audio
            
            if not payload:
                return
            
            # Log first audio chunk
            if not hasattr(self, '_first_audio_logged'):
                logger.info(f"🎤 Receiving audio from Twilio (µ-law payload length: {len(payload)})")
                self._first_audio_logged = True
            
            # Convert µ-law to linear16 PCM for HumeAI
            linear_payload = self.convert_mulaw_to_linear16(payload)
            
            # Send converted audio to HumeAI
            hume_message = {
                "type": "audio_input",
                "data": linear_payload
            }
            
            await self.hume_ws.send(json.dumps(hume_message))
            
            # Log occasionally
            if not hasattr(self, '_audio_count'):
                self._audio_count = 0
            self._audio_count += 1
            
            if self._audio_count % 50 == 0:
                logger.info(f"📡 Sent {self._audio_count} audio chunks to HumeAI")
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"❌ HumeAI connection closed: {e.code} - {e.reason}")
            self.hume_connected = False
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
            logger.info(f"👂 Started listening to HumeAI responses...")
            async for message in self.hume_ws:
                data = json.loads(message)
                
                # Check message type
                msg_type = data.get('type')
                logger.info(f"📨 Received from HumeAI: {msg_type}")
                
                if msg_type == 'audio_output':
                    # Get audio from HumeAI
                    audio_data = data.get('data')  # Base64 audio
                    logger.info(f"🔊 Received audio from HumeAI ({len(audio_data) if audio_data else 0} bytes)")
                    
                    # Send to Twilio
                    await self.send_to_twilio(audio_data)
                
                elif msg_type == 'user_message':
                    # Log transcription
                    transcript = data.get('text')
                    logger.info(f"👤 User said: {transcript}")
                
                elif msg_type == 'assistant_message':
                    # Log AI response
                    response = data.get('text')
                    logger.info(f"🤖 AI responds: {response}")
                
                elif msg_type == 'emotion_scores':
                    # Log emotions
                    emotions = data.get('emotions', {})
                    logger.info(f"😊 Emotions: {emotions}")
                
                elif msg_type == 'error':
                    # Log HumeAI error details
                    error_msg = data.get('message', 'Unknown error')
                    error_code = data.get('code', 'N/A')
                    logger.error(f"❌ HumeAI Error [{error_code}]: {error_msg}")
                    logger.error(f"   Full error data: {data}")
                
                else:
                    # Log unknown message types
                    logger.warning(f"⚠️ Unknown HumeAI message type: {msg_type}")
                    logger.debug(f"   Message data: {data}")
                
        except Exception as e:
            logger.error(f"❌ Listen to HumeAI error: {str(e)}")
    
    async def send_to_twilio(self, audio_base64: str):
        """Send audio from HumeAI back to Twilio"""
        try:
            # Convert linear16 PCM from HumeAI to µ-law for Twilio
            mulaw_payload = self.convert_linear16_to_mulaw(audio_base64)
            
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": mulaw_payload
                }
            }
            
            await self.send(text_data=json.dumps(message))
            logger.info(f"📤 Sent audio to Twilio (converted to µ-law)")
            
        except Exception as e:
            logger.error(f"❌ Send to Twilio error: {str(e)}")