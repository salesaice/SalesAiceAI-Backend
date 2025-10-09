from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json
import os

User = get_user_model()


def agent_script_upload_path(instance, filename):
    """Generate upload path for agent scripts"""
    return f'agents/{instance.id}/scripts/{filename}'


def business_knowledge_upload_path(instance, filename):
    """Generate upload path for business knowledge files"""
    return f'agents/{instance.agent.id}/knowledge/{filename}'


def contacts_upload_path(instance, filename):
    """Generate upload path for contact files"""
    return f'agents/{instance.agent.id}/contacts/{filename}'


class BaseAgent(models.Model):
    """Base agent model with common fields following the workflow requirements"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
    ]
    
    AGENT_TYPES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Agent name")
    agent_type = models.CharField(
        max_length=20, 
        choices=AGENT_TYPES, 
        default='inbound',
        help_text="Agent type: Inbound or Outbound"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active',
        help_text="Agent status: Active or Paused"
    )
    
    # Performance Metrics
    calls_handled = models.IntegerField(default=0, help_text="Total calls handled by agent")
    total_calls = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    average_call_duration = models.FloatField(default=0.0)
    customer_satisfaction = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    
    # Hume AI Configuration
    hume_ai_api_key = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Hume AI API key for this agent"
    )
    hume_ai_config = models.JSONField(
        default=dict, 
        help_text="Hume AI configuration settings"
    )
    
    # Voice and Tone Selection
    voice_model = models.CharField(
        max_length=50, 
        default='en-US-female-1',
        help_text="Selected voice model"
    )
    voice_tone = models.CharField(
        max_length=100,
        default='friendly',
        help_text="Voice tone for the agent (friendly, professional, etc.)"
    )
    tone_settings = models.JSONField(
        default=dict,
        help_text="Voice tone and personality settings"
    )
    
    # Operating Hours - structured as {start: "09:00", end: "17:00"}
    operating_hours = models.JSONField(
        default=dict,
        help_text="Time windows when agent is operational with start and end times"
    )
    
    # Website URL for context
    website_url = models.URLField(
        blank=True,
        help_text="Business website URL for agent context"
    )
    
    # Auto-answer (for inbound agents)
    auto_answer_enabled = models.BooleanField(
        default=False,
        help_text="Enable auto-answer for inbound calls"
    )
    
    # Sales Script
    sales_script_file = models.FileField(
        upload_to=agent_script_upload_path,
        blank=True,
        null=True,
        help_text="Upload sales script/template file"
    )
    sales_script_text = models.TextField(
        blank=True,
        help_text="Sales script text content"
    )
    
    # Website URL for context
    website_url = models.URLField(
        blank=True,
        help_text="Business website URL for agent context"
    )
    
    # Campaign Schedule (for outbound agents)
    campaign_schedule = models.JSONField(
        default=dict,
        blank=True,
        help_text="Campaign schedule configuration: {type: 'immediate'|'scheduled', date?: 'YYYY-MM-DD', time?: 'HH:MM'}"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(default=timezone.now)
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return f"{self.name} ({self.get_agent_type_display()})"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_calls > 0:
            return round((self.successful_calls / self.total_calls) * 100, 2)
        return 0.0
    
    @property
    def is_active(self):
        """Check if agent is currently active"""
        return self.status == 'active'
    
    @property
    def can_delete(self):
        """Check if agent can be deleted (not in active call/campaign)"""
        # This will be implemented based on campaign and call status
        return self.status != 'active' or not hasattr(self, 'active_campaigns')


class Agent(BaseAgent):
    """Main Agent model following the workflow requirements"""
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='agents',
        help_text="User who owns/created this agent"
    )
    
    # For human agents (optional)
    human_operator = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operated_agent',
        help_text="Human operator for this agent (if any)"
    )
    
    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
        unique_together = ['owner', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_agent_type_display()}) - {self.owner.email}"
    
    @property
    def display_name(self):
        return self.name
    
    @property
    def is_ai_agent(self):
        """Check if this is an AI agent (no human operator)"""
        return self.human_operator is None


class BusinessKnowledge(models.Model):
    """Business Knowledge Section for agents"""
    
    FILE_TYPES = [
        ('pdf', 'PDF Document'),
        ('docx', 'Word Document'),
        ('txt', 'Text File'),
        ('csv', 'CSV File'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='business_knowledge'
    )
    
    # Website link
    website_url = models.URLField(
        blank=True,
        help_text="Business website URL"
    )
    
    # File uploads
    knowledge_file = models.FileField(
        upload_to=business_knowledge_upload_path,
        blank=True,
        null=True,
        help_text="Upload business knowledge file (PDF, DOCX, TXT)"
    )
    
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPES,
        blank=True
    )
    
    # Text content
    knowledge_text = models.TextField(
        blank=True,
        help_text="Business knowledge text content"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Knowledge item title"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this knowledge item"
    )
    
    # Processing status
    is_processed = models.BooleanField(
        default=False,
        help_text="Whether the knowledge has been processed by AI"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Business Knowledge"
        verbose_name_plural = "Business Knowledge Items"
    
    def __str__(self):
        return f"{self.agent.name} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Auto-detect file type if file is uploaded
        if self.knowledge_file and not self.file_type:
            file_extension = os.path.splitext(self.knowledge_file.name)[1].lower()
            if file_extension == '.pdf':
                self.file_type = 'pdf'
            elif file_extension in ['.docx', '.doc']:
                self.file_type = 'docx'
            elif file_extension == '.txt':
                self.file_type = 'txt'
            elif file_extension == '.csv':
                self.file_type = 'csv'
        
        super().save(*args, **kwargs)


class Contact(models.Model):
    """Contact model for outbound campaigns"""
    
    CALL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('callback_scheduled', 'Callback Scheduled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    
    # Contact Information (from CSV upload)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    
    # Preferred Time (from CSV)
    preferred_call_time = models.CharField(
        max_length=100,
        blank=True,
        help_text="Preferred time to call (from CSV upload)"
    )
    
    # Call Status
    call_status = models.CharField(
        max_length=20,
        choices=CALL_STATUS_CHOICES,
        default='pending'
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    # Call attempts
    call_attempts = models.IntegerField(default=0)
    last_call_attempt = models.DateTimeField(null=True, blank=True)
    next_call_scheduled = models.DateTimeField(null=True, blank=True)
    
    # Results
    call_outcome = models.CharField(max_length=200, blank=True)
    conversion_achieved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        unique_together = ['agent', 'phone']
    
    def __str__(self):
        return f"{self.name} - {self.phone}"


class ContactUpload(models.Model):
    """Model to track contact file uploads"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='contact_uploads'
    )
    
    contacts_file = models.FileField(
        upload_to=contacts_upload_path,
        help_text="Upload CSV file with contacts (Name, Phone, Email, Notes, Preferred Time)"
    )
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_status = models.TextField(blank=True)
    contacts_imported = models.IntegerField(default=0)
    errors_encountered = models.JSONField(default=list)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Contact Upload"
        verbose_name_plural = "Contact Uploads"
    
    def __str__(self):
        return f"{self.agent.name} - {self.uploaded_at.date()}"


