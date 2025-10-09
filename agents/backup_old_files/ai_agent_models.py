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
    
    def update_learning_data(self, call_data):
        """Update agent learning from call experience"""
        # Add call insights to memory
        if 'learning_insights' not in self.conversation_memory:
            self.conversation_memory['learning_insights'] = []
        
        self.conversation_memory['learning_insights'].append({
            'timestamp': datetime.now().isoformat(),
            'call_outcome': call_data.get('outcome'),
            'customer_response': call_data.get('customer_response'),
            'improvement_notes': call_data.get('notes')
        })
        
        # Update performance
        self.calls_handled += 1
        if call_data.get('outcome') == 'successful':
            self.successful_conversions += 1
        
        self.conversion_rate = (self.successful_conversions / self.calls_handled) * 100
        self.save()

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
        
        # Update performance metrics
        metrics = learning['performance_metrics']
        
        # Update average call duration
        current_avg = metrics['avg_call_duration']
        new_duration = learning_data.get('call_duration', 0)
        total_calls = learning['total_calls_learned_from']
        
        metrics['avg_call_duration'] = ((current_avg * (total_calls - 1)) + new_duration) / total_calls
        
        # Track conversion trends (last 10 calls)
        conversion_trends = metrics['conversion_trends']
        conversion_trends.append({
            'call_number': total_calls,
            'converted': learning_data.get('successful', False),
            'satisfaction': learning_data.get('satisfaction', 5),
            'date': timezone.now().isoformat()
        })
        
        # Keep only last 10 trends
        if len(conversion_trends) > 10:
            metrics['conversion_trends'] = conversion_trends[-10:]
        
        # Update sentiment analysis history
        if learning_data.get('satisfaction'):
            metrics['sentiment_analysis_history'].append({
                'satisfaction_score': learning_data.get('satisfaction'),
                'customer_interest': learning_data.get('customer_interest_level'),
                'call_outcome': learning_data.get('outcome'),
                'timestamp': timezone.now().isoformat()
            })
            
            # Keep only last 20 sentiment records
            if len(metrics['sentiment_analysis_history']) > 20:
                metrics['sentiment_analysis_history'] = metrics['sentiment_analysis_history'][-20:]
        
        # Save updated memory
        self.conversation_memory = current_memory
        
        # Update agent performance stats
        self.calls_handled += 1
        if learning_data.get('successful'):
            self.successful_calls += 1
        
        self.save()
        
        return learning
    
    def get_learning_recommendations(self):
        """
        Agent ke learning data se recommendations generate karna
        """
        if not self.conversation_memory or 'automatic_learning' not in self.conversation_memory:
            return []
        
        learning = self.conversation_memory['automatic_learning']
        recommendations = []
        
        # Analyze success patterns
        successful_patterns = learning.get('successful_patterns', [])
        if len(successful_patterns) >= 3:
            best_pattern = max(successful_patterns, key=lambda x: x['effectiveness_score'])
            recommendations.append({
                'type': 'success_replication',
                'message': f"Your most effective approach: '{best_pattern['approach_used'][:50]}...' - Use this pattern more often",
                'priority': 'high'
            })
        
        # Analyze failed patterns
        failed_patterns = learning.get('failed_patterns', [])
        if len(failed_patterns) >= 2:
            common_failure = failed_patterns[-1]  # Most recent failure
            recommendations.append({
                'type': 'failure_avoidance',
                'message': f"Avoid approach that led to: '{common_failure['what_went_wrong']}' - Try alternative strategies",
                'priority': 'medium'
            })
        
        # Analyze conversion trends
        trends = learning.get('performance_metrics', {}).get('conversion_trends', [])
        if len(trends) >= 5:
            recent_success_rate = sum(1 for t in trends[-5:] if t['converted']) / 5
            if recent_success_rate < 0.2:  # Less than 20% success in last 5 calls
                recommendations.append({
                    'type': 'performance_improvement',
                    'message': 'Your recent conversion rate is low. Consider adjusting your approach or script',
                    'priority': 'high'
                })
            elif recent_success_rate > 0.6:  # More than 60% success
                recommendations.append({
                    'type': 'performance_excellence',
                    'message': 'Excellent performance! Your current approach is working very well',
                    'priority': 'low'
                })
        
        # Analyze customer satisfaction
        sentiment_history = learning.get('performance_metrics', {}).get('sentiment_analysis_history', [])
        if len(sentiment_history) >= 3:
            avg_satisfaction = sum(s['satisfaction_score'] for s in sentiment_history[-3:]) / 3
            if avg_satisfaction < 3:
                recommendations.append({
                    'type': 'customer_satisfaction',
                    'message': 'Customer satisfaction is low. Focus on being more empathetic and less pushy',
                    'priority': 'high'
                })
        
        return recommendations
    
    def auto_adjust_strategy(self):
        """
        Agent apni strategy automatically adjust karta hai
        Learning data ke base par
        """
        if not self.conversation_memory or 'automatic_learning' not in self.conversation_memory:
            return False
        
        learning = self.conversation_memory['automatic_learning']
        
        # Get successful patterns
        successful_patterns = learning.get('successful_patterns', [])
        
        if len(successful_patterns) >= 3:
            # Find most effective pattern
            best_pattern = max(successful_patterns, key=lambda x: x['effectiveness_score'])
            
            # Update agent's default approach based on successful pattern
            memory = self.conversation_memory
            
            if 'adaptive_strategy' not in memory:
                memory['adaptive_strategy'] = {}
            
            memory['adaptive_strategy'].update({
                'primary_approach': best_pattern['approach_used'],
                'target_call_duration': best_pattern['duration'],
                'effective_with_interest_level': best_pattern['customer_interest'],
                'last_strategy_update': timezone.now().isoformat(),
                'confidence_level': min(len(successful_patterns) * 10, 100)  # Max 100%
            })
            
            self.conversation_memory = memory
            self.save()
            
            return True
        
        return False
    
    def get_personalized_script_for_customer(self, customer_profile):
        """
        Customer ke profile ke according personalized script generate karna
        """
        if not self.conversation_memory:
            return self.sales_script or "Hello, this is a sales call."
        
        learning = self.conversation_memory.get('automatic_learning', {})
        successful_patterns = learning.get('successful_patterns', [])
        
        # Find patterns that worked for similar customers
        matching_patterns = [
            pattern for pattern in successful_patterns
            if pattern['customer_interest'] == customer_profile.interest_level
        ]
        
        if matching_patterns:
            # Use the most effective pattern for similar customers
            best_match = max(matching_patterns, key=lambda x: x['effectiveness_score'])
            personalized_script = f"""
            Hello {customer_profile.name or 'there'}, 
            
            {best_match['approach_used']}
            
            Based on our previous successful conversations with customers like you, 
            I believe this could be exactly what you're looking for.
            """
            return personalized_script.strip()
        
        # Fallback to general successful pattern
        elif successful_patterns:
            general_best = max(successful_patterns, key=lambda x: x['effectiveness_score'])
            return f"Hello {customer_profile.name or 'there'}, {general_best['approach_used']}"
        
        # Final fallback
        return f"Hello {customer_profile.name or 'there'}, " + (self.sales_script or "I'm calling about an opportunity that might interest you.")

