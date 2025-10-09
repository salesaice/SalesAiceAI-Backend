from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Agent, 
    BusinessKnowledge, 
    Contact, 
    ContactUpload, 
    Campaign, 
    CallQueue,
    AgentPerformanceMetrics
)

User = get_user_model()


class AgentListSerializer(serializers.ModelSerializer):
    """Serializer for agent list view matching the dashboard design"""
    
    type_display = serializers.CharField(source='get_agent_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    success_rate = serializers.SerializerMethodField()
    active_campaigns_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    can_pause = serializers.SerializerMethodField()
    can_schedule = serializers.SerializerMethodField()
    
    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'agent_type', 'type_display', 'status', 'status_display',
            'calls_handled', 'total_calls', 'successful_calls', 'success_rate',
            'active_campaigns_count', 'voice_tone', 'created_at', 'last_activity',
            'can_edit', 'can_delete', 'can_pause', 'can_schedule'
        ]
    
    def get_success_rate(self, obj):
        """Calculate success rate percentage like in dashboard"""
        if obj.total_calls > 0:
            return f"{round((obj.successful_calls / obj.total_calls) * 100)}%"
        return "0%"
    
    def get_active_campaigns_count(self, obj):
        """Get count of active campaigns for this agent"""
        return obj.campaigns.filter(status='active').count() if hasattr(obj, 'campaigns') else 0
    
    def get_can_edit(self, obj):
        """Check if agent can be edited"""
        return True  # All agents can be edited
    
    def get_can_delete(self, obj):
        """Check if agent can be deleted (not in active call/campaign)"""
        return obj.status != 'active' or self.get_active_campaigns_count(obj) == 0
    
    def get_can_pause(self, obj):
        """Check if agent can be paused"""
        return obj.status == 'active'
    
    def get_can_schedule(self, obj):
        """Check if agent can be scheduled (outbound agents)"""
        return obj.agent_type == 'outbound'


class AgentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating agents with enhanced fields"""
    
    # Clean fields matching AgentCreatePayload interface only
    operating_hours = serializers.JSONField(required=False, default=dict)
    campaign_schedule = serializers.JSONField(required=False, default=dict)
    
    # File fields for multiple knowledge files
    knowledge_files_upload = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        help_text="Upload knowledge files (PDF/DOCX/TXT)"
    )
    
    # Optional file for contacts (outbound only)
    contacts_file = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Upload contacts CSV file (outbound agents only)"
    )
    
    # No extra fields - keeping only AgentCreatePayload interface fields
    
    class Meta:
        model = Agent
        fields = [
            # Core AgentCreatePayload fields only
            'name', 'agent_type', 'status', 'voice_tone', 'operating_hours', 
            'auto_answer_enabled', 'sales_script_file', 'website_url',
            'knowledge_files_upload', 'contacts_file', 'campaign_schedule'
        ]
    
    def validate_name(self, value):
        """Validate agent name is unique for this user"""
        # Skip validation if no request context (for testing)
        if not self.context.get('request'):
            return value
            
        user = self.context['request'].user
        
        # Check for existing agents with same name (excluding current instance if updating)
        queryset = Agent.objects.filter(owner=user, name=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("You already have an agent with this name.")
        
        return value
    
    def validate_agent_type(self, value):
        """Validate agent type based on package limits if needed"""
        # This can be extended to check package limits
        return value
    
    def validate_operating_hours(self, value):
        """Validate operating hours structure"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Operating hours must be an object")
        
        if value and ('start' not in value or 'end' not in value):
            raise serializers.ValidationError("Operating hours must include 'start' and 'end' times")
        
        return value
    
    def validate_campaign_schedule(self, value):
        """Validate campaign schedule structure"""
        if not value:
            return value
            
        if not isinstance(value, dict):
            raise serializers.ValidationError("Campaign schedule must be an object")
        
        schedule_type = value.get('type')
        if schedule_type not in ['immediate', 'scheduled']:
            raise serializers.ValidationError("Campaign schedule type must be 'immediate' or 'scheduled'")
        
        if schedule_type == 'scheduled':
            if 'date' not in value or 'time' not in value:
                raise serializers.ValidationError("Scheduled campaigns must include 'date' and 'time'")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        agent_type = attrs.get('agent_type')
        
        # Auto-answer is only for inbound agents
        if agent_type == 'outbound' and attrs.get('auto_answer_enabled'):
            raise serializers.ValidationError({
                'auto_answer_enabled': 'Auto-answer is only available for inbound agents'
            })
        
        # Contacts file is only for outbound agents
        if agent_type == 'inbound' and 'contacts_file' in attrs:
            raise serializers.ValidationError({
                'contacts_file': 'Contacts file is only for outbound agents'
            })
        
        # Campaign schedule is only for outbound agents
        if agent_type == 'inbound' and attrs.get('campaign_schedule'):
            raise serializers.ValidationError({
                'campaign_schedule': 'Campaign schedule is only for outbound agents'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create new agent with file handling"""
        # Extract files from validated_data
        knowledge_files_upload = validated_data.pop('knowledge_files_upload', [])
        contacts_file = validated_data.pop('contacts_file', None)
        
        # Set owner
        validated_data['owner'] = self.context['request'].user
        
        # Create agent
        agent = super().create(validated_data)
        
        # Handle knowledge files
        if knowledge_files_upload:
            self._create_knowledge_files(agent, knowledge_files_upload)
        
        # Handle contacts file for outbound agents
        if contacts_file and agent.agent_type == 'outbound':
            self._create_contacts_upload(agent, contacts_file)
        
        return agent
    
    def update(self, instance, validated_data):
        """Update agent with file handling"""
        # Extract files from validated_data
        knowledge_files_upload = validated_data.pop('knowledge_files_upload', [])
        contacts_file = validated_data.pop('contacts_file', None)
        
        # Update agent
        agent = super().update(instance, validated_data)
        
        # Handle new knowledge files
        if knowledge_files_upload:
            self._create_knowledge_files(agent, knowledge_files_upload)
        
        # Handle new contacts file for outbound agents
        if contacts_file and agent.agent_type == 'outbound':
            self._create_contacts_upload(agent, contacts_file)
        
        return agent
    
    def _create_knowledge_files(self, agent, knowledge_files):
        """Create BusinessKnowledge entries for uploaded files"""
        for file in knowledge_files:
            BusinessKnowledge.objects.create(
                agent=agent,
                knowledge_file=file,
                title=file.name,
                description=f"Knowledge file: {file.name}"
            )
    
    def _create_contacts_upload(self, agent, contacts_file):
        """Create ContactUpload entry for uploaded contacts file"""
        ContactUpload.objects.create(
            agent=agent,
            contacts_file=contacts_file
        )


class AgentDetailSerializer(serializers.ModelSerializer):
    """Detailed agent serializer"""
    
    type_display = serializers.CharField(source='get_agent_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    business_knowledge_count = serializers.SerializerMethodField()
    contacts_count = serializers.SerializerMethodField()
    active_campaigns_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Agent
        fields = '__all__'
    
    def get_business_knowledge_count(self, obj):
        return obj.business_knowledge.count()
    
    def get_contacts_count(self, obj):
        return obj.contacts.count()
    
    def get_active_campaigns_count(self, obj):
        return obj.campaigns.filter(status='active').count()


class BusinessKnowledgeSerializer(serializers.ModelSerializer):
    """Serializer for business knowledge management"""
    
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    
    class Meta:
        model = BusinessKnowledge
        fields = [
            'id', 'title', 'description', 'website_url', 'knowledge_file',
            'file_type', 'file_type_display', 'knowledge_text', 'is_processed',
            'created_at', 'updated_at'
        ]


class ContactSerializer(serializers.ModelSerializer):
    """Serializer for contact management"""
    
    status_display = serializers.CharField(source='get_call_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Contact
        fields = [
            'id', 'name', 'phone', 'email', 'notes', 'preferred_call_time',
            'call_status', 'status_display', 'priority', 'priority_display',
            'call_attempts', 'last_call_attempt', 'next_call_scheduled',
            'call_outcome', 'conversion_achieved', 'created_at'
        ]


class ContactUploadSerializer(serializers.ModelSerializer):
    """Serializer for contact file uploads"""
    
    class Meta:
        model = ContactUpload
        fields = [
            'id', 'contacts_file', 'is_processed', 'processing_status',
            'contacts_imported', 'errors_encountered', 'uploaded_at', 'processed_at'
        ]
        read_only_fields = [
            'is_processed', 'processing_status', 'contacts_imported',
            'errors_encountered', 'processed_at'
        ]
    
    def validate_contacts_file(self, value):
        """Validate uploaded file is CSV"""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are allowed.")
        return value


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for campaign management"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    schedule_type_display = serializers.CharField(source='get_schedule_type_display', read_only=True)
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'description', 'status', 'status_display',
            'schedule_type', 'schedule_type_display', 'scheduled_start',
            'total_contacts', 'contacts_called', 'successful_calls',
            'failed_calls', 'conversions', 'success_rate', 'conversion_rate',
            'created_at', 'started_at', 'completed_at'
        ]


class CallQueueSerializer(serializers.ModelSerializer):
    """Serializer for call queue status"""
    
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CallQueue
        fields = [
            'id', 'queue_position', 'status', 'status_display',
            'contact_name', 'contact_phone', 'scheduled_time',
            'started_at', 'completed_at', 'call_duration',
            'call_outcome', 'notes'
        ]


class AgentPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for agent performance metrics"""
    
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    
    class Meta:
        model = AgentPerformanceMetrics
        fields = [
            'id', 'agent_name', 'date', 'calls_made', 'calls_answered',
            'calls_completed', 'calls_failed', 'total_talk_time',
            'average_call_duration', 'customer_satisfaction_score',
            'first_call_resolution', 'escalations', 'conversions',
            'conversion_value', 'success_rate', 'conversion_rate',
            'ai_confidence_avg'
        ]


class AgentSummarySerializer(serializers.Serializer):
    """Serializer for agent management summary statistics"""
    
    total_agents = serializers.IntegerField()
    active_agents = serializers.IntegerField()
    paused_agents = serializers.IntegerField()
    inbound_agents = serializers.IntegerField()
    outbound_agents = serializers.IntegerField()
    ai_agents = serializers.IntegerField()
    human_agents = serializers.IntegerField()
    total_calls_today = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()


class OperatingHoursSerializer(serializers.Serializer):
    """Serializer for operating hours configuration"""
    
    monday_start = serializers.TimeField(required=False, allow_null=True)
    monday_end = serializers.TimeField(required=False, allow_null=True)
    tuesday_start = serializers.TimeField(required=False, allow_null=True)
    tuesday_end = serializers.TimeField(required=False, allow_null=True)
    wednesday_start = serializers.TimeField(required=False, allow_null=True)
    wednesday_end = serializers.TimeField(required=False, allow_null=True)
    thursday_start = serializers.TimeField(required=False, allow_null=True)
    thursday_end = serializers.TimeField(required=False, allow_null=True)
    friday_start = serializers.TimeField(required=False, allow_null=True)
    friday_end = serializers.TimeField(required=False, allow_null=True)
    saturday_start = serializers.TimeField(required=False, allow_null=True)
    saturday_end = serializers.TimeField(required=False, allow_null=True)
    sunday_start = serializers.TimeField(required=False, allow_null=True)
    sunday_end = serializers.TimeField(required=False, allow_null=True)
    timezone = serializers.CharField(default='UTC')