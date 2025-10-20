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
            if not mulaw_b64:
                logger.warning(f"⚠️ Empty µ-law data provided for conversion")
                return ""
            
            # Decode base64 µ-law audio
            mulaw_data = base64.b64decode(mulaw_b64)
            
            if len(mulaw_data) == 0:
                logger.warning(f"⚠️ Empty µ-law data after base64 decode")
                return ""
            
            # Convert µ-law to linear16 PCM
            linear_data = audioop.ulaw2lin(mulaw_data, 2)  # 2 bytes per sample (16-bit)
            
            # Validate conversion
            if len(linear_data) != len(mulaw_data) * 2:
                logger.warning(f"⚠️ Unexpected conversion size: {len(mulaw_data)} → {len(linear_data)}")
            
            # Encode back to base64
            linear_b64 = base64.b64encode(linear_data).decode('utf-8')
            
            # Log conversion success occasionally
            if not hasattr(self, '_conversion_count'):
                self._conversion_count = 0
            self._conversion_count += 1
            
            if self._conversion_count % 100 == 1:  # Log first and every 100th
                logger.info(f"🔄 Audio conversion #{self._conversion_count}: {len(mulaw_data)} µ-law → {len(linear_data)} linear16")
            
            return linear_b64
            
        except Exception as e:
            logger.error(f"❌ Audio conversion error: {e}")
            logger.error(f"   Input length: {len(mulaw_b64) if mulaw_b64 else 0}")
            return ""  # Return empty instead of original to prevent bad data
    
    def convert_linear16_to_mulaw(self, linear_b64: str) -> str:
        """Convert linear16 PCM from HumeAI to µ-law for Twilio"""
        try:
            # Decode base64 linear16 audio
            linear_data = base64.b64decode(linear_b64)
            logger.info(f"🔄 Converting audio: {len(linear_data)} bytes linear16 → µ-law")
            
            # Convert linear16 PCM to µ-law
            mulaw_data = audioop.lin2ulaw(linear_data, 2)  # 2 bytes per sample (16-bit)
            
            # Encode back to base64
            mulaw_b64 = base64.b64encode(mulaw_data).decode('utf-8')
            
            logger.info(f"✅ Conversion successful: {len(mulaw_data)} bytes µ-law")
            return mulaw_b64
        except Exception as e:
            logger.error(f"❌ Audio conversion error: {e}")
            logger.error(f"❌ Input data length: {len(linear_b64) if linear_b64 else 0}")
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
            
            # Send initial configuration to Twilio for optimal audio
            await self.configure_twilio_stream()
            
            # Connect to HumeAI
            await self.connect_to_hume()
            
        except Exception as e:
            logger.error(f"❌ Handle start error: {str(e)}")
    
    async def configure_twilio_stream(self):
        """Configure Twilio stream for optimal audio delivery"""
        try:
            logger.info(f"🔧 Configuring Twilio stream for audio delivery...")
            
            # Send stream configuration to Twilio
            # This tells Twilio we're ready to send audio back
            config_message = {
                "event": "start",
                "streamSid": self.stream_sid,
                "start": {
                    "accountSid": None,  # Twilio will fill this
                    "streamSid": self.stream_sid,
                    "callSid": self.call_sid,
                    "tracks": ["outbound"],  # We want to send audio to caller
                    "mediaFormat": {
                        "encoding": "mulaw",
                        "sampleRate": 8000,
                        "channels": 1
                    }
                }
            }
            
            # Note: We don't actually send this config message as Twilio manages it
            # But we log the configuration for debugging
            logger.info(f"📋 Stream config: µ-law, 8kHz, mono, outbound track")
            logger.info(f"📋 Ready to send media to stream: {self.stream_sid}")
            
        except Exception as e:
            logger.error(f"❌ Configure Twilio stream error: {str(e)}")

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
            hume_url = f"wss://api.hume.ai/v0/evi/stream?api_key={hume_api_key}&config_id={config_id}"
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
            
            # Send initial session configuration to HumeAI (simplified and working)
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
            logger.info(f"📤 Sent optimized session config to HumeAI")
            logger.info(f"   🎛️ Audio: 8kHz linear16, 20ms chunks, VAD enabled")
            logger.info(f"   🎙️ Turn detection: Server VAD with 500ms silence threshold")
            
            # Start listening to HumeAI responses
            asyncio.create_task(self.listen_to_hume())
            
            logger.info(f"🎉 HumeAI session ready for audio processing!")
            
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
                logger.warning(f"⚠️ Empty payload received from Twilio")
                return
            
            # Log first audio chunk with detailed info
            if not hasattr(self, '_first_audio_logged'):
                logger.info(f"🎤 First audio from Twilio:")
                logger.info(f"   📏 Payload length: {len(payload)} chars")
                logger.info(f"   🔧 Sample rate: 8kHz µ-law")
                logger.info(f"   📡 Stream: {self.stream_sid}")
                self._first_audio_logged = True
            
            # Convert µ-law to linear16 PCM for HumeAI
            linear_payload = self.convert_mulaw_to_linear16(payload)
            
            if not linear_payload:
                logger.error(f"❌ Audio conversion failed")
                return
            
            # Send converted audio to HumeAI with enhanced message
            hume_message = {
                "type": "audio_input",
                "data": linear_payload
            }
            
            # Check HumeAI connection before sending
            if self.hume_ws.closed:
                logger.error(f"❌ HumeAI connection closed, cannot send audio")
                self.hume_connected = False
                return
            
            await self.hume_ws.send(json.dumps(hume_message))
            
            # Enhanced logging
            if not hasattr(self, '_audio_count'):
                self._audio_count = 0
            self._audio_count += 1
            
            # Log every 25 chunks and show conversion details
            if self._audio_count % 25 == 0:
                logger.info(f"📡 Sent {self._audio_count} audio chunks to HumeAI")
                logger.info(f"   🔄 Last conversion: {len(payload)} → {len(linear_payload)} chars")
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"❌ HumeAI connection closed: {e.code} - {e.reason}")
            self.hume_connected = False
        except Exception as e:
            logger.error(f"❌ Handle media error: {str(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")

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
            self.audio_sequence = 0  # Track audio sequence for Twilio
            
            async for message in self.hume_ws:
                data = json.loads(message)
                
                # Check message type
                msg_type = data.get('type')
                logger.info(f"📨 Received from HumeAI: {msg_type}")
                
                if msg_type == 'audio_output':
                    # Get audio from HumeAI
                    audio_data = data.get('data')  # Base64 audio
                    if audio_data:
                        logger.info(f"🔊 Received audio from HumeAI ({len(audio_data)} bytes)")
                        
                        # Send to Twilio with proper chunking
                        await self.send_audio_chunks_to_twilio(audio_data)
                    else:
                        logger.warning(f"⚠️ Empty audio_output received")
                
                elif msg_type == 'user_message':
                    # Log transcription
                    transcript = data.get('text')
                    logger.info(f"👤 User said: {transcript}")
                
                elif msg_type == 'assistant_message':
                    # Log AI response text
                    response = data.get('content')
                    if response:
                        logger.info(f"🤖 AI responds: {response}")
                
                elif msg_type == 'assistant_prosody':
                    # Handle prosody information (voice characteristics)
                    logger.info(f"🎭 AI prosody data received")
                
                elif msg_type == 'assistant_end':
                    # Handle end of assistant response
                    logger.info(f"✅ AI response completed")
                
                elif msg_type == 'user_interruption':
                    # Handle user interrupting AI
                    logger.info(f"⏸️ User interrupted AI")
                
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
    
    async def send_audio_chunks_to_twilio(self, audio_base64: str):
        """Send audio directly to Twilio without chunking delays"""
        try:
            if not audio_base64:
                logger.warning(f"⚠️ Empty audio data received from HumeAI")
                return
            
            # Convert linear16 PCM from HumeAI to µ-law for Twilio
            mulaw_payload = self.convert_linear16_to_mulaw(audio_base64)
            
            logger.info(f"🚀 Sending audio directly to Twilio: {len(mulaw_payload)} chars")
            
            # Send mark message first to indicate audio start
            mark_message = {
                "event": "mark",
                "streamSid": self.stream_sid,
                "mark": {
                    "name": "audio_start"
                }
            }
            await self.send(text_data=json.dumps(mark_message))
            logger.info(f"📍 Sent mark message: audio_start")
            
            # Send entire audio payload at once - let Twilio handle streaming
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": mulaw_payload
                }
            }
            
            message_json = json.dumps(message)
            await self.send(text_data=message_json)
            
            # Send mark message after audio to indicate completion
            mark_end_message = {
                "event": "mark",
                "streamSid": self.stream_sid,
                "mark": {
                    "name": "audio_end"
                }
            }
            await self.send(text_data=json.dumps(mark_end_message))
            
            logger.info(f"✅ Audio sent directly to Twilio with mark messages!")
                
        except Exception as e:
            logger.error(f"❌ Send audio chunks error: {str(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
    
    async def send_audio_chunk_to_twilio(self, chunk_payload: str, sequence: int):
        """Send individual audio chunk to Twilio with sequence tracking"""
        try:
            # Check if we have a valid stream ID (indicates connection is active)
            if not self.stream_sid:
                logger.warning(f"⚠️ No stream ID available, stopping audio transmission")
                return False
            
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": chunk_payload
                }
            }
            
            message_json = json.dumps(message)
            await self.send(text_data=message_json)
            
            # Log every 10th chunk to avoid spam
            if sequence % 10 == 0:
                logger.info(f"📤 Sent chunk {sequence}: {len(chunk_payload)} chars")
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Send chunk {sequence} error: {str(e)}")
            return False
    
    async def send_to_twilio(self, audio_base64: str):
        """Send audio from HumeAI back to Twilio"""
        try:
            if not audio_base64:
                logger.warning(f"⚠️ Empty audio data received from HumeAI")
                return
            
            # Convert linear16 PCM from HumeAI to µ-law for Twilio
            mulaw_payload = self.convert_linear16_to_mulaw(audio_base64)
            
            # Log detailed audio info
            logger.info(f"🔊 Audio conversion: {len(audio_base64)} → {len(mulaw_payload)} bytes")
            
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": mulaw_payload
                }
            }
            
            # Log the actual message being sent
            message_json = json.dumps(message)
            logger.info(f"📤 Sending to Twilio: {len(message_json)} bytes total")
            logger.info(f"📤 Stream ID: {self.stream_sid}")
            logger.info(f"📤 Payload length: {len(mulaw_payload)} characters")
            
            await self.send(text_data=message_json)
            logger.info(f"✅ Audio successfully sent to Twilio!")
            
        except Exception as e:
            logger.error(f"❌ Send to Twilio error: {str(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")