class Campaign(models.Model):
    """Campaign model for outbound calling"""
    
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
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='campaigns'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Campaign configuration
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPES,
        default='immediate'
    )
    
    scheduled_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled start date/time"
    )
    
    # Campaign metrics
    total_contacts = models.IntegerField(default=0)
    contacts_called = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    failed_calls = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"
    
    def __str__(self):
        return f"{self.agent.name} - {self.name}"
    
    @property
    def is_active(self):
        """Check if campaign is currently active"""
        return self.status == 'active'
    
    @property
    def success_rate(self):
        """Calculate campaign success rate"""
        if self.contacts_called > 0:
            return round((self.successful_calls / self.contacts_called) * 100, 2)
        return 0.0
    
    @property
    def conversion_rate(self):
        """Calculate conversion rate"""
        if self.contacts_called > 0:
            return round((self.conversions / self.contacts_called) * 100, 2)
        return 0.0


class CallQueue(models.Model):
    """Call queue status for outbound campaigns"""
    
    QUEUE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('paused', 'Paused'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='call_queue'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='queue_entries'
    )
    
    queue_position = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=QUEUE_STATUS_CHOICES,
        default='pending'
    )
    
    scheduled_time = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Call results
    call_duration = models.FloatField(default=0.0)
    call_outcome = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Call Queue Entry"
        verbose_name_plural = "Call Queue Entries"
        ordering = ['queue_position', 'created_at']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.contact.name} (#{self.queue_position})"


class AgentPerformanceMetrics(models.Model):
    """Daily performance metrics for agents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='daily_metrics'
    )
    
    date = models.DateField(default=timezone.now)
    
    # Call metrics
    calls_made = models.IntegerField(default=0)
    calls_answered = models.IntegerField(default=0)
    calls_completed = models.IntegerField(default=0)
    calls_failed = models.IntegerField(default=0)
    
    # Time metrics
    total_talk_time = models.FloatField(default=0.0)  # in minutes
    average_call_duration = models.FloatField(default=0.0)
    
    # Quality metrics
    customer_satisfaction_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    first_call_resolution = models.IntegerField(default=0)
    escalations = models.IntegerField(default=0)
    
    # Conversion metrics
    conversions = models.IntegerField(default=0)
    conversion_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    
    # AI specific metrics (for AI agents)
    ai_confidence_avg = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Agent Performance Metrics"
        verbose_name_plural = "Agent Performance Metrics"
        unique_together = ['agent', 'date']
    
    @property
    def success_rate(self):
        """Calculate daily success rate"""
        if self.calls_made > 0:
            return round((self.calls_completed / self.calls_made) * 100, 2)
        return 0.0
    
    @property
    def conversion_rate(self):
        """Calculate conversion rate"""
        if self.calls_made > 0:
            return round((self.conversions / self.calls_made) * 100, 2)
        return 0.0
    
    def __str__(self):
        return f"{self.agent.name} - {self.date}"