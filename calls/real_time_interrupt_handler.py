#!/usr/bin/env python3
"""
🎧 REAL-TIME INTERRUPT STREAM HANDLER
====================================
Handles real-time audio streams from Twilio for instant interruption detection
"""

import json
import base64
import asyncio
import websockets
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import logging

logger = logging.getLogger(__name__)

@csrf_exempt  
def start_media_stream(request):
    """
    Start Twilio Media Stream for real-time interrupt detection
    """
    try:
        call_sid = request.POST.get('CallSid', '')
        
        print(f"🎧 Starting media stream for call {call_sid[:8]}...")
        
        response = VoiceResponse()
        
        # Start media stream for real-time audio
        connect = Connect()
        stream = connect.stream(
            name=f'interrupt_stream_{call_sid}',
            url=f'wss://your-domain.com/ws/audio/{call_sid}'  # WebSocket endpoint
        )
        
        response.append(connect)
        
        # Continue with normal call flow
        response.redirect(f'/calls/webhook/?stream_active=true&CallSid={call_sid}')
        
        return HttpResponse(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Media stream error: {e}")
        response = VoiceResponse()
        response.say("Technical difficulty. Please hold.")
        return HttpResponse(str(response), content_type='text/xml')

class AudioStreamHandler:
    """
    Handle real-time audio streams for interrupt detection
    """
    
    def __init__(self):
        self.active_streams = {}
        self.interrupt_threshold = 0.3  # Voice activity threshold
        
    async def handle_stream(self, websocket, path):
        """
        Handle incoming WebSocket audio stream
        """
        try:
            call_sid = path.split('/')[-1]  # Extract call SID from path
            print(f"🎧 Audio stream connected for call {call_sid[:8]}")
            
            self.active_streams[call_sid] = {
                'websocket': websocket,
                'agent_speaking': False,
                'customer_speaking': False,
                'last_audio_time': None
            }
            
            async for message in websocket:
                await self.process_audio_message(message, call_sid)
                
        except Exception as e:
            print(f"❌ Stream handler error: {e}")
        finally:
            if call_sid in self.active_streams:
                del self.active_streams[call_sid]
                print(f"🎧 Audio stream disconnected for call {call_sid[:8]}")
    
    async def process_audio_message(self, message, call_sid):
        """
        Process real-time audio for interrupt detection
        """
        try:
            data = json.loads(message)
            event = data.get('event')
            
            if event == 'start':
                print(f"🎧 Audio stream started for {call_sid[:8]}")
                self.active_streams[call_sid]['stream_started'] = True
                
            elif event == 'media':
                # Process audio payload for voice activity
                payload = data.get('media', {}).get('payload', '')
                
                if payload:
                    # Decode audio (Twilio sends mulaw encoded audio)
                    audio_data = base64.b64decode(payload)
                    
                    # Detect voice activity (simplified)
                    voice_detected = self.detect_voice_activity(audio_data)
                    
                    # Check for interruption
                    if voice_detected and self.active_streams[call_sid]['agent_speaking']:
                        print(f"🚨 REAL-TIME INTERRUPT: Customer speaking during agent speech!")
                        await self.trigger_interrupt(call_sid)
                        
            elif event == 'stop':
                print(f"🎧 Audio stream stopped for {call_sid[:8]}")
                
        except Exception as e:
            print(f"❌ Audio processing error: {e}")
    
    def detect_voice_activity(self, audio_data):
        """
        Simple voice activity detection
        """
        try:
            # Convert audio to amplitude analysis
            import numpy as np
            
            # Convert mulaw to linear PCM (simplified)
            audio_array = np.frombuffer(audio_data, dtype=np.uint8)
            
            # Calculate RMS (Root Mean Square) for volume detection
            rms = np.sqrt(np.mean(audio_array.astype(float) ** 2))
            
            # Voice detected if RMS above threshold
            return rms > self.interrupt_threshold * 255
            
        except:
            # Fallback: basic volume check
            return len(audio_data) > 0 and max(audio_data) > 50
    
    async def trigger_interrupt(self, call_sid):
        """
        Trigger interrupt handling when customer speaks during agent speech
        """
        try:
            print(f"🚨 Triggering interrupt for call {call_sid[:8]}")
            
            # Mark agent as interrupted
            self.active_streams[call_sid]['agent_speaking'] = False
            self.active_streams[call_sid]['customer_speaking'] = True
            
            # Send interrupt signal to webhook (via HTTP request)
            import requests
            
            interrupt_url = f"https://your-domain.com/calls/webhook/?interrupt=true&CallSid={call_sid}"
            
            # Trigger interrupt handling in main webhook
            requests.post(interrupt_url, data={'SpeechResult': 'INTERRUPT_DETECTED'})
            
            print(f"✅ Interrupt signal sent for call {call_sid[:8]}")
            
        except Exception as e:
            print(f"❌ Interrupt trigger error: {e}")
    
    def set_agent_speaking(self, call_sid, speaking=True):
        """
        Update agent speaking status for interrupt detection
        """
        if call_sid in self.active_streams:
            self.active_streams[call_sid]['agent_speaking'] = speaking
            print(f"📢 Agent speaking status: {speaking} for call {call_sid[:8]}")

# Global stream handler instance
audio_stream_handler = AudioStreamHandler()

def get_stream_handler():
    """Get the audio stream handler instance"""
    return audio_stream_handler