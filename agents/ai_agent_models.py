from django.db import models
from django.contrib.auth import get_user_model
import json
import uuid
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class AIAgent(models.Model):
    """
    Dedicated AI Agent for each client - complete sales automation
    Har client ka apna AI agent jo sab kuch handle karta hai
    """
    AGENT_STATUS_CHOICES = [
        ('training', 'Initial Training'),
        ('learning', 'Learning from Calls'),
        ('active', 'Fully Active'),
        ('optimizing', 'Performance Optimizing'),
        ('paused', 'Paused'),
    ]
    
    PERSONALITY_TYPES = [
        ('friendly', 'Friendly & Casual'),
        ('professional', 'Professional & Formal'),
        ('persuasive', 'Sales Focused'),
        ('supportive', 'Customer Support'),
        ('custom', 'Custom Trained'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_agent')
    
    # Agent Identity
    name = models.CharField(max_length=100, help_text="Agent ka naam")
    personality_type = models.CharField(max_length=20, choices=PERSONALITY_TYPES, default='friendly')
    voice_model = models.CharField(max_length=50, default='en-US-female-1')
    
    # Agent Status & Learning
    status = models.CharField(max_length=20, choices=AGENT_STATUS_CHOICES, default='training')
    training_level = models.IntegerField(default=0, help_text="0-100 training completion")
    calls_handled = models.IntegerField(default=0)
    successful_conversions = models.IntegerField(default=0)
    
    # Learning Data
    conversation_memory = models.JSONField(default=dict, help_text="Agent ki memory aur learning")
    customer_preferences = models.JSONField(default=dict, help_text="Customer behavior patterns")
    sales_script = models.TextField(blank=True, help_text="Dynamic sales script")
    
    # Performance Metrics
    conversion_rate = models.FloatField(default=0.0)
    avg_call_duration = models.FloatField(default=0.0)
    customer_satisfaction = models.FloatField(default=0.0)
    
    # Configuration
    working_hours_start = models.TimeField(default='09:00')
    working_hours_end = models.TimeField(default='18:00')
    max_daily_calls = models.IntegerField(default=50)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_agents'
        verbose_name = 'AI Agent'
        verbose_name_plural = 'AI Agents'
    
    def __str__(self):
        return f"{self.name} - {self.client.email}"
    
    @property
    def is_ready_for_calls(self):
        """Check if agent is ready for live calls"""
        return self.status in ['active', 'learning'] and self.training_level >= 20

    def update_learning_data(self, learning_data):
        """
        Automatic learning from call data
        Har call ke baad agent khud ko update karta hai
        """
        current_memory = self.conversation_memory or {}
        
        # Initialize learning structure if not exists
        if 'automatic_learning' not in current_memory:
            current_memory['automatic_learning'] = {
                'total_calls_learned_from': 0,
                'successful_patterns': [],
                'failed_patterns': [],
                'objection_database': {},
                'customer_behavior_insights': {},
                'performance_metrics': {
                    'avg_call_duration': 0,
                    'conversion_trends': [],
                    'best_performing_scripts': [],
                    'sentiment_analysis_history': []
                }
            }
        
        learning = current_memory['automatic_learning']
        
        # Update call count
        learning['total_calls_learned_from'] += 1
        
        # Process successful patterns
        if learning_data.get('successful'):
            pattern = {
                'approach_used': learning_data.get('notes', '')[:200],
                'customer_response': learning_data.get('customer_response', ''),
                'outcome': learning_data.get('outcome'),
                'duration': learning_data.get('call_duration', 0),
                'customer_interest': learning_data.get('customer_interest_level'),
                'timestamp': timezone.now().isoformat(),
                'effectiveness_score': 8 if learning_data.get('outcome') == 'converted' else 6
            }
            learning['successful_patterns'].append(pattern)
            
            # Keep only top 20 successful patterns
            learning['successful_patterns'] = sorted(
                learning['successful_patterns'], 
                key=lambda x: x['effectiveness_score'], 
                reverse=True
            )[:20]
        
        else:
            # Learn from failures too
            failed_pattern = {
                'approach_tried': learning_data.get('notes', '')[:200],
                'customer_response': learning_data.get('customer_response', ''),
                'outcome': learning_data.get('outcome'),
                'what_went_wrong': 'Low customer satisfaction' if learning_data.get('satisfaction', 5) < 4 else 'No interest generated',
                'timestamp': timezone.now().isoformat()
            }
            learning['failed_patterns'].append(failed_pattern)
            
            # Keep only recent 15 failed patterns
            if len(learning['failed_patterns']) > 15:
                learning['failed_patterns'] = learning['failed_patterns'][-15:]
        
        # Save updated memory
        self.conversation_memory = current_memory
        
        # Update agent performance stats
        if learning_data.get('outcome') == 'converted':
            self.successful_conversions += 1
        
        self.calls_handled += 1
        if self.calls_handled > 0:
            self.conversion_rate = (self.successful_conversions / self.calls_handled) * 100
        
        self.save()


class AIAgentTraining(models.Model):
    """
    Training sessions for AI Agent
    Agent ki training sessions aur knowledge base
    """
    TRAINING_TYPES = [
        ('script', 'Sales Script Training'),
        ('objections', 'Objection Handling'),
        ('product', 'Product Knowledge'),
        ('personality', 'Personality Training'),
        ('conversation', 'Conversation Flow'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='training_sessions')
    
    # Training Details
    training_type = models.CharField(max_length=20, choices=TRAINING_TYPES)
    training_data = models.JSONField(help_text="Complete training content")
    
    # Status
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_agent_training'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ai_agent.name} - {self.get_training_type_display()}"


class CustomerProfile(models.Model):
    """
    Customer profiles managed by AI Agent
    AI agent ke customers ki profiles
    """
    INTEREST_LEVELS = [
        ('cold', 'Cold Lead'),
        ('warm', 'Warm Lead'), 
        ('hot', 'Hot Lead'),
        ('converted', 'Converted Customer'),
    ]
    
    COMMUNICATION_STYLES = [
        ('direct', 'Direct & Quick'),
        ('detailed', 'Detailed Discussion'),
        ('friendly', 'Casual & Friendly'),
        ('formal', 'Professional & Formal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='customers')
    
    # Contact Information
    phone_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    
    # Customer Intelligence
    interest_level = models.CharField(max_length=20, choices=INTEREST_LEVELS, default='cold')
    communication_style = models.CharField(max_length=20, choices=COMMUNICATION_STYLES, default='friendly')
    call_preference_time = models.CharField(max_length=50, default='morning', help_text="Best time to call")
    
    # Call History
    total_calls = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    last_interaction = models.DateTimeField(null=True, blank=True)
    next_followup = models.DateTimeField(null=True, blank=True)
    
    # Conversion Tracking
    is_converted = models.BooleanField(default=False)
    conversion_date = models.DateTimeField(null=True, blank=True)
    conversion_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # AI Learning Data
    conversation_history = models.JSONField(default=list, help_text="Conversation patterns and responses")
    objections_raised = models.JSONField(default=list, help_text="Common objections from this customer")
    preferences = models.JSONField(default=dict, help_text="Customer preferences learned by AI")
    
    # Status
    is_do_not_call = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_profiles'
        unique_together = ['ai_agent', 'phone_number']
    
    def __str__(self):
        return f"{self.name or self.phone_number} - {self.get_interest_level_display()}"


class CallSession(models.Model):
    """
    Individual call sessions with learning data
    Har call ka complete record aur learning
    """
    CALL_TYPES = [
        ('inbound', 'Inbound Call'),
        ('outbound', 'Outbound Call'), 
        ('callback', 'Scheduled Callback'),
        ('followup', 'Follow-up Call'),
    ]
    
    CALL_OUTCOMES = [
        ('answered', 'Call Answered'),
        ('voicemail', 'Voicemail Left'),
        ('busy', 'Customer Busy'),
        ('interested', 'Customer Interested'),
        ('callback_requested', 'Callback Requested'),
        ('converted', 'Successfully Converted'),
        ('not_interested', 'Not Interested'),
        ('do_not_call', 'Do Not Call Request'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='call_sessions', null=True, blank=True)
    customer_profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='call_sessions', null=True, blank=True)
    
    # Call Details
    phone_number = models.CharField(max_length=20)
    call_type = models.CharField(max_length=20, choices=CALL_TYPES)
    outcome = models.CharField(max_length=30, choices=CALL_OUTCOMES, default='answered')
    
    # Timing
    initiated_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    # AI Learning Data
    conversation_transcript = models.TextField(blank=True, help_text="Full conversation text")
    customer_sentiment = models.JSONField(default=dict, help_text="HumeAI sentiment analysis")
    agent_performance = models.JSONField(default=dict, help_text="How well agent performed")
    learning_extracted = models.JSONField(default=dict, help_text="What agent learned from this call")
    
    # Follow-up
    followup_scheduled = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    # External Integration
    twilio_call_sid = models.CharField(max_length=100, blank=True)
    hume_conversation_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'call_sessions'
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"{self.call_type} - {self.phone_number} - {self.get_outcome_display()}"
    
    @property
    def duration_formatted(self):
        """Get formatted duration"""
        if self.duration_seconds:
            minutes, seconds = divmod(self.duration_seconds, 60)
            return f"{minutes}:{seconds:02d}"
        return "0:00"


class ScheduledCallback(models.Model):
    """
    Scheduled callbacks by AI Agent
    AI agent ke scheduled callbacks
    """
    CALLBACK_STATUS = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='scheduled_callbacks')
    customer_profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='scheduled_callbacks')
    
    # Scheduling
    scheduled_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=CALLBACK_STATUS, default='scheduled')
    priority_level = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # Context
    reason = models.CharField(max_length=200, help_text="Why this callback was scheduled")
    notes = models.TextField(blank=True)
    expected_outcome = models.CharField(max_length=100, blank=True)
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    actual_outcome = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scheduled_callbacks'
        ordering = ['scheduled_datetime']
    
    def __str__(self):
        return f"Callback - {self.customer_profile.phone_number} - {self.scheduled_datetime}"