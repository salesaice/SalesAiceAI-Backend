from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class Agent(models.Model):
    """Agent profiles for call center"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('on_call', 'On Call'),
        ('break', 'On Break'),
        ('offline', 'Offline'),
        ('training', 'Training'),
    ]
    
    SKILL_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    
    # Agent details
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=50, blank=True)
    team = models.CharField(max_length=50, blank=True)
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status and availability
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    last_activity = models.DateTimeField(default=timezone.now)
    
    # Skills and capabilities
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='beginner')
    languages = models.JSONField(default=list, blank=True)  # ['en', 'es', 'fr']
    specializations = models.JSONField(default=list, blank=True)  # ['sales', 'support', 'billing']
    
    # Performance metrics
    total_calls = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    average_call_duration = models.FloatField(default=0.0)  # in minutes
    customer_satisfaction = models.FloatField(default=0.0)  # 1-5 rating
    
    # AI assistance preferences
    use_ai_assistance = models.BooleanField(default=True)
    ai_confidence_threshold = models.FloatField(default=0.8)
    preferred_ai_model = models.CharField(max_length=50, default='homeai-standard')
    
    # Twilio configuration
    twilio_worker_sid = models.CharField(max_length=100, blank=True)
    extension_number = models.CharField(max_length=10, blank=True)
    
    is_active = models.BooleanField(default=True)
    hired_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"
    
    @property
    def success_rate(self):
        if self.total_calls > 0:
            return (self.successful_calls / self.total_calls) * 100
        return 0.0
    
    @property
    def is_online(self):
        return self.status != 'offline'


class AgentShift(models.Model):
    """Agent work shifts and schedules"""
    SHIFT_TYPES = [
        ('regular', 'Regular'),
        ('overtime', 'Overtime'),
        ('holiday', 'Holiday'),
        ('weekend', 'Weekend'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='shifts')
    
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPES, default='regular')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # Actual work time
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    
    # Break times
    total_break_time = models.IntegerField(default=0)  # in minutes
    
    # Performance during shift
    calls_handled = models.IntegerField(default=0)
    avg_handle_time = models.FloatField(default=0.0)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.agent.user.get_full_name()} - {self.start_time.date()}"
    
    @property
    def worked_hours(self):
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            return duration.total_seconds() / 3600
        return 0.0


class AgentSkill(models.Model):
    """Agent skills and certifications"""
    SKILL_CATEGORIES = [
        ('technical', 'Technical'),
        ('communication', 'Communication'),
        ('sales', 'Sales'),
        ('support', 'Support'),
        ('language', 'Language'),
        ('product', 'Product Knowledge'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='skills')
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=SKILL_CATEGORIES)
    proficiency_level = models.IntegerField(default=1)  # 1-10 scale
    
    # Certification
    is_certified = models.BooleanField(default=False)
    certification_date = models.DateField(null=True, blank=True)
    certification_expiry = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.agent.user.get_full_name()} - {self.name}"


class HomeAIIntegration(models.Model):
    """HomeAI integration settings and logs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='ai_integrations')
    
    # API Configuration
    api_key = models.CharField(max_length=200, blank=True)
    model_version = models.CharField(max_length=50, default='v1.0')
    
    # Usage settings
    auto_suggestions = models.BooleanField(default=True)
    real_time_assistance = models.BooleanField(default=True)
    sentiment_analysis = models.BooleanField(default=True)
    call_summarization = models.BooleanField(default=True)
    
    # Usage statistics
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    last_request_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"HomeAI - {self.agent.user.get_full_name()}"
    
    @property
    def success_rate(self):
        if self.total_requests > 0:
            return (self.successful_requests / self.total_requests) * 100
        return 0.0


class AgentPerformance(models.Model):
    """Daily agent performance metrics"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='performance_metrics')
    
    date = models.DateField(default=timezone.now)
    
    # Call metrics
    total_calls = models.IntegerField(default=0)
    answered_calls = models.IntegerField(default=0)
    completed_calls = models.IntegerField(default=0)
    average_talk_time = models.FloatField(default=0.0)  # in minutes
    average_hold_time = models.FloatField(default=0.0)  # in minutes
    
    # Quality metrics
    customer_satisfaction = models.FloatField(default=0.0)  # 1-5 rating
    first_call_resolution = models.IntegerField(default=0)
    escalations = models.IntegerField(default=0)
    
    # AI assistance metrics
    ai_suggestions_used = models.IntegerField(default=0)
    ai_accuracy_score = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['agent', 'date']
    
    def __str__(self):
        return f"{self.agent.user.get_full_name()} - {self.date}"

# Import AI Agent models
from .ai_agent_models import (
    AIAgent,
    CustomerProfile,
    CallSession as AICallSession,
    AIAgentTraining,
    ScheduledCallback
)

# Add to __all__ if exists
__all__ = [
    'Agent',
    'AgentPerformance',
    'AIAgent',
    'CustomerProfile', 
    'AICallSession',
    'AIAgentTraining',
    'ScheduledCallback'
]
