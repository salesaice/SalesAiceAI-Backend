from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class CallSession(models.Model):
    """Call sessions for inbound and outbound calls"""
    CALL_TYPES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    CALL_STATUS = [
        ('initiated', 'Initiated'),
        ('ringing', 'Ringing'),
        ('answered', 'Answered'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('busy', 'Busy'),
        ('no_answer', 'No Answer'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls')
    agent = models.ForeignKey('agents.Agent', on_delete=models.SET_NULL, null=True, blank=True)
    
    call_type = models.CharField(max_length=20, choices=CALL_TYPES)
    status = models.CharField(max_length=20, choices=CALL_STATUS, default='initiated')
    
    # Contact information
    caller_number = models.CharField(max_length=20)
    callee_number = models.CharField(max_length=20)
    caller_name = models.CharField(max_length=100, blank=True)
    
    # Twilio related
    twilio_call_sid = models.CharField(max_length=100, blank=True)
    twilio_conference_sid = models.CharField(max_length=100, blank=True)
    twilio_recording_url = models.URLField(blank=True)
    
    # Call details
    started_at = models.DateTimeField(default=timezone.now)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)  # in seconds
    
    # AI Integration
    ai_summary = models.TextField(blank=True)
    ai_sentiment = models.CharField(max_length=20, blank=True)
    ai_keywords = models.JSONField(default=list, blank=True)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.call_type.title()} - {self.caller_number} to {self.callee_number}"
    
    @property
    def call_duration_formatted(self):
        """Return formatted duration in MM:SS"""
        if self.duration:
            minutes = self.duration // 60
            seconds = self.duration % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"


class CallQueue(models.Model):
    """Queue for managing inbound calls"""
    QUEUE_STATUS = [
        ('waiting', 'Waiting'),
        ('assigned', 'Assigned'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_session = models.OneToOneField(CallSession, on_delete=models.CASCADE)
    assigned_agent = models.ForeignKey('agents.Agent', on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=QUEUE_STATUS, default='waiting')
    priority = models.IntegerField(default=1)  # 1 = high, 5 = low
    
    queued_at = models.DateTimeField(default=timezone.now)
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    wait_time = models.IntegerField(default=0)  # in seconds
    
    def __str__(self):
        return f"Queue: {self.call_session.caller_number} - {self.status}"


class CallScript(models.Model):
    """Call scripts for agents"""
    SCRIPT_TYPES = [
        ('greeting', 'Greeting'),
        ('sales', 'Sales'),
        ('support', 'Support'),
        ('survey', 'Survey'),
        ('followup', 'Follow-up'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    script_type = models.CharField(max_length=20, choices=SCRIPT_TYPES)
    content = models.TextField()
    
    # AI integration
    use_ai_assistance = models.BooleanField(default=False)
    ai_prompts = models.JSONField(default=list, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.script_type})"


class CallRecording(models.Model):
    """Call recordings and transcriptions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_session = models.OneToOneField(CallSession, on_delete=models.CASCADE, related_name='recording')
    
    # Recording details
    recording_url = models.URLField()
    duration = models.IntegerField(default=0)  # in seconds
    file_size = models.BigIntegerField(default=0)  # in bytes
    
    # Transcription
    transcription = models.TextField(blank=True)
    transcription_confidence = models.FloatField(default=0.0)
    
    # AI Analysis
    sentiment_analysis = models.JSONField(default=dict, blank=True)
    key_phrases = models.JSONField(default=list, blank=True)
    compliance_score = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Recording: {self.call_session.caller_number}"


class QuickAction(models.Model):
    """Quick actions for agent dashboard"""
    ACTION_TYPES = [
        ('call', 'Make Call'),
        ('sms', 'Send SMS'),
        ('email', 'Send Email'),
        ('note', 'Add Note'),
        ('schedule', 'Schedule Callback'),
        ('transfer', 'Transfer Call'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    icon = models.CharField(max_length=50, default='phone')
    color = models.CharField(max_length=20, default='primary')
    
    # Action configuration
    config = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.action_type})"
