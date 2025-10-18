from django.contrib import admin
from .models import (
    HumeAgent, TwilioCall, ConversationLog, 
    CallAnalytics, WebhookLog
)


@admin.register(HumeAgent)
class HumeAgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'voice_name', 'language', 'created_by', 'created_at']
    list_filter = ['status', 'language', 'created_at']
    search_fields = ['name', 'description', 'hume_config_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'status', 'created_by')
        }),
        ('HumeAI Configuration', {
            'fields': ('hume_config_id', 'voice_name', 'language')
        }),
        ('Agent Personality', {
            'fields': ('system_prompt', 'greeting_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(TwilioCall)
class TwilioCallAdmin(admin.ModelAdmin):
    list_display = ['call_sid', 'from_number', 'to_number', 'direction', 'status', 'duration', 'created_at']
    list_filter = ['status', 'direction', 'created_at']
    search_fields = ['call_sid', 'from_number', 'to_number', 'customer_name']
    readonly_fields = ['id', 'call_sid', 'hume_session_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Call Information', {
            'fields': ('id', 'call_sid', 'from_number', 'to_number', 'direction', 'status')
        }),
        ('HumeAI Integration', {
            'fields': ('agent', 'hume_session_id', 'hume_chat_id')
        }),
        ('Call Metadata', {
            'fields': ('duration', 'recording_url', 'started_at', 'ended_at')
        }),
        ('Customer Information', {
            'fields': ('user', 'customer_name', 'customer_email')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class ConversationLogInline(admin.TabularInline):
    model = ConversationLog
    extra = 0
    readonly_fields = ['role', 'message', 'timestamp']
    can_delete = False


@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ['call', 'role', 'message_preview', 'sentiment', 'timestamp']
    list_filter = ['role', 'sentiment', 'timestamp']
    search_fields = ['message', 'call__call_sid']
    readonly_fields = ['id', 'timestamp']
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(CallAnalytics)
class CallAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'call', 'total_messages', 'overall_sentiment', 
        'lead_qualified', 'appointment_booked', 'sale_made', 'created_at'
    ]
    list_filter = ['overall_sentiment', 'lead_qualified', 'appointment_booked', 'sale_made', 'created_at']
    search_fields = ['call__call_sid', 'summary']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['source', 'event_type', 'processed', 'call', 'created_at']
    list_filter = ['source', 'processed', 'created_at']
    search_fields = ['event_type', 'call__call_sid']
    readonly_fields = ['id', 'payload', 'headers', 'created_at']
