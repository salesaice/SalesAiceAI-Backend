from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import CallSession, CallTranscript, CallEmotion
from .broadcasting import CallsBroadcaster
import logging

logger = logging.getLogger(__name__)
broadcaster = CallsBroadcaster()


@receiver(post_save, sender=CallSession)
def call_session_saved(sender, instance, created, **kwargs):
    """Signal handler for CallSession save events"""
    try:
        if created:
            # New call created
            logger.info(f"New call created: {instance.id}")
            broadcaster.broadcast_call_created(
                instance, 
                user_id=instance.user.id if instance.user else None,
                agent_id=instance.agent.id if instance.agent else None
            )
        else:
            # Existing call updated
            logger.info(f"Call updated: {instance.id} - Status: {instance.status}")
            broadcaster.broadcast_call_status_update(
                instance,
                user_id=instance.user.id if instance.user else None, 
                agent_id=instance.agent.id if instance.agent else None
            )
    except Exception as e:
        logger.error(f"Error broadcasting call update: {e}")


@receiver(post_save, sender=CallTranscript)
def call_transcript_saved(sender, instance, created, **kwargs):
    """Signal handler for CallTranscript save events"""
    try:
        if created:
            logger.info(f"New transcript entry: Call {instance.call_session.id}")
            
            # Broadcast transcript update
            transcript_data = {
                'call_id': str(instance.call_session.id),
                'session_id': instance.session_id,
                'speaker': instance.speaker,
                'message': instance.message,
                'timestamp': instance.timestamp.isoformat(),
                'confidence': instance.confidence
            }
            
            broadcaster.broadcast_transcript_update(
                instance.call_session,
                transcript_data
            )
    except Exception as e:
        logger.error(f"Error broadcasting transcript update: {e}")


@receiver(post_save, sender=CallEmotion)
def call_emotion_saved(sender, instance, created, **kwargs):
    """Signal handler for CallEmotion save events"""
    try:
        if created:
            logger.info(f"New emotion entry: Call {instance.call_session.id}")
            
            # Broadcast emotion update
            emotion_data = {
                'call_id': str(instance.call_session.id),
                'timestamp': instance.timestamp,
                'emotion': instance.emotion,
                'confidence': instance.confidence,
                'intensity': instance.intensity,
                'speaker': instance.speaker
            }
            
            broadcaster.broadcast_emotion_update(
                instance.call_session,
                emotion_data
            )
    except Exception as e:
        logger.error(f"Error broadcasting emotion update: {e}")


# Real-time helper functions for manual broadcasting
def broadcast_call_data_update(call_session):
    """Manually broadcast complete call data update"""
    try:
        from .serializers import CallDataSerializer
        
        # Serialize complete call data
        serializer = CallDataSerializer(call_session)
        call_data = serializer.data
        
        broadcaster.broadcast_call_data_complete(
            call_session,
            call_data
        )
        
        logger.info(f"Broadcasted complete call data for: {call_session.id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting complete call data: {e}")


def broadcast_live_call_update(call_id, update_type, data):
    """Broadcast live updates during an active call"""
    try:
        broadcaster.broadcast_live_call_update(call_id, update_type, data)
        logger.info(f"Broadcasted live update for call: {call_id}")
    except Exception as e:
        logger.error(f"Error broadcasting live call update: {e}")