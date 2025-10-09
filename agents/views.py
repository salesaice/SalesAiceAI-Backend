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

from .models import (
    Agent, 
    BusinessKnowledge, 
    Contact, 
    ContactUpload, 
    Campaign, 
    CallQueue,
    AgentPerformanceMetrics
)
from .serializers import (
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

User = get_user_model()

# ====================================
# CORE AGENT ENDPOINTS ONLY (Minimal)
# ====================================

# 1. Agent List
@swagger_auto_schema(
    method='get',
    responses={200: AgentListSerializer(many=True)},
    operation_description="Get all agents configured by the subscriber",
    tags=['AI Agents']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def agent_list_page(request):
    """Agent List - See all agents with Name, Type, Status, Calls Handled"""
    try:
        agents = Agent.objects.filter(owner=request.user).order_by('-created_at')
        
        # Summary statistics
        summary = {
            'total_agents': agents.count(),
            'active_agents': agents.filter(status='active').count(),
            'paused_agents': agents.filter(status='paused').count(),
            'inbound_agents': agents.filter(agent_type='inbound').count(),
            'outbound_agents': agents.filter(agent_type='outbound').count(),
        }
        
        serializer = AgentListSerializer(agents, many=True)
        
        return Response({
            'success': True,
            'agents': serializer.data,
            'summary': summary
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 2. Agent Detail
@swagger_auto_schema(
    method='get',
    responses={200: AgentDetailSerializer},
    operation_description="Get agent details",
    tags=['AI Agents']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def agent_detail(request, agent_id):
    """Get detailed agent information"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        serializer = AgentDetailSerializer(agent)
        
        return Response({
            'success': True,
            'agent': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 3. Create Agent
@swagger_auto_schema(
    method='post',
    request_body=AgentCreateUpdateSerializer,
    responses={201: AgentDetailSerializer},
    operation_description="Create new agent - all data in request body",
    tags=['AI Agents']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_agent(request):
    """Create Agent with all data in request body following AgentCreatePayload structure"""
    try:
        serializer = AgentCreateUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            agent = serializer.save()
            response_serializer = AgentDetailSerializer(agent)
            
            return Response({
                'success': True,
                'message': f"{agent.get_agent_type_display()} agent '{agent.name}' created successfully",
                'agent': response_serializer.data
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


# 4. Update Agent
@swagger_auto_schema(
    method='put',
    request_body=AgentCreateUpdateSerializer,
    responses={200: AgentDetailSerializer},
    operation_description="Update agent - agent_id in URL, data in request body",
    tags=['AI Agents']
)
@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_agent(request, agent_id):
    """Update Agent - ID from URL, data from request body following AgentCreatePayload structure"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        serializer = AgentCreateUpdateSerializer(
            agent, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_agent = serializer.save()
            response_serializer = AgentDetailSerializer(updated_agent)
            
            return Response({
                'success': True,
                'message': f"{updated_agent.get_agent_type_display()} agent '{updated_agent.name}' updated successfully",
                'agent': response_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Agent not found',
            'errors': {'agent': ['Agent not found or access denied']}
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error updating agent: {str(e)}',
            'errors': {'general': [str(e)]}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 4. Delete Agent
@swagger_auto_schema(
    method='delete',
    responses={200: 'Agent deleted successfully'},
    operation_description="Delete agent",
    tags=['AI Agents']
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_agent(request, agent_id):
    """Delete agent"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        agent_name = agent.name
        agent.delete()
        
        return Response({
            'success': True,
            'message': f'Agent "{agent_name}" deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 5. Agent Analytics
@swagger_auto_schema(
    method='get',
    responses={200: AgentPerformanceSerializer},
    operation_description="Get agent analytics and performance metrics",
    tags=['AI Agents']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def agent_analytics(request, agent_id):
    """Agent analytics and performance data"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        
        # Get performance metrics
        performance_metrics = AgentPerformanceMetrics.objects.filter(agent=agent).first()
        
        analytics_data = {
            'agent_id': str(agent.id),
            'agent_name': agent.name,
            'agent_type': agent.agent_type,
            'status': agent.status,
            'total_calls': performance_metrics.total_calls if performance_metrics else 0,
            'successful_calls': performance_metrics.successful_calls if performance_metrics else 0,
            'failed_calls': performance_metrics.failed_calls if performance_metrics else 0,
            'average_call_duration': performance_metrics.average_call_duration if performance_metrics else 0,
            'conversion_rate': performance_metrics.conversion_rate if performance_metrics else 0,
            'customer_satisfaction': performance_metrics.customer_satisfaction_score if performance_metrics else 0,
            'created_at': agent.created_at,
            'last_active': agent.last_active
        }
        
        return Response({
            'success': True,
            'analytics': analytics_data
        }, status=status.HTTP_200_OK)
        
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 6. Agent Contacts
@swagger_auto_schema(
    method='get',
    responses={200: ContactSerializer(many=True)},
    operation_description="Get agent contacts list",
    tags=['AI Agents']
)
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def agent_contacts(request, agent_id):
    """Agent contacts management"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        
        if request.method == 'GET':
            contacts = Contact.objects.filter(agent=agent).order_by('-created_at')
            serializer = ContactSerializer(contacts, many=True)
            
            return Response({
                'success': True,
                'contacts': serializer.data,
                'total': contacts.count()
            }, status=status.HTTP_200_OK)
            
        elif request.method == 'POST':
            # Handle CSV upload or individual contact creation
            if 'csv_file' in request.FILES:
                csv_file = request.FILES['csv_file']
                
                # Process CSV upload
                try:
                    decoded_file = csv_file.read().decode('utf-8')
                    io_string = io.StringIO(decoded_file)
                    reader = csv.DictReader(io_string)
                    
                    contacts_created = 0
                    for row in reader:
                        Contact.objects.create(
                            agent=agent,
                            name=row.get('name', ''),
                            phone=row.get('phone', row.get('phone_number', '')),
                            email=row.get('email', ''),
                            notes=row.get('notes', ''),
                            preferred_call_time=row.get('preferred_time', row.get('preferred_call_time', ''))
                        )
                        contacts_created += 1
                    
                    return Response({
                        'success': True,
                        'message': f'{contacts_created} contacts uploaded successfully',
                        'contacts_created': contacts_created
                    }, status=status.HTTP_201_CREATED)
                    
                except Exception as e:
                    return Response({
                        'success': False,
                        'error': f'CSV processing error: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Create individual contact
                serializer = ContactSerializer(data=request.data)
                if serializer.is_valid():
                    contact = serializer.save(agent=agent)
                    return Response({
                        'success': True,
                        'message': 'Contact created successfully',
                        'contact': ContactSerializer(contact).data
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        'success': False,
                        'errors': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
        
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 7. Agent Knowledge
@swagger_auto_schema(
    method='get',
    responses={200: BusinessKnowledgeSerializer(many=True)},
    operation_description="Get agent knowledge base",
    tags=['AI Agents']
)
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def agent_knowledge(request, agent_id):
    """Agent business knowledge management"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        
        if request.method == 'GET':
            knowledge_items = BusinessKnowledge.objects.filter(agent=agent).order_by('-created_at')
            serializer = BusinessKnowledgeSerializer(knowledge_items, many=True)
            
            return Response({
                'success': True,
                'knowledge_items': serializer.data,
                'total': knowledge_items.count()
            }, status=status.HTTP_200_OK)
            
        elif request.method == 'POST':
            serializer = BusinessKnowledgeSerializer(data=request.data)
            if serializer.is_valid():
                knowledge_item = serializer.save(agent=agent)
                return Response({
                    'success': True,
                    'message': 'Knowledge item added successfully',
                    'knowledge_item': BusinessKnowledgeSerializer(knowledge_item).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 8. Campaigns List
@swagger_auto_schema(
    method='get',
    responses={200: CampaignSerializer(many=True)},
    operation_description="List all campaigns",
    tags=['AI Agents']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def campaigns_list(request):
    """List all campaigns for user"""
    try:
        campaigns = Campaign.objects.filter(agent__owner=request.user).order_by('-created_at')
        serializer = CampaignSerializer(campaigns, many=True)
        
        return Response({
            'success': True,
            'campaigns': serializer.data,
            'total': campaigns.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 9. Campaign Detail
@swagger_auto_schema(
    method='get',
    responses={200: CampaignSerializer},
    operation_description="Get campaign details",
    tags=['AI Agents']
)
@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def campaign_detail(request, campaign_id):
    """Campaign details and update"""
    try:
        campaign = Campaign.objects.get(id=campaign_id, agent__owner=request.user)
        
        if request.method == 'GET':
            serializer = CampaignSerializer(campaign)
            return Response({
                'success': True,
                'campaign': serializer.data
            }, status=status.HTTP_200_OK)
            
        elif request.method == 'PUT':
            serializer = CampaignSerializer(campaign, data=request.data, partial=True)
            if serializer.is_valid():
                updated_campaign = serializer.save()
                return Response({
                    'success': True,
                    'message': 'Campaign updated successfully',
                    'campaign': CampaignSerializer(updated_campaign).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
    except Campaign.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 10. Bulk Delete Agents
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'agent_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
        }
    ),
    responses={200: 'Agents deleted successfully'},
    operation_description="Bulk delete agents",
    tags=['AI Agents']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_delete_agents(request):
    """Bulk delete agents"""
    try:
        agent_ids = request.data.get('agent_ids', [])
        if not agent_ids:
            return Response({
                'success': False,
                'error': 'No agent IDs provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        agents = Agent.objects.filter(id__in=agent_ids, owner=request.user)
        deleted_count = agents.count()
        agents.delete()
        
        return Response({
            'success': True,
            'message': f'{deleted_count} agents deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 11. Bulk Status Update
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'agent_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
            'status': openapi.Schema(type=openapi.TYPE_STRING, enum=['active', 'paused'])
        }
    ),
    responses={200: 'Agent status updated successfully'},
    operation_description="Bulk update agent status",
    tags=['AI Agents']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_status_update(request):
    """Bulk update agent status"""
    try:
        agent_ids = request.data.get('agent_ids', [])
        new_status = request.data.get('status')
        
        if not agent_ids or not new_status:
            return Response({
                'success': False,
                'error': 'Agent IDs and status are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in ['active', 'paused']:
            return Response({
                'success': False,
                'error': 'Status must be either "active" or "paused"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        agents = Agent.objects.filter(id__in=agent_ids, owner=request.user)
        updated_count = agents.update(status=new_status)
        
        return Response({
            'success': True,
            'message': f'{updated_count} agents status updated to {new_status}'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 12. Knowledge Detail
@swagger_auto_schema(
    method='get',
    responses={200: BusinessKnowledgeSerializer},
    operation_description="Get knowledge item details",
    tags=['AI Agents']
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def knowledge_detail(request, knowledge_id):
    """Knowledge item details, update, delete"""
    try:
        knowledge_item = BusinessKnowledge.objects.get(id=knowledge_id, agent__owner=request.user)
        
        if request.method == 'GET':
            serializer = BusinessKnowledgeSerializer(knowledge_item)
            return Response({
                'success': True,
                'knowledge_item': serializer.data
            }, status=status.HTTP_200_OK)
            
        elif request.method == 'PUT':
            serializer = BusinessKnowledgeSerializer(knowledge_item, data=request.data, partial=True)
            if serializer.is_valid():
                updated_item = serializer.save()
                return Response({
                    'success': True,
                    'message': 'Knowledge item updated successfully',
                    'knowledge_item': BusinessKnowledgeSerializer(updated_item).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        elif request.method == 'DELETE':
            item_title = knowledge_item.title
            knowledge_item.delete()
            return Response({
                'success': True,
                'message': f'Knowledge item "{item_title}" deleted successfully'
            }, status=status.HTTP_200_OK)
        
    except BusinessKnowledge.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Knowledge item not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 13. Dashboard Summary
@swagger_auto_schema(
    method='get',
    responses={200: AgentSummarySerializer},
    operation_description="Get agents dashboard summary",
    tags=['AI Agents']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    """Dashboard summary for all agents"""
    try:
        user_agents = Agent.objects.filter(owner=request.user)
        
        summary = {
            'total_agents': user_agents.count(),
            'active_agents': user_agents.filter(status='active').count(),
            'paused_agents': user_agents.filter(status='paused').count(),
            'inbound_agents': user_agents.filter(agent_type='inbound').count(),
            'outbound_agents': user_agents.filter(agent_type='outbound').count(),
            
            # Campaign statistics
            'total_campaigns': Campaign.objects.filter(agent__owner=request.user).count(),
            'active_campaigns': Campaign.objects.filter(agent__owner=request.user, status='active').count(),
            
            # Contact statistics  
            'total_contacts': Contact.objects.filter(agent__owner=request.user).count(),
            
            # Knowledge base statistics
            'total_knowledge_items': BusinessKnowledge.objects.filter(agent__owner=request.user).count(),
        }
        
        return Response({
            'success': True,
            'summary': summary
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ====================================
# OUTBOUND AGENT SPECIFIC FEATURES
# ====================================

# 14. Create Campaign (Outbound Agents)
@swagger_auto_schema(
    method='post',
    request_body=CampaignSerializer,
    responses={201: CampaignSerializer},
    operation_description="Create campaign for outbound agent - schedule start date/time or start immediately",
    tags=['AI Agents']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_campaign(request, agent_id):
    """Create campaign for outbound agent with scheduling"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        
        # Verify this is an outbound agent
        if agent.agent_type != 'outbound':
            return Response({
                'success': False,
                'error': 'Campaigns can only be created for outbound agents'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CampaignSerializer(data=request.data)
        if serializer.is_valid():
            campaign = serializer.save(agent=agent)
            
            # Handle immediate start vs scheduled start
            if campaign.schedule_type == 'immediate':
                campaign.status = 'active'
                campaign.started_at = timezone.now()
                campaign.save()
            elif campaign.schedule_type == 'scheduled' and campaign.scheduled_start:
                campaign.status = 'scheduled'
                campaign.save()
            
            return Response({
                'success': True,
                'message': 'Campaign created successfully',
                'campaign': CampaignSerializer(campaign).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 15. Call Queue Management
@swagger_auto_schema(
    method='get',
    responses={200: CallQueueSerializer(many=True)},
    operation_description="View call queue - pending/completed calls with status",
    tags=['AI Agents']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def call_queue(request, agent_id):
    """View call queue for outbound agent - pending/completed calls"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        
        # Get active campaigns for this agent
        campaigns = Campaign.objects.filter(agent=agent)
        
        # Get call queue entries for all campaigns
        queue_entries = CallQueue.objects.filter(
            campaign__in=campaigns
        ).select_related('campaign', 'contact').order_by('queue_position', 'created_at')
        
        # Filter by status if requested
        status_filter = request.GET.get('status')
        if status_filter:
            queue_entries = queue_entries.filter(status=status_filter)
        
        serializer = CallQueueSerializer(queue_entries, many=True)
        
        # Summary statistics
        queue_summary = {
            'total_calls': queue_entries.count(),
            'pending_calls': queue_entries.filter(status='pending').count(),
            'in_progress_calls': queue_entries.filter(status='in_progress').count(),
            'completed_calls': queue_entries.filter(status='completed').count(),
            'failed_calls': queue_entries.filter(status='failed').count(),
        }
        
        return Response({
            'success': True,
            'call_queue': serializer.data,
            'summary': queue_summary
        }, status=status.HTTP_200_OK)
        
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)


# 16. Enhanced Delete Agent (with active call/campaign check)
@swagger_auto_schema(
    method='delete',
    responses={200: 'Agent deleted successfully'},
    operation_description="Delete agent - only if not in active call/campaign",
    tags=['AI Agents']
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_agent_enhanced(request, agent_id):
    """Delete agent with active call/campaign validation"""
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        
        # Check for active campaigns
        active_campaigns = Campaign.objects.filter(
            agent=agent, 
            status__in=['active', 'in_progress']
        ).count()
        
        if active_campaigns > 0:
            return Response({
                'success': False,
                'error': f'Cannot delete agent. Agent has {active_campaigns} active campaign(s). Please pause or complete campaigns first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check for active calls
        active_calls = CallQueue.objects.filter(
            campaign__agent=agent,
            status='in_progress'
        ).count()
        
        if active_calls > 0:
            return Response({
                'success': False,
                'error': f'Cannot delete agent. Agent has {active_calls} active call(s). Please wait for calls to complete.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        agent_name = agent.name
        agent.delete()
        
        return Response({
            'success': True,
            'message': f'Agent "{agent_name}" deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Agent.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
