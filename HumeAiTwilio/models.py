from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class HumeAgent(models.Model):
    """HumeAI Agent Configuration"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    hume_config_id = models.CharField(max_length=255, help_text="HumeAI Configuration ID")
    
    # Agent Settings
    voice_name = models.CharField(max_length=100, default="ITO", help_text="Voice model name")
    language = models.CharField(max_length=10, default="en", help_text="Language code")
    
    # Personality & Behavior
    system_prompt = models.TextField(
        help_text="Instructions for the AI agent's behavior",
        default="You are a helpful sales assistant. Be friendly, professional, and helpful."
    )
    greeting_message = models.TextField(
        default="Hello! How can I help you today?",
        help_text="Initial greeting when call starts"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='hume_agents')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hume_agents'
        ordering = ['-created_at']
        verbose_name = 'HumeAI Agent'
        verbose_name_plural = 'HumeAI Agents'
    
    def __str__(self):
        return f"{self.name} ({self.status})"


class TwilioCall(models.Model):
    """Twilio Call Records with HumeAI Integration"""
    
    CALL_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('ringing', 'Ringing'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('busy', 'Busy'),
        ('no_answer', 'No Answer'),
        ('canceled', 'Canceled'),
    ]
    
    CALL_DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Twilio Details
    call_sid = models.CharField(max_length=255, unique=True, help_text="Twilio Call SID")
    from_number = models.CharField(max_length=20)
    to_number = models.CharField(max_length=20)
    direction = models.CharField(max_length=20, choices=CALL_DIRECTION_CHOICES, default='outbound')
    status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='initiated')
    
    # HumeAI Integration
    agent = models.ForeignKey(HumeAgent, on_delete=models.SET_NULL, null=True, related_name='calls')
    hume_session_id = models.CharField(max_length=255, blank=True, null=True)
    hume_chat_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Call Metadata
    duration = models.IntegerField(default=0, help_text="Call duration in seconds")
    recording_url = models.URLField(blank=True, null=True)
    
    # User Association
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='twilio_calls')
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'twilio_calls'
        ordering = ['-created_at']
        verbose_name = 'Twilio Call'
        verbose_name_plural = 'Twilio Calls'
        indexes = [
            models.Index(fields=['call_sid']),
            models.Index(fields=['status']),
            models.Index(fields=['from_number']),
            models.Index(fields=['to_number']),
        ]
    
    def __str__(self):
        return f"{self.from_number} → {self.to_number} ({self.status})"


class ConversationLog(models.Model):
    """Store conversation messages between Customer and HumeAI Agent"""
    
    ROLE_CHOICES = [
        ('user', 'Customer'),
        ('assistant', 'AI Agent'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(TwilioCall, on_delete=models.CASCADE, related_name='conversation_logs')
    
    # Message Details
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField()
    
    # Emotion & Sentiment (from HumeAI)
    emotion_scores = models.JSONField(blank=True, null=True, help_text="Emotion detection scores")
    sentiment = models.CharField(max_length=20, blank=True, null=True)
    confidence = models.FloatField(default=0.0)
    
    # Metadata
    metadata = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'conversation_logs'
        ordering = ['timestamp']
        verbose_name = 'Conversation Log'
        verbose_name_plural = 'Conversation Logs'
    
    def __str__(self):
        return f"{self.role}: {self.message[:50]}..."


class CallAnalytics(models.Model):
    """Analytics and Insights from Calls"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.OneToOneField(TwilioCall, on_delete=models.CASCADE, related_name='analytics')
    
    # Conversation Metrics
    total_messages = models.IntegerField(default=0)
    user_messages = models.IntegerField(default=0)
    agent_messages = models.IntegerField(default=0)
    
    # Sentiment Analysis
    overall_sentiment = models.CharField(max_length=20, blank=True, null=True)
    positive_score = models.FloatField(default=0.0)
    negative_score = models.FloatField(default=0.0)
    neutral_score = models.FloatField(default=0.0)
    
    # Emotion Analysis (Top emotions detected)
    top_emotions = models.JSONField(blank=True, null=True)
    
    # Call Quality
    interruptions = models.IntegerField(default=0)
    response_time_avg = models.FloatField(default=0.0, help_text="Average response time in seconds")
    
    # Business Metrics
    lead_qualified = models.BooleanField(default=False)
    appointment_booked = models.BooleanField(default=False)
    sale_made = models.BooleanField(default=False)
    
    # Additional Data
    keywords_mentioned = models.JSONField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'call_analytics'
        verbose_name = 'Call Analytics'
        verbose_name_plural = 'Call Analytics'
    
    def __str__(self):
        return f"Analytics for {self.call.call_sid}"


class WebhookLog(models.Model):
    """Log all webhook events from Twilio and HumeAI"""
    
    SOURCE_CHOICES = [
        ('twilio', 'Twilio'),
        ('hume', 'HumeAI'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    event_type = models.CharField(max_length=100)
    
    # Webhook Data
    payload = models.JSONField()
    headers = models.JSONField(blank=True, null=True)
    
    # Processing Status
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True, null=True)
    
    # Associations
    call = models.ForeignKey(TwilioCall, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'webhook_logs'
        ordering = ['-created_at']
        verbose_name = 'Webhook Log'
        verbose_name_plural = 'Webhook Logs'
        indexes = [
            models.Index(fields=['source', 'event_type']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f"{self.source} - {self.event_type}"
