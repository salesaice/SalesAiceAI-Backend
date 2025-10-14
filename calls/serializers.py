from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    CallSession, 
    CallQueue, 
    CallTranscript, 
    CallEmotion,
    CallRecording,
    CallScript,
    QuickAction
)
from agents.models import Agent

User = get_user_model()


class CallTranscriptSerializer(serializers.ModelSerializer):
    """Serializer for individual transcript entries"""
    
    class Meta:
        model = CallTranscript
        fields = ['session_id', 'speaker', 'message', 'timestamp']


class CallEmotionSerializer(serializers.ModelSerializer):
    """Serializer for emotion analysis data"""
    
    class Meta:
        model = CallEmotion
        fields = ['timestamp', 'emotion', 'confidence']


class CallDataSerializer(serializers.ModelSerializer):
    """
    Serializer for call data matching the frontend interface:
    interface CallData {
      id: string;
      type: 'inbound' | 'outbound';
      status: 'active' | 'completed' | 'failed' | 'pending';
      caller_number: string;
      caller_name?: string;
      start_time: string;
      end_time?: string;
      duration?: number;
      transcript: TranscriptItem[];
      emotions: Array<{
        timestamp: number;
        emotion: string;
        confidence: number;
      }>;
      outcome?: 'answered' | 'voicemail' | 'busy' | 'no_answer' | 'converted' | 'not_interested';
      summary?: string;
      agent_id: number;
      agent_name?: string;
      scheduled_time?: string;
    }
    """
    id = serializers.CharField(source='pk', read_only=True)
    type = serializers.CharField(source='call_type', read_only=True)
    status = serializers.SerializerMethodField()
    start_time = serializers.DateTimeField(source='started_at', read_only=True)
    end_time = serializers.DateTimeField(source='ended_at', read_only=True)
    transcript = serializers.SerializerMethodField()
    emotions = serializers.SerializerMethodField()
    summary = serializers.CharField(source='ai_summary', read_only=True)
    agent_id = str(serializers.SerializerMethodField())
    agent_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CallSession
        fields = [
            'id', 'type', 'status', 'caller_number', 'caller_name',
            'start_time', 'end_time', 'duration', 'transcript', 'emotions',
            'outcome', 'summary', 'agent_id', 'agent_name', 'scheduled_time'
        ]
    
    def get_status(self, obj):
        """Convert Django call status to frontend format"""
        # Map Django status to frontend status
        status_mapping = {
            'initiated': 'pending',
            'ringing': 'pending', 
            'answered': 'active',
            'completed': 'completed',
            'failed': 'failed',
            'busy': 'failed',
            'no_answer': 'failed',
            'cancelled': 'failed'
        }
        
        # If call is currently in progress
        if obj.answered_at and not obj.ended_at:
            return 'active'
        
        django_status = obj.status
        return status_mapping.get(django_status, 'pending')
    
    def get_transcript(self, obj):
        """Get transcript items for this call"""
        transcripts = obj.transcripts.all()
        return CallTranscriptSerializer(transcripts, many=True).data
    
    def get_emotions(self, obj):
        """Get emotion analysis data for this call"""
        emotions = obj.emotions.all()
        return CallEmotionSerializer(emotions, many=True).data
    
    def get_agent_id(self, obj):
        """Get agent ID as integer"""
        return int(obj.agent.pk) if obj.agent else None
    
    def get_agent_name(self, obj):
        """Get agent name"""
        return obj.agent.name if obj.agent else None


class CallSessionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for call list views"""
    id = serializers.CharField(source='pk', read_only=True)
    type = serializers.CharField(source='call_type', read_only=True)
    status = serializers.SerializerMethodField()
    duration_formatted = serializers.CharField(source='call_duration_formatted', read_only=True)
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    
    class Meta:
        model = CallSession
        fields = [
            'id', 'type', 'status', 'caller_number', 'caller_name',
            'started_at', 'ended_at', 'duration', 'duration_formatted',
            'agent_name', 'outcome'
        ]
    
    def get_status(self, obj):
        """Convert Django call status to frontend format"""
        status_mapping = {
            'initiated': 'pending',
            'ringing': 'pending', 
            'answered': 'active',
            'completed': 'completed',
            'failed': 'failed',
            'busy': 'failed',
            'no_answer': 'failed',
            'cancelled': 'failed'
        }
        
        if obj.answered_at and not obj.ended_at:
            return 'active'
            
        return status_mapping.get(obj.status, 'pending')


class CallQueueSerializer(serializers.ModelSerializer):
    """Serializer for call queue management"""
    call_info = serializers.SerializerMethodField()
    agent_name = serializers.CharField(source='assigned_agent.name', read_only=True)
    
    class Meta:
        model = CallQueue
        fields = [
            'id', 'status', 'priority', 'queued_at', 'assigned_at',
            'completed_at', 'wait_time', 'call_info', 'agent_name'
        ]
    
    def get_call_info(self, obj):
        """Get basic call information"""
        return {
            'id': str(obj.call_session.pk),
            'caller_number': obj.call_session.caller_number,
            'caller_name': obj.call_session.caller_name,
            'call_type': obj.call_session.call_type
        }