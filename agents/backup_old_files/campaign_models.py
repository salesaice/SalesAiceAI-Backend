from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import datetime

User = get_user_model()


class Campaign(models.Model):
    """Campaign model for managing outbound calling campaigns"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SCHEDULE_TYPES = [
        ('immediate', 'Start Immediately'),
        ('scheduled', 'Schedule for Later'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Owner and agent assignment
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns_created')
    assigned_agent_human = models.ForeignKey('Agent', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_agent_ai = models.ForeignKey('AIAgent', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Campaign configuration
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES, default='immediate')
    scheduled_datetime = models.DateTimeField(null=True, blank=True)
    
    # Campaign metrics
    total_contacts = models.IntegerField(default=0)
    contacts_called = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    failed_calls = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Campaign settings
    max_attempts_per_contact = models.IntegerField(default=3)
    retry_interval_hours = models.IntegerField(default=24)  # Hours between retry attempts
    preferred_call_time_start = models.TimeField(null=True, blank=True)
    preferred_call_time_end = models.TimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    @property
    def assigned_agent_name(self):
        """Return the name of the assigned agent"""
        if self.assigned_agent_ai:
            return self.assigned_agent_ai.name
        elif self.assigned_agent_human:
            return self.assigned_agent_human.user.get_full_name()
        return "Unassigned"
    
    @property
    def success_rate(self):
        """Calculate campaign success rate"""
        if self.contacts_called > 0:
            return round((self.successful_calls / self.contacts_called) * 100, 2)
        return 0.0
    
    @property
    def completion_rate(self):
        """Calculate campaign completion rate"""
        if self.total_contacts > 0:
            return round((self.contacts_called / self.total_contacts) * 100, 2)
        return 0.0


class CampaignContact(models.Model):
    """Track individual contacts within a campaign"""
    
    CALL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('busy', 'Busy'),
        ('no_answer', 'No Answer'),
        ('do_not_call', 'Do Not Call'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_contacts')
    customer_profile = models.ForeignKey('CustomerProfile', on_delete=models.CASCADE)
    
    # Call tracking
    call_status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='pending')
    attempts_made = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    
    # Call results
    call_duration = models.IntegerField(default=0)  # in seconds
    call_outcome = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['campaign', 'customer_profile']
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.customer_profile.name}"


class AgentSchedule(models.Model):
    """Agent working schedule configuration"""
    
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('Agent', on_delete=models.CASCADE, related_name='schedules')
    
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    work_start_time = models.TimeField()
    work_end_time = models.TimeField()
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['agent', 'day_of_week']
        ordering = ['day_of_week']
    
    def __str__(self):
        return f"{self.agent.user.get_full_name()} - {self.day_of_week}"


class BusinessKnowledge(models.Model):
    """Business knowledge base for AI agents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.OneToOneField('AIAgent', on_delete=models.CASCADE, related_name='business_knowledge')
    
    # Company information
    company_name = models.CharField(max_length=200, blank=True)
    company_description = models.TextField(blank=True)
    website_url = models.URLField(blank=True)
    
    # Products and services
    products_services = models.JSONField(default=list, blank=True)
    pricing_information = models.JSONField(default=dict, blank=True)
    
    # Sales information
    sales_script = models.TextField(blank=True)
    common_objections = models.JSONField(default=list, blank=True)
    objection_responses = models.JSONField(default=dict, blank=True)
    
    # Contact information
    business_hours = models.JSONField(default=dict, blank=True)
    contact_information = models.JSONField(default=dict, blank=True)
    
    # Knowledge files
    knowledge_documents = models.JSONField(default=list, blank=True)  # File paths/URLs
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Knowledge Base - {self.ai_agent.name}"


class AgentPerformanceMetrics(models.Model):
    """Detailed performance metrics for agents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_human = models.ForeignKey('Agent', on_delete=models.CASCADE, null=True, blank=True, related_name='detailed_performance_metrics')
    agent_ai = models.ForeignKey('AIAgent', on_delete=models.CASCADE, null=True, blank=True, related_name='detailed_performance_metrics')
    
    # Date for metrics
    date = models.DateField()
    
    # Call metrics
    total_calls = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    failed_calls = models.IntegerField(default=0)
    average_call_duration = models.FloatField(default=0.0)
    
    # Customer satisfaction
    customer_satisfaction_score = models.FloatField(default=0.0)
    total_ratings = models.IntegerField(default=0)
    
    # Revenue metrics
    total_revenue_generated = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    conversions = models.IntegerField(default=0)
    
    # Activity metrics
    active_hours = models.FloatField(default=0.0)
    break_hours = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['agent_human', 'date'], ['agent_ai', 'date']]
        ordering = ['-date']
    
    def __str__(self):
        agent_name = self.agent_ai.name if self.agent_ai else self.agent_human.user.get_full_name()
        return f"{agent_name} - {self.date}"
