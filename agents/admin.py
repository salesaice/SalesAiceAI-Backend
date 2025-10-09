from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Agent,
    BusinessKnowledge,
    Contact,
    ContactUpload,
    Campaign,
    CallQueue,
    AgentPerformanceMetrics
)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """Admin interface for Agent management"""
    
    list_display = [
        'name', 'owner', 'agent_type', 'status', 'calls_handled', 
        'success_rate', 'is_ai_agent', 'last_activity'
    ]
    list_filter = [
        'agent_type', 'status', 'created_at', 'human_operator'
    ]
    search_fields = ['name', 'owner__email', 'owner__first_name', 'owner__last_name']
    readonly_fields = [
        'id', 'calls_handled', 'total_calls', 'successful_calls', 
        'average_call_duration', 'customer_satisfaction', 'created_at', 
        'updated_at', 'success_rate', 'is_ai_agent'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'owner', 'agent_type', 'status', 'human_operator')
        }),
        ('Voice & AI Configuration', {
            'fields': (
                'hume_ai_api_key', 'hume_ai_config', 'voice_model', 
                'tone_settings', 'auto_answer_enabled'
            ),
            'classes': ('collapse',)
        }),
        ('Schedule & Operations', {
            'fields': ('operating_hours',),
            'classes': ('collapse',)
        }),
        ('Sales Configuration', {
            'fields': ('sales_script_file', 'sales_script_text'),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': (
                'calls_handled', 'total_calls', 'successful_calls',
                'average_call_duration', 'customer_satisfaction', 'success_rate'
            ),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('id', 'created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'human_operator')
    
    def success_rate(self, obj):
        """Display success rate with color coding"""
        rate = obj.success_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate.short_description = 'Success Rate'
    
    def is_ai_agent(self, obj):
        """Display AI agent status with icon"""
        if obj.is_ai_agent:
            return format_html(
                '<span style="color: blue;">🤖 AI</span>'
            )
        else:
            return format_html(
                '<span style="color: green;">👤 Human</span>'
            )
    is_ai_agent.short_description = 'Type'


class BusinessKnowledgeInline(admin.TabularInline):
    """Inline admin for Business Knowledge"""
    model = BusinessKnowledge
    extra = 0
    fields = ['title', 'knowledge_file', 'website_url', 'is_processed']
    readonly_fields = ['is_processed']


class ContactInline(admin.TabularInline):
    """Inline admin for Contacts (limited display)"""
    model = Contact
    extra = 0
    fields = ['name', 'phone', 'call_status', 'call_attempts']
    readonly_fields = ['call_attempts']
    max_num = 10  # Limit display for performance


@admin.register(BusinessKnowledge)
class BusinessKnowledgeAdmin(admin.ModelAdmin):
    """Admin interface for Business Knowledge"""
    
    list_display = ['title', 'agent', 'file_type', 'is_processed', 'created_at']
    list_filter = ['file_type', 'is_processed', 'created_at']
    search_fields = ['title', 'agent__name', 'description']
    readonly_fields = ['id', 'is_processed', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('agent', 'title', 'description')
        }),
        ('Knowledge Content', {
            'fields': ('website_url', 'knowledge_file', 'knowledge_text', 'file_type')
        }),
        ('Processing Status', {
            'fields': ('is_processed',)
        }),
        ('System Info', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Admin interface for Contacts"""
    
    list_display = [
        'name', 'phone', 'agent', 'call_status', 'priority',
        'call_attempts', 'conversion_achieved', 'last_call_attempt'
    ]
    list_filter = [
        'call_status', 'priority', 'conversion_achieved', 
        'agent__name', 'created_at'
    ]
    search_fields = ['name', 'phone', 'email', 'agent__name']
    readonly_fields = ['id', 'call_attempts', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('agent', 'name', 'phone', 'email', 'notes', 'preferred_call_time')
        }),
        ('Call Management', {
            'fields': (
                'call_status', 'priority', 'call_attempts', 
                'last_call_attempt', 'next_call_scheduled'
            )
        }),
        ('Results', {
            'fields': ('call_outcome', 'conversion_achieved')
        }),
        ('System Info', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('agent')


@admin.register(ContactUpload)
class ContactUploadAdmin(admin.ModelAdmin):
    """Admin interface for Contact Uploads"""
    
    list_display = [
        'agent', 'contacts_file', 'is_processed', 'contacts_imported',
        'uploaded_at', 'processed_at'
    ]
    list_filter = ['is_processed', 'uploaded_at']
    search_fields = ['agent__name']
    readonly_fields = [
        'id', 'is_processed', 'processing_status', 'contacts_imported',
        'errors_encountered', 'uploaded_at', 'processed_at'
    ]
    
    fieldsets = (
        ('Upload Information', {
            'fields': ('agent', 'contacts_file')
        }),
        ('Processing Results', {
            'fields': (
                'is_processed', 'processing_status', 'contacts_imported',
                'errors_encountered'
            )
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'processed_at')
        }),
    )


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin interface for Campaigns"""
    
    list_display = [
        'name', 'agent', 'status', 'total_contacts', 'contacts_called',
        'success_rate', 'conversion_rate', 'created_at'
    ]
    list_filter = [
        'status', 'schedule_type', 'agent__name', 'created_at'
    ]
    search_fields = ['name', 'agent__name', 'description']
    readonly_fields = [
        'id', 'total_contacts', 'contacts_called', 'successful_calls',
        'failed_calls', 'conversions', 'created_at', 'updated_at',
        'success_rate', 'conversion_rate'
    ]
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('agent', 'name', 'description')
        }),
        ('Schedule & Status', {
            'fields': ('status', 'schedule_type', 'scheduled_start')
        }),
        ('Campaign Metrics', {
            'fields': (
                'total_contacts', 'contacts_called', 'successful_calls',
                'failed_calls', 'conversions', 'success_rate', 'conversion_rate'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('agent')
    
    def success_rate(self, obj):
        """Display success rate with color coding"""
        rate = obj.success_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate.short_description = 'Success Rate'
    
    def conversion_rate(self, obj):
        """Display conversion rate with color coding"""
        rate = obj.conversion_rate
        if rate >= 20:
            color = 'green'
        elif rate >= 10:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    conversion_rate.short_description = 'Conversion Rate'


@admin.register(CallQueue)
class CallQueueAdmin(admin.ModelAdmin):
    """Admin interface for Call Queue"""
    
    list_display = [
        'campaign', 'contact_name', 'queue_position', 'status',
        'scheduled_time', 'call_duration', 'call_outcome'
    ]
    list_filter = ['status', 'campaign__name', 'scheduled_time']
    search_fields = ['contact__name', 'contact__phone', 'campaign__name']
    readonly_fields = [
        'id', 'started_at', 'completed_at', 'call_duration',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Queue Information', {
            'fields': ('campaign', 'contact', 'queue_position', 'status')
        }),
        ('Scheduling', {
            'fields': ('scheduled_time', 'started_at', 'completed_at')
        }),
        ('Call Results', {
            'fields': ('call_duration', 'call_outcome', 'notes')
        }),
        ('System Info', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('campaign', 'contact')
    
    def contact_name(self, obj):
        return obj.contact.name
    contact_name.short_description = 'Contact'


@admin.register(AgentPerformanceMetrics)
class AgentPerformanceMetricsAdmin(admin.ModelAdmin):
    """Admin interface for Agent Performance Metrics"""
    
    list_display = [
        'agent', 'date', 'calls_made', 'calls_completed',
        'success_rate', 'conversion_rate', 'customer_satisfaction_score'
    ]
    list_filter = ['date', 'agent__name']
    search_fields = ['agent__name']
    readonly_fields = ['id', 'success_rate', 'conversion_rate', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('agent', 'date')
        }),
        ('Call Metrics', {
            'fields': (
                'calls_made', 'calls_answered', 'calls_completed', 'calls_failed',
                'total_talk_time', 'average_call_duration'
            )
        }),
        ('Quality Metrics', {
            'fields': (
                'customer_satisfaction_score', 'first_call_resolution',
                'escalations', 'conversions', 'conversion_value'
            )
        }),
        ('AI Metrics', {
            'fields': ('ai_confidence_avg',)
        }),
        ('Calculated Metrics', {
            'fields': ('success_rate', 'conversion_rate'),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('agent')
    
    def success_rate(self, obj):
        """Display success rate with color coding"""
        rate = obj.success_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate.short_description = 'Success Rate'
    
    def conversion_rate(self, obj):
        """Display conversion rate with color coding"""
        rate = obj.conversion_rate
        if rate >= 20:
            color = 'green'
        elif rate >= 10:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    conversion_rate.short_description = 'Conversion Rate'


# Customize admin site
admin.site.site_header = "SalesAI Agent Management"
admin.site.site_title = "Agent Admin"
admin.site.index_title = "Agent Management Dashboard"