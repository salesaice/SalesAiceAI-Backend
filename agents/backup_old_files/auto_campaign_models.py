from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import datetime

User = get_user_model()


class AutoCallCampaign(models.Model):
    """
    Auto Call Campaign Model
    Specifically for automatic calling campaigns
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    CAMPAIGN_TYPES = [
        ('general', 'General Outreach'),
        ('followup', 'Follow-up Calls'),
        ('new_leads', 'New Leads'),
        ('callbacks', 'Scheduled Callbacks'),
        ('test', 'Test Campaign'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey('AIAgent', on_delete=models.CASCADE, related_name='auto_campaigns')
    
    # Campaign Details
    name = models.CharField(max_length=200)
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Call Configuration
    target_customers = models.IntegerField(default=50)
    calls_per_hour = models.IntegerField(default=10)
    working_hours_start = models.CharField(max_length=5, default='09:00')
    working_hours_end = models.CharField(max_length=5, default='17:00')
    
    # Campaign Data
    campaign_data = models.JSONField(default=dict)
    
    # Metrics
    total_contacts = models.IntegerField(default=0)
    contacts_called = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    failed_calls = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    @property
    def success_rate(self):
        if self.contacts_called > 0:
            return round((self.successful_calls / self.contacts_called) * 100, 1)
        return 0
    
    @property
    def completion_percentage(self):
        if self.target_customers > 0:
            return round((self.contacts_called / self.target_customers) * 100, 1)
        return 0


class AutoCampaignContact(models.Model):
    """
    Contacts for auto call campaigns
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('calling', 'Currently Calling'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('scheduled', 'Scheduled for Later'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(AutoCallCampaign, on_delete=models.CASCADE, related_name='contacts')
    customer_profile = models.ForeignKey('CustomerProfile', on_delete=models.CASCADE)
    
    # Contact Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=1)  # 1=lowest, 5=highest
    
    # Call Scheduling
    scheduled_datetime = models.DateTimeField()
    call_started_at = models.DateTimeField(null=True, blank=True)
    call_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Call Results
    call_outcome = models.CharField(max_length=50, blank=True)
    call_duration = models.IntegerField(default=0, help_text="Duration in seconds")
    failure_reason = models.CharField(max_length=200, blank=True)
    
    # Twilio Integration
    twilio_call_sid = models.CharField(max_length=100, blank=True)
    
    # Tracking
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'scheduled_datetime']
    
    def __str__(self):
        return f"{self.customer_profile.phone_number} - {self.status}"
