"""
Test fix for Twilio audio playback issues
Add timing and buffering controls
"""

# Add this to your send_to_twilio function in hume_realtime_consumer.py

async def send_to_twilio_with_timing(self, audio_base64: str):
    """Send audio from HumeAI back to Twilio with timing controls"""
    try:
        if not audio_base64:
            logger.warning(f"⚠️ Empty audio data received from HumeAI")
            return
        
        # Convert linear16 PCM from HumeAI to µ-law for Twilio
        mulaw_payload = self.convert_linear16_to_mulaw(audio_base64)
        
        # Create media message with additional timing parameters
        message = {
            "event": "media",
            "streamSid": self.stream_sid,
            "media": {
                "payload": mulaw_payload,
                "timestamp": None  # Let Twilio handle timing
            }
        }
        
        # Send immediately
        message_json = json.dumps(message)
        await self.send(text_data=message_json)
        
        # Log timing info
        import time
        current_time = time.time()
        logger.info(f"📤 Audio sent at {current_time}: {len(mulaw_payload)} chars")
        
        # Optional: Add a small delay to prevent overwhelming Twilio
        await asyncio.sleep(0.01)  # 10ms delay
        
    except Exception as e:
        logger.error(f"❌ Send to Twilio error: {str(e)}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")