class CustomerProfile(models.Model):
    """
    Customer profile maintained by AI Agent
    Agent har customer ka detailed profile maintain karta hai
    """
    INTEREST_LEVELS = [
        ('cold', 'Not Interested'),
        ('warm', 'Somewhat Interested'),
        ('hot', 'Very Interested'),
        ('converted', 'Purchased'),
    ]
    
    CALL_PREFERENCES = [
        ('morning', 'Morning (9-12)'),
        ('afternoon', 'Afternoon (12-17)'),
        ('evening', 'Evening (17-20)'),
        ('anytime', 'Anytime'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='customer_profiles')
    
    # Customer Info
    phone_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    
    # Behavioral Data
    interest_level = models.CharField(max_length=20, choices=INTEREST_LEVELS, default='warm')
    call_preference_time = models.CharField(max_length=20, choices=CALL_PREFERENCES, default='anytime')
    communication_style = models.CharField(max_length=50, blank=True, help_text="Formal, casual, etc")
    
    # Interaction History
    total_calls = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    last_interaction = models.DateTimeField(null=True, blank=True)
    next_followup = models.DateTimeField(null=True, blank=True)
    
    # Learning Data
    conversation_notes = models.JSONField(default=dict)
    preferences = models.JSONField(default=dict, help_text="Customer ki pasand, requirements")
    objections = models.JSONField(default=list, help_text="Customer ke objections aur responses")
    
    # Status
    is_do_not_call = models.BooleanField(default=False)
    is_converted = models.BooleanField(default=False)
    conversion_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_profiles'
        unique_together = ['ai_agent', 'phone_number']
    
    def __str__(self):
        return f"{self.name or self.phone_number} - {self.interest_level}"
    
    def schedule_callback(self, callback_time):
        """Schedule next callback"""
        self.next_followup = callback_time
        self.save()
    
    def update_interaction(self, call_outcome, notes=None):
        """Update customer interaction data"""
        self.total_calls += 1
        self.last_interaction = datetime.now()
        
        if call_outcome == 'successful':
            self.successful_calls += 1
        elif call_outcome == 'converted':
            self.is_converted = True
            self.conversion_date = datetime.now()
            self.interest_level = 'converted'
        
        if notes:
            if 'call_notes' not in self.conversation_notes:
                self.conversation_notes['call_notes'] = []
            self.conversation_notes['call_notes'].append({
                'date': datetime.now().isoformat(),
                'outcome': call_outcome,
                'notes': notes
            })
        
        self.save()


class CallSession(models.Model):
    """
    Enhanced Call Session with AI Agent integration
    """
    CALL_TYPES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('scheduled', 'Scheduled Callback'),
        ('followup', 'Follow-up'),
    ]
    
    CALL_OUTCOMES = [
        ('answered', 'Call Answered'),
        ('no_answer', 'No Answer'),
        ('busy', 'Line Busy'),
        ('interested', 'Customer Interested'),
        ('callback_requested', 'Callback Requested'),
        ('not_interested', 'Not Interested'),
        ('converted', 'Sale Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='call_sessions')
    customer_profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='call_sessions')
    
    # Call Details
    call_type = models.CharField(max_length=20, choices=CALL_TYPES)
    phone_number = models.CharField(max_length=20)
    
    # Timing
    initiated_at = models.DateTimeField(auto_now_add=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    # Call Outcome
    outcome = models.CharField(max_length=30, choices=CALL_OUTCOMES)
    customer_response = models.TextField(blank=True)
    agent_notes = models.TextField(blank=True)
    
    # AI Generated Data
    conversation_transcript = models.TextField(blank=True)
    sentiment_analysis = models.JSONField(default=dict)
    extracted_insights = models.JSONField(default=dict)
    
    # Follow-up
    followup_scheduled = models.BooleanField(default=False)
    followup_datetime = models.DateTimeField(null=True, blank=True)
    followup_reason = models.CharField(max_length=200, blank=True)
    
    # Twilio Integration
    twilio_call_sid = models.CharField(max_length=100, blank=True)
    recording_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_call_sessions'
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"{self.phone_number} - {self.outcome} - {self.initiated_at.date()}"
    
    @property
    def duration_formatted(self):
        """Format duration in MM:SS"""
        if self.duration_seconds:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"


class AIAgentTraining(models.Model):
    """
    Training sessions and data for AI Agent
    """
    TRAINING_TYPES = [
        ('initial', 'Initial Setup Training'),
        ('script', 'Sales Script Training'),
        ('objection_handling', 'Objection Handling'),
        ('product_knowledge', 'Product Knowledge'),
        ('real_time', 'Real-time Learning'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='training_sessions')
    
    training_type = models.CharField(max_length=30, choices=TRAINING_TYPES)
    training_data = models.JSONField(help_text="Training content and scripts")
    completion_percentage = models.IntegerField(default=0)
    
    # Client provided training
    client_instructions = models.TextField(blank=True, help_text="Client ke instructions")
    sales_goals = models.JSONField(default=dict, help_text="Sales targets aur goals")
    product_info = models.JSONField(default=dict, help_text="Product/service details")
    
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_agent_training'
    
    def __str__(self):
        return f"{self.ai_agent.name} - {self.training_type}"


class ScheduledCallback(models.Model):
    """
    Scheduled callbacks managed by AI Agent
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rescheduled', 'Rescheduled'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='scheduled_callbacks')
    customer_profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE)
    
    scheduled_datetime = models.DateTimeField()
    reason = models.CharField(max_length=200, help_text="Callback ka reason")
    notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    completed_at = models.DateTimeField(null=True, blank=True)
    rescheduled_from = models.DateTimeField(null=True, blank=True)
    
    # Auto-generated by AI
    priority_level = models.IntegerField(default=1, help_text="1-5 priority")
    expected_outcome = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scheduled_callbacks'
        ordering = ['scheduled_datetime']
    
    def __str__(self):
        return f"Callback: {self.customer_profile.phone_number} - {self.scheduled_datetime}"
