from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
import csv
import io
import json
from .models import Agent
from .ai_agent_models import AIAgent, CustomerProfile
from .campaign_models import Campaign, CampaignContact, BusinessKnowledge
from accounts.models import User

User = get_user_model()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def agent_list_page(request):
    """
    Agent List Page - View all agents configured by the subscriber
    """
    user = request.user
    
    # Get all agents for the current user/organization
    if user.role == 'admin':
        # Admin can see all agents
        agents = Agent.objects.select_related('user').all()
        ai_agents = AIAgent.objects.select_related('client').all()
    else:
        # Users can only see their own agents
        agents = Agent.objects.filter(user=user).select_related('user')
        ai_agents = AIAgent.objects.filter(client=user).select_related('client')
    
    # Format human agents data
    human_agents_data = []
    for agent in agents:
        agent_data = {
            'id': str(agent.id),
            'name': agent.user.get_full_name(),
            'email': agent.user.email,
            'employee_id': agent.employee_id,
            'type': 'Human Agent',
            'status': agent.status,
            'department': agent.department,
            'team': agent.team,
            'skill_level': agent.skill_level,
            'languages': agent.languages,
            'specializations': agent.specializations,
            'total_calls': agent.total_calls,
            'successful_calls': agent.successful_calls,
            'average_call_duration': agent.average_call_duration,
            'customer_satisfaction': agent.customer_satisfaction,
            'last_activity': agent.last_activity.isoformat() if agent.last_activity else None,
            'calls_handled': agent.total_calls,
            'active_campaigns': 0,  # Will be calculated later
            'can_edit': True,
            'can_delete': agent.status != 'on_call',
        }
        human_agents_data.append(agent_data)
    
    # Format AI agents data
    ai_agents_data = []
    for ai_agent in ai_agents:
        agent_data = {
            'id': str(ai_agent.id),
            'name': ai_agent.name,
            'email': ai_agent.client.email,
            'employee_id': f'AI-{str(ai_agent.id)[:8]}',
            'type': 'AI Agent',
            'status': ai_agent.status,
            'department': 'AI Operations',
            'team': 'AI Team',
            'skill_level': 'advanced' if ai_agent.training_level > 80 else 'intermediate',
            'languages': ['en'],  # Default for AI
            'specializations': [ai_agent.personality_type],
            'total_calls': ai_agent.calls_handled,
            'successful_calls': ai_agent.successful_conversions,
            'average_call_duration': 0,  # AI agents don't have duration tracking yet
            'customer_satisfaction': 0,  # Will be calculated from feedback
            'last_activity': timezone.now().isoformat(),
            'calls_handled': ai_agent.calls_handled,
            'active_campaigns': 0,  # Will be calculated later
            'can_edit': True,
            'can_delete': ai_agent.status != 'active',
            'training_level': ai_agent.training_level,
            'personality_type': ai_agent.personality_type,
            'voice_model': ai_agent.voice_model,
        }
        ai_agents_data.append(agent_data)
    
    # Combine all agents
    all_agents = human_agents_data + ai_agents_data
    
    # Calculate summary statistics
    total_agents = len(all_agents)
    active_agents = len([a for a in all_agents if a['status'] in ['available', 'on_call', 'active']])
    paused_agents = len([a for a in all_agents if a['status'] in ['offline', 'paused', 'break']])
    human_agents_count = len(human_agents_data)
    ai_agents_count = len(ai_agents_data)
    
    return Response({
        'agents': all_agents,
        'summary': {
            'total_agents': total_agents,
            'active_agents': active_agents,
            'paused_agents': paused_agents,
            'human_agents': human_agents_count,
            'ai_agents': ai_agents_count,
            'avg_calls_per_agent': sum([a['total_calls'] for a in all_agents]) / total_agents if total_agents > 0 else 0,
            'avg_customer_satisfaction': sum([a['customer_satisfaction'] for a in all_agents]) / total_agents if total_agents > 0 else 0
        },
        'filters': {
            'status_options': ['available', 'busy', 'on_call', 'break', 'offline', 'training', 'active', 'paused'],
            'type_options': ['Human Agent', 'AI Agent'],
            'skill_levels': ['beginner', 'intermediate', 'advanced', 'expert'],
            'departments': list(set([a.get('department', '') for a in all_agents if a.get('department')]))
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_edit_agent(request):
    """
    Create/Edit Agent Page - Agent configuration
    """
    user = request.user
    agent_id = request.data.get('agent_id')
    agent_type = request.data.get('agent_type', 'human')  # 'human' or 'ai'
    
    if agent_id:
        # Edit existing agent
        try:
            if agent_type == 'ai':
                agent = AIAgent.objects.get(id=agent_id, client=user)
                is_edit = True
            else:
                if user.role == 'admin':
                    agent = Agent.objects.get(id=agent_id)
                else:
                    agent = Agent.objects.get(id=agent_id, user=user)
                is_edit = True
        except (Agent.DoesNotExist, AIAgent.DoesNotExist):
            return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Create new agent
        is_edit = False
        agent = None
    
    if request.method == 'POST':
        # Handle agent creation/update
        data = request.data
        
        if agent_type == 'ai':
            # Create/Update AI Agent
            if is_edit:
                # Update existing AI agent
                agent.name = data.get('name', agent.name)
                agent.personality_type = data.get('personality_type', agent.personality_type)
                agent.voice_model = data.get('voice_model', agent.voice_model)
                agent.status = data.get('status', agent.status)
                
                # Update business knowledge
                if 'business_knowledge' in data:
                    business_knowledge = agent.conversation_memory.get('business_knowledge', {})
                    business_knowledge.update(data['business_knowledge'])
                    agent.conversation_memory['business_knowledge'] = business_knowledge
                
                # Update sales script
                if 'sales_script' in data:
                    agent.sales_script = data['sales_script']
                
                agent.save()
                message = 'AI Agent updated successfully'
                
            else:
                # Create new AI agent
                agent = AIAgent.objects.create(
                    client=user,
                    name=data.get('name', f'{user.first_name}\'s AI Agent'),
                    personality_type=data.get('personality_type', 'friendly'),
                    voice_model=data.get('voice_model', 'en-US-female-1'),
                    status='training',
                    sales_script=data.get('sales_script', ''),
                    conversation_memory={
                        'business_knowledge': data.get('business_knowledge', {}),
                        'created_at': timezone.now().isoformat()
                    }
                )
                message = 'AI Agent created successfully'
        
        else:
            # Create/Update Human Agent
            if is_edit:
                # Update existing human agent
                agent.employee_id = data.get('employee_id', agent.employee_id)
                agent.department = data.get('department', agent.department)
                agent.team = data.get('team', agent.team)
                agent.status = data.get('status', agent.status)
                agent.skill_level = data.get('skill_level', agent.skill_level)
                agent.languages = data.get('languages', agent.languages)
                agent.specializations = data.get('specializations', agent.specializations)
                agent.save()
                
                # Update user info if provided
                if 'user_info' in data:
                    user_info = data['user_info']
                    agent.user.first_name = user_info.get('first_name', agent.user.first_name)
                    agent.user.last_name = user_info.get('last_name', agent.user.last_name)
                    agent.user.phone = user_info.get('phone', agent.user.phone)
                    agent.user.save()
                
                message = 'Human Agent updated successfully'
                
            else:
                # Create new human agent (requires creating user first)
                user_data = data.get('user_info', {})
                
                # Create user account for the agent
                agent_user = User.objects.create_user(
                    email=user_data.get('email'),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    phone=user_data.get('phone', ''),
                    role='agent',
                    password=user_data.get('password', 'defaultpass123')
                )
                
                # Create agent profile
                agent = Agent.objects.create(
                    user=agent_user,
                    employee_id=data.get('employee_id', f'AGT{Agent.objects.count() + 1:03d}'),
                    department=data.get('department', ''),
                    team=data.get('team', ''),
                    status='offline',
                    skill_level=data.get('skill_level', 'beginner'),
                    languages=data.get('languages', ['en']),
                    specializations=data.get('specializations', [])
                )
                message = 'Human Agent created successfully'
        
        return Response({
            'message': message,
            'agent': {
                'id': str(agent.id),
                'name': agent.name if agent_type == 'ai' else agent.user.get_full_name(),
                'type': agent_type,
                'status': agent.status
            }
        }, status=status.HTTP_201_CREATED if not is_edit else status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def agent_settings(request, agent_id):
    """
    Agent Settings - Common Agent Settings, AI API key config, etc.
    """
    user = request.user
    
    try:
        # Try to get AI agent first
        try:
            agent = AIAgent.objects.get(id=agent_id, client=user)
            agent_type = 'ai'
        except AIAgent.DoesNotExist:
            # Try human agent
            if user.role == 'admin':
                agent = Agent.objects.get(id=agent_id)
            else:
                agent = Agent.objects.get(id=agent_id, user=user)
            agent_type = 'human'
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        # Get current settings
        if agent_type == 'ai':
            settings_data = {
                'agent_id': str(agent.id),
                'agent_name': agent.name,
                'agent_type': 'ai',
                'basic_settings': {
                    'name': agent.name,
                    'status': agent.status,
                    'personality_type': agent.personality_type,
                    'voice_model': agent.voice_model,
                    'training_level': agent.training_level
                },
                'call_handling': {
                    'auto_answer_enabled': True,  # AI agents auto-answer by default
                    'max_call_duration': 30,  # minutes
                    'enable_call_recording': True,
                    'enable_sentiment_analysis': True,
                    'enable_keyword_detection': True
                },
                'ai_configuration': {
                    'homeai_api_key': '***configured***',
                    'voice_tone': agent.personality_type,
                    'response_style': 'conversational',
                    'enable_learning': agent.status == 'learning',
                    'conversation_memory_enabled': True
                },
                'business_knowledge': agent.conversation_memory.get('business_knowledge', {}),
                'sales_script': agent.sales_script,
                'performance_metrics': {
                    'calls_handled': agent.calls_handled,
                    'successful_conversions': agent.successful_conversions,
                    'conversion_rate': (agent.successful_conversions / agent.calls_handled * 100) if agent.calls_handled > 0 else 0
                }
            }
        else:
            settings_data = {
                'agent_id': str(agent.id),
                'agent_name': agent.user.get_full_name(),
                'agent_type': 'human',
                'basic_settings': {
                    'name': agent.user.get_full_name(),
                    'status': agent.status,
                    'skill_level': agent.skill_level,
                    'department': agent.department,
                    'team': agent.team
                },
                'call_handling': {
                    'auto_answer_enabled': False,  # Human agents don't auto-answer
                    'max_call_duration': 60,  # minutes
                    'enable_call_recording': True,
                    'preferred_call_types': ['inbound', 'outbound'],
                    'languages': agent.languages,
                    'specializations': agent.specializations
                },
                'schedule_settings': {
                    'work_hours_start': '09:00',
                    'work_hours_end': '17:00',
                    'timezone': 'UTC',
                    'available_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
                },
                'performance_metrics': {
                    'total_calls': agent.total_calls,
                    'successful_calls': agent.successful_calls,
                    'average_call_duration': agent.average_call_duration,
                    'customer_satisfaction': agent.customer_satisfaction
                }
            }
        
        return Response(settings_data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Update settings
        data = request.data
        
        if agent_type == 'ai':
            # Update AI agent settings
            if 'basic_settings' in data:
                basic = data['basic_settings']
                agent.name = basic.get('name', agent.name)
                agent.status = basic.get('status', agent.status)
                agent.personality_type = basic.get('personality_type', agent.personality_type)
                agent.voice_model = basic.get('voice_model', agent.voice_model)
            
            if 'business_knowledge' in data:
                business_knowledge = agent.conversation_memory.get('business_knowledge', {})
                business_knowledge.update(data['business_knowledge'])
                agent.conversation_memory['business_knowledge'] = business_knowledge
            
            if 'sales_script' in data:
                agent.sales_script = data['sales_script']
            
            agent.save()
            
        else:
            # Update human agent settings
            if 'basic_settings' in data:
                basic = data['basic_settings']
                agent.status = basic.get('status', agent.status)
                agent.skill_level = basic.get('skill_level', agent.skill_level)
                agent.department = basic.get('department', agent.department)
                agent.team = basic.get('team', agent.team)
            
            if 'call_handling' in data:
                call_handling = data['call_handling']
                agent.languages = call_handling.get('languages', agent.languages)
                agent.specializations = call_handling.get('specializations', agent.specializations)
            
            agent.save()
        
        return Response({'message': 'Agent settings updated successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_contacts(request):
    """
    Upload contacts file (CSV) for outbound campaigns
    """
    user = request.user
    
    if 'contacts_file' not in request.FILES:
        return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['contacts_file']
    
    if not file.name.endswith('.csv'):
        return Response({'error': 'Only CSV files are supported'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Read CSV file
        file_data = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_data))
        
        contacts_created = 0
        contacts_updated = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=1):
            try:
                # Expected columns: Name, Phone, Email, Notes, Preferred Time
                name = row.get('Name', '').strip()
                phone = row.get('Phone', '').strip()
                email = row.get('Email', '').strip()
                notes = row.get('Notes', '').strip()
                preferred_time = row.get('Preferred Time', '').strip()
                
                if not name or not phone:
                    errors.append(f'Row {row_num}: Name and Phone are required')
                    continue
                
                # Check if contact already exists
                existing_contact = CustomerProfile.objects.filter(
                    phone_number=phone,
                    ai_agent__client=user
                ).first()
                
                if existing_contact:
                    # Update existing contact
                    existing_contact.name = name
                    existing_contact.email = email or existing_contact.email
                    existing_contact.notes = notes or existing_contact.notes
                    if preferred_time:
                        existing_contact.contact_preferences['preferred_time'] = preferred_time
                    existing_contact.save()
                    contacts_updated += 1
                else:
                    # Create new contact
                    # Get user's AI agent (create one if doesn't exist)
                    ai_agent, created = AIAgent.objects.get_or_create(
                        client=user,
                        defaults={
                            'name': f'{user.first_name}\'s AI Agent',
                            'personality_type': 'friendly',
                            'status': 'training'
                        }
                    )
                    
                    CustomerProfile.objects.create(
                        ai_agent=ai_agent,
                        name=name,
                        phone_number=phone,
                        email=email,
                        notes=notes,
                        lead_status='cold',
                        contact_preferences={
                            'preferred_time': preferred_time,
                            'uploaded_at': timezone.now().isoformat()
                        }
                    )
                    contacts_created += 1
                    
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
        return Response({
            'message': 'Contacts upload completed',
            'summary': {
                'contacts_created': contacts_created,
                'contacts_updated': contacts_updated,
                'total_processed': contacts_created + contacts_updated,
                'errors_count': len(errors)
            },
            'errors': errors[:10]  # Show only first 10 errors
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'File processing error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def schedule_campaign(request):
    """
    Schedule campaign: pick start date/time or start immediately
    """
    user = request.user
    data = request.data
    
    agent_id = data.get('agent_id')
    campaign_name = data.get('campaign_name', 'Untitled Campaign')
    contact_list = data.get('contact_list', [])  # List of contact IDs
    schedule_type = data.get('schedule_type', 'immediate')  # 'immediate' or 'scheduled'
    scheduled_datetime = data.get('scheduled_datetime')  # ISO format datetime
    
    if not agent_id:
        return Response({'error': 'Agent ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not contact_list:
        return Response({'error': 'Contact list cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get the agent
        try:
            agent = AIAgent.objects.get(id=agent_id, client=user)
            agent_type = 'ai'
        except AIAgent.DoesNotExist:
            agent = Agent.objects.get(id=agent_id, user=user)
            agent_type = 'human'
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Validate contacts belong to user
    valid_contacts = CustomerProfile.objects.filter(
        id__in=contact_list,
        ai_agent__client=user
    ).count()
    
    if valid_contacts != len(contact_list):
        return Response({'error': 'Some contacts are invalid or not accessible'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create campaign record
    campaign = Campaign.objects.create(
        name=campaign_name,
        created_by=user,
        assigned_agent_ai=agent if agent_type == 'ai' else None,
        assigned_agent_human=agent if agent_type == 'human' else None,
        schedule_type=schedule_type,
        scheduled_datetime=scheduled_datetime,
        status='scheduled' if schedule_type == 'scheduled' else 'active',
        total_contacts=len(contact_list)
    )
    
    # Add contacts to campaign
    for contact_id in contact_list:
        try:
            customer_profile = CustomerProfile.objects.get(id=contact_id, ai_agent__client=user)
            CampaignContact.objects.create(
                campaign=campaign,
                customer_profile=customer_profile,
                call_status='pending'
            )
        except CustomerProfile.DoesNotExist:
            continue
    
    campaign_data = {
        'id': str(campaign.id),
        'name': campaign.name,
        'agent_id': str(agent_id),
        'agent_name': campaign.assigned_agent_name,
        'agent_type': agent_type,
        'contact_count': campaign.total_contacts,
        'schedule_type': campaign.schedule_type,
        'scheduled_datetime': campaign.scheduled_datetime.isoformat() if campaign.scheduled_datetime else None,
        'status': campaign.status,
        'created_at': campaign.created_at.isoformat(),
        'created_by': user.email
    }
    
    if schedule_type == 'immediate':
        # Start campaign immediately
        message = f'Campaign "{campaign_name}" started immediately with {len(contact_list)} contacts'
        campaign_data['status'] = 'active'
        campaign_data['started_at'] = timezone.now().isoformat()
    else:
        # Schedule for later
        message = f'Campaign "{campaign_name}" scheduled for {scheduled_datetime} with {len(contact_list)} contacts'
        campaign_data['status'] = 'scheduled'
    
    return Response({
        'message': message,
        'campaign': campaign_data
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_agent(request, agent_id):
    """
    Delete Agent - User can remove any agent not currently in an active call/campaign
    """
    user = request.user
    
    try:
        # Try to get AI agent first
        try:
            agent = AIAgent.objects.get(id=agent_id, client=user)
            agent_type = 'ai'
            agent_name = agent.name
        except AIAgent.DoesNotExist:
            # Try human agent
            if user.role == 'admin':
                agent = Agent.objects.get(id=agent_id)
            else:
                agent = Agent.objects.get(id=agent_id, user=user)
            agent_type = 'human'
            agent_name = agent.user.get_full_name()
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if agent can be deleted
    if agent_type == 'ai':
        if agent.status == 'active':
            return Response({'error': 'Cannot delete active AI agent'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        if agent.status == 'on_call':
            return Response({'error': 'Cannot delete agent currently on call'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Delete the agent
    if agent_type == 'ai':
        agent.delete()
    else:
        # For human agents, you might want to deactivate the user account instead
        agent.user.is_active = False
        agent.user.save()
        agent.delete()
    
    return Response({
        'message': f'{agent_type.title()} agent "{agent_name}" deleted successfully'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def call_queue_status(request):
    """
    View call queue (pending/completed) status
    """
    user = request.user
    
    # Get call queue data (you might need to implement a CallQueue model)
    # For now, returning mock data based on existing calls
    from calls.models import CallSession
    
    if user.role == 'admin':
        pending_calls = CallSession.objects.filter(status__in=['initiated', 'ringing']).count()
        completed_calls = CallSession.objects.filter(status='completed').count()
        failed_calls = CallSession.objects.filter(status__in=['failed', 'busy', 'no_answer']).count()
    else:
        user_calls = CallSession.objects.filter(user=user)
        pending_calls = user_calls.filter(status__in=['initiated', 'ringing']).count()
        completed_calls = user_calls.filter(status='completed').count()
        failed_calls = user_calls.filter(status__in=['failed', 'busy', 'no_answer']).count()
    
    return Response({
        'call_queue': {
            'pending_calls': pending_calls,
            'completed_calls': completed_calls,
            'failed_calls': failed_calls,
            'total_calls': pending_calls + completed_calls + failed_calls
        },
        'queue_status': 'normal' if pending_calls < 10 else 'busy'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def campaign_list(request):
    """List all campaigns for the user"""
    user = request.user
    campaigns = Campaign.objects.filter(created_by=user).order_by('-created_at')
    
    campaigns_data = []
    for campaign in campaigns:
        campaign_data = {
            'id': str(campaign.id),
            'name': campaign.name,
            'status': campaign.status,
            'agent_name': campaign.assigned_agent_name,
            'total_contacts': campaign.total_contacts,
            'contacts_called': campaign.contacts_called,
            'successful_calls': campaign.successful_calls,
            'success_rate': campaign.success_rate,
            'completion_rate': campaign.completion_rate,
            'created_at': campaign.created_at.isoformat(),
            'scheduled_datetime': campaign.scheduled_datetime.isoformat() if campaign.scheduled_datetime else None,
        }
        campaigns_data.append(campaign_data)
    
    return Response({
        'campaigns': campaigns_data,
        'total_campaigns': len(campaigns_data),
        'active_campaigns': len([c for c in campaigns_data if c['status'] == 'active']),
        'completed_campaigns': len([c for c in campaigns_data if c['status'] == 'completed'])
    }, status=status.HTTP_200_OK)
