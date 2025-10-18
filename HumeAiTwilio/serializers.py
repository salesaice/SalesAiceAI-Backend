from rest_framework import serializers
from .models import (
    HumeAgent, TwilioCall, ConversationLog,
    CallAnalytics, WebhookLog
)


class HumeAgentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    total_calls = serializers.SerializerMethodField()
    
    class Meta:
        model = HumeAgent
        fields = [
            'id', 'name', 'description', 'hume_config_id',
            'voice_name', 'language', 'system_prompt', 'greeting_message',
            'status', 'created_by', 'created_by_name', 'total_calls',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_calls(self, obj):
        return obj.calls.count()


class ConversationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationLog
        fields = [
            'id', 'role', 'message', 'emotion_scores',
            'sentiment', 'confidence', 'metadata', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class CallAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallAnalytics
        fields = [
            'id', 'total_messages', 'user_messages', 'agent_messages',
            'overall_sentiment', 'positive_score', 'negative_score', 'neutral_score',
            'top_emotions', 'interruptions', 'response_time_avg',
            'lead_qualified', 'appointment_booked', 'sale_made',
            'keywords_mentioned', 'summary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TwilioCallSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    conversation_logs = ConversationLogSerializer(many=True, read_only=True)
    analytics = CallAnalyticsSerializer(read_only=True)
    
    class Meta:
        model = TwilioCall
        fields = [
            'id', 'call_sid', 'from_number', 'to_number', 'direction', 'status',
            'agent', 'agent_name', 'hume_session_id', 'hume_chat_id',
            'duration', 'recording_url', 'user', 'user_name',
            'customer_name', 'customer_email',
            'started_at', 'ended_at', 'created_at', 'updated_at',
            'conversation_logs', 'analytics'
        ]
        read_only_fields = ['id', 'call_sid', 'created_at', 'updated_at']


class TwilioCallListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list view"""
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    
    class Meta:
        model = TwilioCall
        fields = [
            'id', 'call_sid', 'from_number', 'to_number', 'direction',
            'status', 'agent_name', 'duration', 'customer_name',
            'started_at', 'created_at'
        ]


class WebhookLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookLog
        fields = [
            'id', 'source', 'event_type', 'payload', 'headers',
            'processed', 'error', 'call', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InitiateCallSerializer(serializers.Serializer):
    """Serializer for initiating outbound calls"""
    to_number = serializers.CharField(max_length=20, required=True)
    agent_id = serializers.UUIDField(required=True)
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    custom_greeting = serializers.CharField(required=False, allow_blank=True)
    
    def validate_to_number(self, value):
        # Basic phone number validation
        if not value.startswith('+'):
            raise serializers.ValidationError("Phone number must include country code (e.g., +1234567890)")
        return value
    
    def validate_agent_id(self, value):
        try:
            agent = HumeAgent.objects.get(id=value, status='active')
        except HumeAgent.DoesNotExist:
            raise serializers.ValidationError("Agent not found or not active")
        return value
