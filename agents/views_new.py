from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import csv
import io
from datetime import datetime, timedelta

from .models_new import (
    Agent, 
    BusinessKnowledge, 
    Contact, 
    ContactUpload, 
    Campaign, 
    CallQueue,
    AgentPerformanceMetrics
)
from .serializers_new import (
    AgentListSerializer,
    AgentCreateUpdateSerializer,
    AgentDetailSerializer,
    BusinessKnowledgeSerializer,
    ContactSerializer,
    ContactUploadSerializer,
    CampaignSerializer,
    CallQueueSerializer,
    AgentSummarySerializer,
    AgentPerformanceSerializer
)
from .subscription_utils import (
    get_subscription_summary,
    can_create_agent,
    validate_agent_creation,
    SubscriptionLimitError
)

User = get_user_model()


# Agent List Page (User)
@swagger_auto_schema(
    method='get',
    responses={200: AgentListSerializer(many=True)},
    operation_description="Get all agents configured by the subscriber",
    tags=['Agent Management']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def agent_list_page(request):
    """
    Agent List Page - See all agents configured by the subscriber.
    For each: Name, Type (Inbound/Outbound), Status (Active/Paused), Calls Handled.
    """
    user = request.user
    
    # Get user's agents
    agents = Agent.objects.filter(owner=user).select_related('owner')
    
    # Apply filters if provided
    agent_type = request.GET.get('type')
    status_filter = request.GET.get('status')
    
    if agent_type:
        agents = agents.filter(agent_type=agent_type)
    if status_filter:
        agents = agents.filter(status=status_filter)
    
    # Serialize agent data
    serializer = AgentListSerializer(agents, many=True)
    
    # Calculate dashboard statistics matching the image
    total_agents = agents.count()
    active_agents = agents.filter(status='active').count()
    
    # Calculate total calls and success rate
    total_calls = sum(agent.total_calls for agent in agents)
    total_successful = sum(agent.successful_calls for agent in agents)
    avg_success_rate = round((total_successful / total_calls * 100)) if total_calls > 0 else 0
    
    # Get subscription and limit information
    subscription_info = get_subscription_summary(user)
    
    # Dashboard stats matching the UI
    dashboard_stats = {
        'total_agents': total_agents,
        'active_agents': active_agents,
        'total_calls': total_calls,
        'avg_success_rate': f"{avg_success_rate}%",
        'agents_allowed': subscription_info['limits']['agents_allowed'],
        'remaining_agents': subscription_info['remaining_agents'],
        'usage_percentage': subscription_info['usage_percentage'],
        'can_create_more': subscription_info['can_create_more']
    }
    
    return Response({
        'success': True,
        'dashboard_stats': dashboard_stats,
        'agents': serializer.data,
        'filters': {
            'agent_types': [{'value': key, 'label': value} for key, value in Agent.AGENT_TYPES],
            'statuses': [{'value': key, 'label': value} for key, value in Agent.STATUS_CHOICES]
        }
    })


# Create/Edit Agent Page
@swagger_auto_schema(
    method='post',
    request_body=AgentCreateUpdateSerializer,
    responses={201: AgentDetailSerializer},
    operation_description="Create a new agent",
    tags=['Agent Management']
)
@swagger_auto_schema(
    method='put',
    request_body=AgentCreateUpdateSerializer,
    responses={200: AgentDetailSerializer},
    operation_description="Update existing agent",
    tags=['Agent Management']
)
@api_view(['POST', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_edit_agent(request):
    """
    Create/Edit Agent Page with common settings:
    - Name, Agent Type (Inbound/Outbound), Status (Active/Paused)
    - Hume AI API key/config
    - Voice/tone selection
    - Operating hours (time windows for agent to work)
    - Enable/disable auto-answer (for inbound)
    - Upload sales script/template (file upload)
    """
    if request.method == 'POST':
        # Create new agent following AgentCreatePayload structure
        try:
            # Check subscription limits before creating agent
            agent_type = request.data.get('agent_type', 'inbound')
            try:
                validate_agent_creation(request.user, agent_type)
            except SubscriptionLimitError as e:
                return Response({
                    'success': False,
                    'message': str(e),
                    'error_type': 'subscription_limit',
                    'subscription_info': get_subscription_summary(request.user)
                }, status=status.HTTP_403_FORBIDDEN)
            serializer = AgentCreateUpdateSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                agent = serializer.save()
                detail_serializer = AgentDetailSerializer(agent)
                
                return Response({
                    'success': True,
                    'message': f'{agent.get_agent_type_display()} agent "{agent.name}" created successfully',
                    'agent': detail_serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error creating agent: {str(e)}',
                'errors': {'general': [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'PUT':
        # Update existing agent
        agent_id = request.data.get('id')
        if not agent_id:
            return Response({
                'success': False,
                'message': 'Agent ID is required for updates',
                'errors': {'id': ['Agent ID is required']}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            agent = Agent.objects.get(id=agent_id, owner=request.user)
        except Agent.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Agent not found',
                'errors': {'agent': ['Agent not found or access denied']}
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            serializer = AgentCreateUpdateSerializer(
                agent,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                updated_agent = serializer.save()
                detail_serializer = AgentDetailSerializer(updated_agent)
                
                return Response({
                    'success': True,
                    'message': f'{updated_agent.get_agent_type_display()} agent "{updated_agent.name}" updated successfully',
                    'agent': detail_serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error updating agent: {str(e)}',
                'errors': {'general': [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Agent Settings
@swagger_auto_schema(
    method='get',
    responses={200: AgentDetailSerializer},
    operation_description="Get agent settings and configuration",
    tags=['Agent Management']
)
@swagger_auto_schema(
    method='post',
    request_body=AgentCreateUpdateSerializer,
    responses={200: AgentDetailSerializer},
    operation_description="Update agent settings",
    tags=['Agent Management']
)
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def agent_settings(request, agent_id):
    """Agent settings configuration page"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = AgentDetailSerializer(agent)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = AgentCreateUpdateSerializer(
            agent,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            agent = serializer.save()
            detail_serializer = AgentDetailSerializer(agent)
            return Response(detail_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete Agent
@swagger_auto_schema(
    method='delete',
    responses={204: 'Agent deleted successfully'},
    operation_description="Delete agent (if not in active call/campaign)",
    tags=['Agent Management']
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_agent(request, agent_id):
    """
    Delete Agent - User can remove any agent not currently in an active call/campaign
    """
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if agent can be deleted
    if not agent.can_delete:
        return Response({
            'error': 'Cannot delete agent that is currently in an active call or campaign'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check for active campaigns
    active_campaigns = agent.campaigns.filter(status='active')
    if active_campaigns.exists():
        return Response({
            'error': 'Cannot delete agent with active campaigns. Please complete or cancel active campaigns first.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    agent.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# Business Knowledge Section
@swagger_auto_schema(
    method='get',
    responses={200: BusinessKnowledgeSerializer(many=True)},
    operation_description="Get business knowledge items for agent",
    tags=['Agent Management']
)
@swagger_auto_schema(
    method='post',
    request_body=BusinessKnowledgeSerializer,
    responses={201: BusinessKnowledgeSerializer},
    operation_description="Add business knowledge item",
    tags=['Agent Management']
)
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def business_knowledge(request, agent_id):
    """
    Business Knowledge Section:
    - Website link (URL field)
    - Upload text / pdf / docx files for business knowledge
    """
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        knowledge_items = agent.business_knowledge.all()
        serializer = BusinessKnowledgeSerializer(knowledge_items, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = BusinessKnowledgeSerializer(data=request.data)
        if serializer.is_valid():
            knowledge_item = serializer.save(agent=agent)
            return Response(
                BusinessKnowledgeSerializer(knowledge_item).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# For Outbound Agents Only - Upload Contacts
@swagger_auto_schema(
    method='post',
    request_body=ContactUploadSerializer,
    responses={201: ContactUploadSerializer},
    operation_description="Upload contacts file (CSV: Name, Phone, Notes, Preferred Time)",
    tags=['Agent Management']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_contacts(request, agent_id):
    """
    For Outbound Agents Only:
    Upload contacts file (CSV: Name, Phone, Notes, Preferred Time)
    """
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if agent.agent_type != 'outbound':
        return Response({
            'error': 'Contact upload is only available for outbound agents'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ContactUploadSerializer(data=request.data)
    if serializer.is_valid():
        contact_upload = serializer.save(agent=agent)
        
        # Process the CSV file
        try:
            process_contact_upload(contact_upload)
        except Exception as e:
            return Response({
                'error': f'Error processing contact file: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            ContactUploadSerializer(contact_upload).data,
            status=status.HTTP_201_CREATED
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def process_contact_upload(contact_upload):
    """Process uploaded contact CSV file"""
    try:
        file_content = contact_upload.contacts_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        contacts_created = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header
            try:
                # Required fields
                name = row.get('Name', '').strip()
                phone = row.get('Phone', '').strip()
                
                if not name or not phone:
                    errors.append(f"Row {row_num}: Name and Phone are required")
                    continue
                
                # Optional fields
                email = row.get('Email', '').strip()
                notes = row.get('Notes', '').strip()
                preferred_time = row.get('Preferred Time', '').strip()
                
                # Create or update contact
                contact, created = Contact.objects.get_or_create(
                    agent=contact_upload.agent,
                    phone=phone,
                    defaults={
                        'name': name,
                        'email': email,
                        'notes': notes,
                        'preferred_call_time': preferred_time
                    }
                )
                
                if created:
                    contacts_created += 1
                else:
                    # Update existing contact
                    contact.name = name
                    contact.email = email
                    contact.notes = notes
                    contact.preferred_call_time = preferred_time
                    contact.save()
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # Update upload record
        contact_upload.is_processed = True
        contact_upload.contacts_imported = contacts_created
        contact_upload.errors_encountered = errors
        contact_upload.processing_status = f"Imported {contacts_created} contacts"
        contact_upload.processed_at = timezone.now()
        contact_upload.save()
        
    except Exception as e:
        contact_upload.processing_status = f"Error: {str(e)}"
        contact_upload.save()
        raise e


# Schedule Campaign
@swagger_auto_schema(
    method='post',
    request_body=CampaignSerializer,
    responses={201: CampaignSerializer},
    operation_description="Schedule campaign: pick start date/time or start immediately",
    tags=['Agent Management']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def schedule_campaign(request, agent_id):
    """
    Schedule campaign: pick start date/time or start immediately
    """
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if agent.agent_type != 'outbound':
        return Response({
            'error': 'Campaigns are only available for outbound agents'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = CampaignSerializer(data=request.data)
    if serializer.is_valid():
        campaign = serializer.save(agent=agent)
        
        # Count available contacts
        available_contacts = agent.contacts.filter(call_status='pending').count()
        campaign.total_contacts = available_contacts
        campaign.save()
        
        # If immediate start, update status
        if campaign.schedule_type == 'immediate':
            campaign.status = 'active'
            campaign.started_at = timezone.now()
            campaign.save()
        
        return Response(
            CampaignSerializer(campaign).data,
            status=status.HTTP_201_CREATED
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View Call Queue Status
@swagger_auto_schema(
    method='get',
    responses={200: CallQueueSerializer(many=True)},
    operation_description="View call queue (pending/completed), status",
    tags=['Agent Management']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def call_queue_status(request, agent_id):
    """
    View call queue (pending/completed), status
    """
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get active campaigns
    active_campaigns = agent.campaigns.filter(status='active')
    
    if not active_campaigns.exists():
        return Response({
            'message': 'No active campaigns for this agent',
            'queue': []
        })
    
    # Get call queue for active campaigns
    queue_entries = CallQueue.objects.filter(
        campaign__in=active_campaigns
    ).select_related('contact', 'campaign').order_by('queue_position')
    
    # Apply status filter if provided
    status_filter = request.GET.get('status')
    if status_filter:
        queue_entries = queue_entries.filter(status=status_filter)
    
    serializer = CallQueueSerializer(queue_entries, many=True)
    
    # Calculate queue statistics
    total_queue = queue_entries.count()
    pending_count = queue_entries.filter(status='pending').count()
    in_progress_count = queue_entries.filter(status='in_progress').count()
    completed_count = queue_entries.filter(status='completed').count()
    
    return Response({
        'queue': serializer.data,
        'statistics': {
            'total': total_queue,
            'pending': pending_count,
            'in_progress': in_progress_count,
            'completed': completed_count
        }
    })


# Agent Performance Dashboard
@swagger_auto_schema(
    method='get',
    responses={200: AgentPerformanceSerializer(many=True)},
    operation_description="Get agent performance metrics",
    tags=['Agent Management']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def agent_performance(request, agent_id):
    """Get agent performance metrics"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get date range
    days = int(request.GET.get('days', 7))  # Default to 7 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    metrics = AgentPerformanceMetrics.objects.filter(
        agent=agent,
        date__range=[start_date, end_date]
    ).order_by('-date')
    
    serializer = AgentPerformanceSerializer(metrics, many=True)
    return Response(serializer.data)


# Additional API Views

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def bulk_delete_agents(request):
    """Bulk delete agents"""
    agent_ids = request.data.get('agent_ids', [])
    if not agent_ids:
        return Response({
            'error': 'No agent IDs provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    agents = Agent.objects.filter(id__in=agent_ids, owner=request.user)
    deleted_count = 0
    errors = []
    
    for agent in agents:
        if agent.can_delete:
            agent.delete()
            deleted_count += 1
        else:
            errors.append(f"Cannot delete agent '{agent.name}' - has active campaigns")
    
    return Response({
        'deleted_count': deleted_count,
        'errors': errors
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_update_status(request):
    """Bulk update agent status"""
    agent_ids = request.data.get('agent_ids', [])
    new_status = request.data.get('status')
    
    if not agent_ids or not new_status:
        return Response({
            'error': 'Agent IDs and status are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    agents = Agent.objects.filter(id__in=agent_ids, owner=request.user)
    updated_count = agents.update(status=new_status)
    
    return Response({
        'updated_count': updated_count
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_campaigns(request):
    """List all campaigns for user's agents"""
    campaigns = Campaign.objects.filter(agent__owner=request.user)
    
    # Apply filters
    status_filter = request.GET.get('status')
    agent_id = request.GET.get('agent_id')
    
    if status_filter:
        campaigns = campaigns.filter(status=status_filter)
    if agent_id:
        campaigns = campaigns.filter(agent_id=agent_id)
    
    serializer = CampaignSerializer(campaigns, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def campaign_detail(request, campaign_id):
    """Campaign detail operations"""
    try:
        campaign = Campaign.objects.get(id=campaign_id, agent__owner=request.user)
    except Campaign.DoesNotExist:
        return Response({
            'error': 'Campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = CampaignSerializer(campaign)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = CampaignSerializer(campaign, data=request.data, partial=True)
        if serializer.is_valid():
            campaign = serializer.save()
            return Response(CampaignSerializer(campaign).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if campaign.status == 'active':
            return Response({
                'error': 'Cannot delete active campaign'
            }, status=status.HTTP_400_BAD_REQUEST)
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_campaign(request, campaign_id):
    """Start a campaign"""
    try:
        campaign = Campaign.objects.get(id=campaign_id, agent__owner=request.user)
    except Campaign.DoesNotExist:
        return Response({
            'error': 'Campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if campaign.status == 'active':
        return Response({
            'error': 'Campaign is already active'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    campaign.status = 'active'
    campaign.started_at = timezone.now()
    campaign.save()
    
    return Response(CampaignSerializer(campaign).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pause_campaign(request, campaign_id):
    """Pause a campaign"""
    try:
        campaign = Campaign.objects.get(id=campaign_id, agent__owner=request.user)
    except Campaign.DoesNotExist:
        return Response({
            'error': 'Campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    campaign.status = 'paused'
    campaign.save()
    
    return Response(CampaignSerializer(campaign).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def stop_campaign(request, campaign_id):
    """Stop a campaign"""
    try:
        campaign = Campaign.objects.get(id=campaign_id, agent__owner=request.user)
    except Campaign.DoesNotExist:
        return Response({
            'error': 'Campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    campaign.status = 'completed'
    campaign.completed_at = timezone.now()
    campaign.save()
    
    return Response(CampaignSerializer(campaign).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_contacts(request, agent_id):
    """List contacts for an agent"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    contacts = agent.contacts.all()
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        contacts = contacts.filter(call_status=status_filter)
    
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def contact_detail(request, contact_id):
    """Contact detail operations"""
    try:
        contact = Contact.objects.get(id=contact_id, agent__owner=request.user)
    except Contact.DoesNotExist:
        return Response({
            'error': 'Contact not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = ContactSerializer(contact)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            contact = serializer.save()
            return Response(ContactSerializer(contact).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def knowledge_detail(request, knowledge_id):
    """Business knowledge detail operations"""
    try:
        knowledge = BusinessKnowledge.objects.get(id=knowledge_id, agent__owner=request.user)
    except BusinessKnowledge.DoesNotExist:
        return Response({
            'error': 'Knowledge item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = BusinessKnowledgeSerializer(knowledge)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BusinessKnowledgeSerializer(knowledge, data=request.data, partial=True)
        if serializer.is_valid():
            knowledge = serializer.save()
            return Response(BusinessKnowledgeSerializer(knowledge).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        knowledge.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def agent_analytics(request, agent_id):
    """Get detailed analytics for an agent"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
    except Agent.DoesNotExist:
        return Response({
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Performance metrics
    metrics = AgentPerformanceMetrics.objects.filter(
        agent=agent,
        date__range=[start_date, end_date]
    ).order_by('-date')
    
    # Campaign statistics
    campaign_stats = {
        'total_campaigns': agent.campaigns.count(),
        'active_campaigns': agent.campaigns.filter(status='active').count(),
        'completed_campaigns': agent.campaigns.filter(status='completed').count(),
    }
    
    # Contact statistics (for outbound agents)
    contact_stats = {}
    if agent.agent_type == 'outbound':
        contact_stats = {
            'total_contacts': agent.contacts.count(),
            'pending_contacts': agent.contacts.filter(call_status='pending').count(),
            'completed_contacts': agent.contacts.filter(call_status='completed').count(),
        }
    
    return Response({
        'agent': AgentDetailSerializer(agent).data,
        'performance_metrics': AgentPerformanceSerializer(metrics, many=True).data,
        'campaign_statistics': campaign_stats,
        'contact_statistics': contact_stats,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    """Get dashboard summary for user's agents"""
    user = request.user
    
    # Agent statistics
    agents = Agent.objects.filter(owner=user)
    agent_stats = {
        'total_agents': agents.count(),
        'active_agents': agents.filter(status='active').count(),
        'paused_agents': agents.filter(status='paused').count(),
        'inbound_agents': agents.filter(agent_type='inbound').count(),
        'outbound_agents': agents.filter(agent_type='outbound').count(),
    }
    
    # Campaign statistics
    campaigns = Campaign.objects.filter(agent__owner=user)
    campaign_stats = {
        'total_campaigns': campaigns.count(),
        'active_campaigns': campaigns.filter(status='active').count(),
        'completed_campaigns': campaigns.filter(status='completed').count(),
    }
    
    # Today's performance
    today = timezone.now().date()
    today_metrics = AgentPerformanceMetrics.objects.filter(
        agent__owner=user,
        date=today
    ).aggregate(
        total_calls=Count('calls_made'),
        total_conversions=Count('conversions')
    )
    
    return Response({
        'agent_statistics': agent_stats,
        'campaign_statistics': campaign_stats,
        'today_performance': today_metrics,
    })