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
            
            # Twilio sends 8kHz, but HumeAI expects 16kHz - upsample
            linear_16khz = audioop.ratecv(linear_data, 2, 1, 8000, 16000, None)[0]
            
            # Encode back to base64
            linear_b64 = base64.b64encode(linear_16khz).decode('utf-8')
            
            return linear_b64
        except Exception as e:
            logger.error(f"❌ Audio conversion error: {e}")
            return mulaw_b64  # Return original if conversion fails
    
    def convert_linear16_to_mulaw(self, linear_b64: str) -> str:
        """Convert linear16 PCM from HumeAI to µ-law for Twilio"""
        try:
            # Decode base64 linear16 audio
            linear_data = base64.b64decode(linear_b64)
            
            # Log original data info
            logger.info(f"🔄 Converting audio: {len(linear_data)} bytes of linear16 data")
            
            # HumeAI might send different sample rate - try without conversion first
            # Then convert to µ-law directly
            mulaw_data = audioop.lin2ulaw(linear_data, 2)  # 2 bytes per sample (16-bit)
            
            # Encode back to base64
            mulaw_b64 = base64.b64encode(mulaw_data).decode('utf-8')
            
            logger.info(f"✅ Converted to µ-law: {len(mulaw_data)} bytes")
            return mulaw_b64
            
        except Exception as e:
            logger.error(f"❌ Audio conversion error: {e}")
            # Try returning original data as fallback
            logger.warning(f"⚠️ Returning original audio data as fallback")
            return linear_b64
    
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
            
            # Get HumeAI config - TEMPORARY: Hardcode for testing
            from channels.db import database_sync_to_async
            from .models import TwilioCall, HumeAgent
            from decouple import config
            
            # Get credentials from environment - Support both variable names
            hume_api_key = config('HUME_AI_API_KEY', default=config('HUME_API_KEY', default=''))
            hume_secret_key = config('HUME_AI_SECRET_KEY', default=config('HUME_SECRET_KEY', default=''))
            config_id = config('HUME_CONFIG_ID')  # Hardcoded from .env for now
            
            logger.info(f"🔧 Using HumeAI Config ID: {config_id}")
            
            # Try to get agent from database (for logging only)
            @database_sync_to_async
            def get_active_agent():
                agent = HumeAgent.objects.filter(status='active').first()
                return agent
            
            agent = await get_active_agent()
            if agent:
                logger.info(f"✅ Found agent in DB: {agent.name} (ID: {agent.hume_config_id})")
            else:
                logger.warning(f"⚠️  No agent in DB, using config from .env")
            
            # Connect to HumeAI EVI WebSocket
            # Use config_id from environment (already set above)
            
            # Validate credentials before connecting
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
            
            # HumeAI EVI WebSocket URL with API key as query parameter
            hume_url = f"wss://api.hume.ai/v0/evi/chat?api_key={hume_api_key}&config_id={config_id}"
            
            headers = {
                "X-Hume-Api-Key": hume_api_key,
                "X-Hume-Secret-Key": hume_secret_key,
            }
            
            logger.info(f"🔌 Connecting to HumeAI EVI...")
            logger.info(f"🌐 URL: wss://api.hume.ai/v0/evi/chat?api_key=...&config_id={config_id}")
            
            # Connect to HumeAI with timeout
            self.hume_ws = await asyncio.wait_for(
                websockets.connect(
                    hume_url,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=20
                ),
                timeout=10.0
            )
            self.hume_connected = True
            
            logger.info(f"✅ HumeAI WebSocket connected successfully!")
            logger.info(f"✅ Ready for call: {call_sid}")
            
            # Send initial session configuration to HumeAI with audio settings
            session_config = {
                "type": "session_settings",
                "config_id": config_id,
                "audio": {
                    "encoding": "linear16",
                    "channels": 1,
                    "sample_rate": 16000  # Try 16kHz instead of 8kHz
                }
            }
            await self.hume_ws.send(json.dumps(session_config))
            logger.info(f"📤 Sent session config to HumeAI with 16kHz audio settings")
            
            # Start listening to HumeAI responses
            asyncio.create_task(self.listen_to_hume())
            
        except asyncio.TimeoutError:
            logger.error(f"❌ HumeAI connection timeout after 10 seconds")
            logger.error(f"   Check: 1) Internet connection 2) API credentials 3) HumeAI service status")
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"❌ HumeAI rejected connection: HTTP {e.status_code}")
            if e.status_code == 401:
                logger.error(f"   → Invalid API Key or Secret Key")
            elif e.status_code == 403:
                logger.error(f"   → Access forbidden - check credentials")
            elif e.status_code == 404:
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
            if self._audio_count % 50 == 0:  # Every 50 chunks
                logger.info(f"📡 Sent {self._audio_count} audio chunks to HumeAI")
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"❌ HumeAI connection closed: {e.code} - {e.reason}")
        except Exception as e:
            logger.error(f"❌ Handle media error: {type(e).__name__}: {str(e)}")
    
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
                    # Skip audio output - using TTS instead
                    audio_data = data.get('data')
                    logger.info(f"🔊 Received audio from HumeAI ({len(audio_data) if audio_data else 0} bytes) - SKIPPING (using TTS)")
                    # Comment out audio sending
                    # await self.send_to_twilio(audio_data)
                
                elif msg_type == 'user_message':
                    # Log transcription
                    transcript = data.get('text')
                    logger.info(f"👤 User said: {transcript}")
                
                elif msg_type == 'assistant_message':
                    # Log AI response and send as TTS
                    response = data.get('message', {}).get('content', '')
                    if response:
                        logger.info(f"🤖 AI responds: {response}")
                        # Send text to Twilio for TTS instead of audio
                        await self.send_tts_to_twilio(response)
                    else:
                        logger.warning(f"⚠️ Empty AI response received")
                
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
            
            # Log detailed audio info
            if not hasattr(self, '_audio_sent_count'):
                self._audio_sent_count = 0
            self._audio_sent_count += 1
            
            if self._audio_sent_count <= 3:  # Log first 3 audio sends
                logger.info(f"📤 Sending audio #{self._audio_sent_count}:")
                logger.info(f"   Original size: {len(audio_base64)} chars")
                logger.info(f"   Converted size: {len(mulaw_payload)} chars")
                logger.info(f"   Stream SID: {self.stream_sid}")
            
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": mulaw_payload
                }
            }
            
            await self.send(text_data=json.dumps(message))
            
            if self._audio_sent_count <= 3:
                logger.info(f"✅ Audio #{self._audio_sent_count} sent to Twilio successfully")
            elif self._audio_sent_count % 10 == 0:
                logger.info(f"📤 Sent {self._audio_sent_count} audio chunks to Twilio")
            
        except Exception as e:
            logger.error(f"❌ Send to Twilio error: {str(e)}")
    
    async def send_raw_audio_to_twilio(self, audio_base64: str):
        """Send raw audio from HumeAI to Twilio (no conversion) - for testing"""
        try:
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_base64  # Send raw without conversion
                }
            }
            
            await self.send(text_data=json.dumps(message))
            logger.info(f"🧪 Sent RAW audio to Twilio (no conversion)")
            
        except Exception as e:
            logger.error(f"❌ Send RAW audio to Twilio error: {str(e)}")
    
    async def send_tts_to_twilio(self, text: str):
        """Send text to Twilio for TTS playback using redirect"""
        try:
            # Get TTS settings from environment or use defaults
            from decouple import config
            
            tts_voice = config('TWILIO_TTS_VOICE', default='Polly.Joanna')
            
            # Instead of WebSocket say event, use redirect to TwiML endpoint
            redirect_message = {
                "event": "redirect",
                "streamSid": self.stream_sid,
                "redirect": {
                    "url": f"https://uncontortioned-na-ponderously.ngrok-free.dev/api/hume-twilio/tts-response/?text={text[:200]}&voice={tts_voice}"
                }
            }
            
            await self.send(text_data=json.dumps(redirect_message))
            logger.info(f"� Sent TTS redirect to Twilio [{tts_voice}]: '{text[:50]}...'")
            
        except Exception as e:
            logger.error(f"❌ Send TTS to Twilio error: {str(e)}")
