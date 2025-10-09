from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Agent
from .ai_agent_models import AIAgent, CustomerProfile, ScheduledCallback

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information for agent management"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'phone', 'role']


class HumanAgentSerializer(serializers.ModelSerializer):
    """Human agent serializer for management views"""
    user = UserBasicSerializer(read_only=True)
    user_info = serializers.DictField(write_only=True, required=False)
    agent_type = serializers.CharField(default='human', read_only=True)
    
    class Meta:
        model = Agent
        fields = [
            'id', 'user', 'user_info', 'employee_id', 'department', 'team', 
            'status', 'skill_level', 'languages', 'specializations',
            'total_calls', 'successful_calls', 'average_call_duration',
            'customer_satisfaction', 'last_activity', 'agent_type'
        ]
        read_only_fields = ['id', 'total_calls', 'successful_calls', 'average_call_duration', 'customer_satisfaction']


class AIAgentSerializer(serializers.ModelSerializer):
    """AI agent serializer for management views"""
    client = UserBasicSerializer(read_only=True)
    agent_type = serializers.CharField(default='ai', read_only=True)
    conversion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = AIAgent
        fields = [
            'id', 'client', 'name', 'personality_type', 'voice_model',
            'status', 'training_level', 'calls_handled', 'successful_conversions',
            'conversation_memory', 'sales_script', 'agent_type', 'conversion_rate'
        ]
        read_only_fields = ['id', 'calls_handled', 'successful_conversions']
    
    def get_conversion_rate(self, obj):
        if obj.calls_handled > 0:
            return round((obj.successful_conversions / obj.calls_handled) * 100, 2)
        return 0.0


class AgentSettingsSerializer(serializers.Serializer):
    """Serializer for agent settings configuration"""
    agent_id = serializers.UUIDField()
    agent_name = serializers.CharField(read_only=True)
    agent_type = serializers.CharField(read_only=True)
    
    # Basic settings
    basic_settings = serializers.DictField(required=False)
    
    # Call handling settings
    call_handling = serializers.DictField(required=False)
    
    # AI specific settings
    ai_configuration = serializers.DictField(required=False)
    
    # Business knowledge
    business_knowledge = serializers.DictField(required=False)
    
    # Sales script
    sales_script = serializers.CharField(required=False, allow_blank=True)
    
    # Schedule settings (for human agents)
    schedule_settings = serializers.DictField(required=False)
    
    # Performance metrics (read-only)
    performance_metrics = serializers.DictField(read_only=True)


class ContactUploadSerializer(serializers.Serializer):
    """Serializer for contact upload"""
    contacts_file = serializers.FileField()
    
    def validate_contacts_file(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are supported")
        
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 10MB")
        
        return value


class CampaignScheduleSerializer(serializers.Serializer):
    """Serializer for campaign scheduling"""
    agent_id = serializers.UUIDField()
    campaign_name = serializers.CharField(max_length=200)
    contact_list = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of contact IDs to include in campaign"
    )
    schedule_type = serializers.ChoiceField(
        choices=[('immediate', 'Start Immediately'), ('scheduled', 'Schedule for Later')],
        default='immediate'
    )
    scheduled_datetime = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate(self, data):
        if data['schedule_type'] == 'scheduled' and not data.get('scheduled_datetime'):
            raise serializers.ValidationError({
                'scheduled_datetime': 'This field is required when schedule_type is "scheduled"'
            })
        return data


class CustomerProfileListSerializer(serializers.ModelSerializer):
    """Simplified customer profile for list views"""
    ai_agent_name = serializers.CharField(source='ai_agent.name', read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'name', 'phone_number', 'email', 'lead_status',
            'last_contact_date', 'ai_agent_name', 'notes'
        ]


class AgentManagementSummarySerializer(serializers.Serializer):
    """Summary statistics for agent management"""
    total_agents = serializers.IntegerField()
    active_agents = serializers.IntegerField()
    paused_agents = serializers.IntegerField()
    human_agents = serializers.IntegerField()
    ai_agents = serializers.IntegerField()
    avg_calls_per_agent = serializers.FloatField()
    avg_customer_satisfaction = serializers.FloatField()


class AgentFiltersSerializer(serializers.Serializer):
    """Available filters for agent list"""
    status_options = serializers.ListField(child=serializers.CharField())
    type_options = serializers.ListField(child=serializers.CharField())
    skill_levels = serializers.ListField(child=serializers.CharField())
    departments = serializers.ListField(child=serializers.CharField())


class AgentListResponseSerializer(serializers.Serializer):
    """Response serializer for agent list API"""
    agents = serializers.ListField()
    summary = AgentManagementSummarySerializer()
    filters = AgentFiltersSerializer()


class CallQueueStatusSerializer(serializers.Serializer):
    """Call queue status serializer"""
    call_queue = serializers.DictField()
    queue_status = serializers.CharField()


class BusinessKnowledgeSerializer(serializers.Serializer):
    """Business knowledge configuration"""
    company_info = serializers.DictField(required=False)
    products_services = serializers.ListField(required=False)
    pricing_info = serializers.DictField(required=False)
    common_objections = serializers.ListField(required=False)
    contact_information = serializers.DictField(required=False)
    website_url = serializers.URLField(required=False, allow_blank=True)
    business_hours = serializers.DictField(required=False)
    
    def validate(self, data):
        # Add any business knowledge validation logic here
        return data


class VoiceToneConfigSerializer(serializers.Serializer):
    """Voice and tone configuration for AI agents"""
    personality_type = serializers.ChoiceField(
        choices=[
            ('friendly', 'Friendly & Casual'),
            ('professional', 'Professional & Formal'),
            ('persuasive', 'Sales Focused'),
            ('supportive', 'Customer Support'),
            ('custom', 'Custom Trained')
        ]
    )
    voice_model = serializers.CharField(max_length=50)
    response_style = serializers.ChoiceField(
        choices=[
            ('conversational', 'Conversational'),
            ('formal', 'Formal'),
            ('casual', 'Casual'),
            ('professional', 'Professional')
        ],
        default='conversational'
    )
    enable_learning = serializers.BooleanField(default=True)
    conversation_memory_enabled = serializers.BooleanField(default=True)
