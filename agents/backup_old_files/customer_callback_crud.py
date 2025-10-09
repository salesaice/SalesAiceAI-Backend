from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta

from .ai_agent_models import (
    AIAgent, CustomerProfile, CallSession, ScheduledCallback
)

User = get_user_model()


class CustomerProfileCRUDAPIView(generics.ListCreateAPIView):
    """
    Complete CRUD for Customer Profiles
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            agent = user.ai_agent
            return CustomerProfile.objects.filter(ai_agent=agent).order_by('-last_interaction', '-created_at')
        except AIAgent.DoesNotExist:
            return CustomerProfile.objects.none()
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('interest_level', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('converted', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Search by name or phone'),
        ],
        responses={200: "List of customer profiles"},
        tags=['AI Agents']
    )
    def get(self, request, *args, **kwargs):
        customers = self.get_queryset()
        
        # Apply filters
        interest_level = request.query_params.get('interest_level')
        converted = request.query_params.get('converted')
        search = request.query_params.get('search')
        
        if interest_level:
            customers = customers.filter(interest_level=interest_level)
        if converted is not None:
            customers = customers.filter(is_converted=converted.lower() == 'true')
        if search:
            customers = customers.filter(
                models.Q(name__icontains=search) | 
                models.Q(phone_number__icontains=search) |
                models.Q(email__icontains=search)
            )
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': str(customer.id),
                'phone_number': customer.phone_number,
                'name': customer.name or 'Unknown',
                'email': customer.email,
                'interest_level': customer.interest_level,
                'communication_style': customer.communication_style,
                'call_preference_time': customer.call_preference_time,
                'total_calls': customer.total_calls,
                'successful_calls': customer.successful_calls,
                'last_interaction': customer.last_interaction.isoformat() if customer.last_interaction else None,
                'next_followup': customer.next_followup.isoformat() if customer.next_followup else None,
                'is_converted': customer.is_converted,
                'conversion_date': customer.conversion_date.isoformat() if customer.conversion_date else None,
                'is_do_not_call': customer.is_do_not_call,
                'created_at': customer.created_at.isoformat(),
                'conversation_notes': customer.conversation_notes,
                'preferences': customer.preferences
            })
        
        return Response({
            'customers': customers_data,
            'total_count': len(customers_data),
            'summary': {
                'total': customers.count(),
                'hot_leads': customers.filter(interest_level='hot').count(),
                'warm_leads': customers.filter(interest_level='warm').count(),
                'cold_leads': customers.filter(interest_level='cold').count(),
                'converted': customers.filter(is_converted=True).count(),
                'do_not_call': customers.filter(is_do_not_call=True).count()
            }
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Customer phone number'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Customer name'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Customer email'),
                'interest_level': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['cold', 'warm', 'hot', 'converted'],
                    description='Customer interest level'
                ),
                'call_preference_time': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['morning', 'afternoon', 'evening', 'anytime']
                ),
                'communication_style': openapi.Schema(type=openapi.TYPE_STRING),
                'preferences': openapi.Schema(type=openapi.TYPE_OBJECT),
                'notes': openapi.Schema(type=openapi.TYPE_STRING)
            },
            required=['phone_number']
        ),
        responses={201: "Customer profile created"},
        tags=['AI Agents']
    )
    def post(self, request, *args, **kwargs):
        try:
            agent = request.user.ai_agent
        except AIAgent.DoesNotExist:
            return Response({
                'error': 'No AI Agent found. Please create an AI Agent first.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        phone_number = data.get('phone_number')
        
        # Check if customer already exists
        if CustomerProfile.objects.filter(ai_agent=agent, phone_number=phone_number).exists():
            return Response({
                'error': 'Customer with this phone number already exists',
                'phone_number': phone_number
            }, status=status.HTTP_409_CONFLICT)
        
        try:
            customer = CustomerProfile.objects.create(
                ai_agent=agent,
                phone_number=phone_number,
                name=data.get('name', ''),
                email=data.get('email', ''),
                interest_level=data.get('interest_level', 'warm'),
                call_preference_time=data.get('call_preference_time', 'anytime'),
                communication_style=data.get('communication_style', ''),
                preferences=data.get('preferences', {}),
                conversation_notes={
                    'initial_notes': data.get('notes', ''),
                    'created_at': datetime.now().isoformat(),
                    'created_by': 'manual_entry'
                }
            )
            
            return Response({
                'message': 'Customer profile created successfully',
                'customer': {
                    'id': str(customer.id),
                    'phone_number': customer.phone_number,
                    'name': customer.name,
                    'email': customer.email,
                    'interest_level': customer.interest_level,
                    'created_at': customer.created_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Failed to create customer profile: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class CustomerProfileDetailAPIView(APIView):
    """
    Detailed CRUD operations for specific customer profile
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        customer_id = self.kwargs.get('id')
        user = self.request.user
        
        try:
            agent = user.ai_agent
            return get_object_or_404(CustomerProfile, id=customer_id, ai_agent=agent)
        except AIAgent.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        responses={200: "Customer profile details"},
        tags=['AI Agents']
    )
    def get(self, request, *args, **kwargs):
        customer = self.get_object()
        if not customer:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get call history for this customer
        call_history = CallSession.objects.filter(
            customer_profile=customer
        ).order_by('-initiated_at')[:10]
        
        calls_data = []
        for call in call_history:
            calls_data.append({
                'id': str(call.id),
                'call_type': call.call_type,
                'outcome': call.outcome,
                'duration': call.duration_formatted,
                'initiated_at': call.initiated_at.isoformat(),
                'customer_response': call.customer_response,
                'agent_notes': call.agent_notes
            })
        
        # Get scheduled callbacks
        callbacks = ScheduledCallback.objects.filter(
            customer_profile=customer,
            status__in=['scheduled', 'in_progress']
        ).order_by('scheduled_datetime')
        
        callbacks_data = []
        for callback in callbacks:
            callbacks_data.append({
                'id': str(callback.id),
                'scheduled_datetime': callback.scheduled_datetime.isoformat(),
                'reason': callback.reason,
                'status': callback.status,
                'priority_level': callback.priority_level
            })
        
        customer_data = {
            'id': str(customer.id),
            'phone_number': customer.phone_number,
            'name': customer.name,
            'email': customer.email,
            'interest_level': customer.interest_level,
            'communication_style': customer.communication_style,
            'call_preference_time': customer.call_preference_time,
            'total_calls': customer.total_calls,
            'successful_calls': customer.successful_calls,
            'last_interaction': customer.last_interaction.isoformat() if customer.last_interaction else None,
            'next_followup': customer.next_followup.isoformat() if customer.next_followup else None,
            'is_converted': customer.is_converted,
            'conversion_date': customer.conversion_date.isoformat() if customer.conversion_date else None,
            'is_do_not_call': customer.is_do_not_call,
            'conversation_notes': customer.conversation_notes,
            'preferences': customer.preferences,
            'objections': customer.objections,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat(),
            'call_history': calls_data,
            'scheduled_callbacks': callbacks_data,
            'statistics': {
                'success_rate': (customer.successful_calls / customer.total_calls * 100) if customer.total_calls > 0 else 0,
                'avg_calls_per_month': customer.total_calls // max(1, (timezone.now().date() - customer.created_at.date()).days // 30),
                'days_since_last_contact': (timezone.now().date() - customer.last_interaction.date()).days if customer.last_interaction else None
            }
        }
        
        return Response(customer_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'interest_level': openapi.Schema(type=openapi.TYPE_STRING),
                'communication_style': openapi.Schema(type=openapi.TYPE_STRING),
                'call_preference_time': openapi.Schema(type=openapi.TYPE_STRING),
                'is_do_not_call': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'preferences': openapi.Schema(type=openapi.TYPE_OBJECT),
                'notes': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={200: "Customer profile updated"},
        tags=['AI Agents']
    )
    def put(self, request, *args, **kwargs):
        customer = self.get_object()
        if not customer:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        
        # Update fields
        if 'name' in data:
            customer.name = data['name']
        if 'email' in data:
            customer.email = data['email']
        if 'interest_level' in data:
            customer.interest_level = data['interest_level']
        if 'communication_style' in data:
            customer.communication_style = data['communication_style']
        if 'call_preference_time' in data:
            customer.call_preference_time = data['call_preference_time']
        if 'is_do_not_call' in data:
            customer.is_do_not_call = data['is_do_not_call']
        if 'preferences' in data:
            customer.preferences.update(data['preferences'])
        
        # Add notes to conversation history
        if 'notes' in data:
            if 'manual_updates' not in customer.conversation_notes:
                customer.conversation_notes['manual_updates'] = []
            customer.conversation_notes['manual_updates'].append({
                'timestamp': datetime.now().isoformat(),
                'notes': data['notes'],
                'updated_by': request.user.email
            })
        
        customer.save()
        
        return Response({
            'message': 'Customer profile updated successfully',
            'customer': {
                'id': str(customer.id),
                'name': customer.name,
                'interest_level': customer.interest_level,
                'updated_at': customer.updated_at.isoformat()
            }
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        responses={204: "Customer profile deleted"},
        tags=['AI Agents']
    )
    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        if not customer:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            customer_phone = customer.phone_number
            customer_name = customer.name
            
            # Delete related data
            with transaction.atomic():
                ScheduledCallback.objects.filter(customer_profile=customer).delete()
                CallSession.objects.filter(customer_profile=customer).delete()
                customer.delete()
            
            return Response({
                'message': f'Customer profile deleted successfully',
                'deleted_customer': {
                    'phone_number': customer_phone,
                    'name': customer_name,
                    'deleted_at': datetime.now().isoformat()
                }
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response({
                'error': f'Failed to delete customer: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class ScheduledCallbackCRUDAPIView(generics.ListCreateAPIView):
    """
    Complete CRUD for Scheduled Callbacks
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            agent = user.ai_agent
            return ScheduledCallback.objects.filter(ai_agent=agent).order_by('scheduled_datetime')
        except AIAgent.DoesNotExist:
            return ScheduledCallback.objects.none()
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('overdue', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('today', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: "List of scheduled callbacks"},
        tags=['AI Agents']
    )
    def get(self, request, *args, **kwargs):
        callbacks = self.get_queryset()
        
        # Apply filters
        status_filter = request.query_params.get('status')
        overdue = request.query_params.get('overdue')
        today = request.query_params.get('today')
        
        if status_filter:
            callbacks = callbacks.filter(status=status_filter)
        if overdue and overdue.lower() == 'true':
            callbacks = callbacks.filter(
                status='scheduled',
                scheduled_datetime__lt=timezone.now()
            )
        if today and today.lower() == 'true':
            callbacks = callbacks.filter(
                scheduled_datetime__date=timezone.now().date()
            )
        
        callbacks_data = []
        for callback in callbacks:
            callbacks_data.append({
                'id': str(callback.id),
                'customer': {
                    'id': str(callback.customer_profile.id),
                    'phone_number': callback.customer_profile.phone_number,
                    'name': callback.customer_profile.name,
                    'interest_level': callback.customer_profile.interest_level
                },
                'scheduled_datetime': callback.scheduled_datetime.isoformat(),
                'reason': callback.reason,
                'notes': callback.notes,
                'status': callback.status,
                'priority_level': callback.priority_level,
                'expected_outcome': callback.expected_outcome,
                'is_overdue': callback.scheduled_datetime < timezone.now() and callback.status == 'scheduled',
                'time_until_call': str(callback.scheduled_datetime - timezone.now()) if callback.scheduled_datetime > timezone.now() else 'Overdue',
                'created_at': callback.created_at.isoformat()
            })
        
        return Response({
            'callbacks': callbacks_data,
            'total_count': len(callbacks_data),
            'summary': {
                'scheduled': callbacks.filter(status='scheduled').count(),
                'in_progress': callbacks.filter(status='in_progress').count(),
                'completed': callbacks.filter(status='completed').count(),
                'overdue': callbacks.filter(
                    status='scheduled',
                    scheduled_datetime__lt=timezone.now()
                ).count(),
                'today': callbacks.filter(
                    scheduled_datetime__date=timezone.now().date()
                ).count()
            }
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'customer_phone': openapi.Schema(type=openapi.TYPE_STRING, description='Customer phone number'),
                'scheduled_datetime': openapi.Schema(type=openapi.TYPE_STRING, description='ISO datetime'),
                'reason': openapi.Schema(type=openapi.TYPE_STRING),
                'notes': openapi.Schema(type=openapi.TYPE_STRING),
                'priority_level': openapi.Schema(type=openapi.TYPE_INTEGER, description='1-5 priority'),
                'expected_outcome': openapi.Schema(type=openapi.TYPE_STRING)
            },
            required=['customer_phone', 'scheduled_datetime', 'reason']
        ),
        responses={201: "Callback scheduled successfully"},
        tags=['AI Agents']
    )
    def post(self, request, *args, **kwargs):
        try:
            agent = request.user.ai_agent
        except AIAgent.DoesNotExist:
            return Response({
                'error': 'No AI Agent found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        customer_phone = data.get('customer_phone')
        
        # Get or create customer profile
        customer_profile, created = CustomerProfile.objects.get_or_create(
            ai_agent=agent,
            phone_number=customer_phone,
            defaults={'interest_level': 'warm'}
        )
        
        try:
            callback = ScheduledCallback.objects.create(
                ai_agent=agent,
                customer_profile=customer_profile,
                scheduled_datetime=datetime.fromisoformat(data.get('scheduled_datetime').replace('Z', '+00:00')),
                reason=data.get('reason'),
                notes=data.get('notes', ''),
                priority_level=data.get('priority_level', 2),
                expected_outcome=data.get('expected_outcome', ''),
                status='scheduled'
            )
            
            # Update customer's next followup
            customer_profile.next_followup = callback.scheduled_datetime
            customer_profile.save()
            
            return Response({
                'message': 'Callback scheduled successfully',
                'callback': {
                    'id': str(callback.id),
                    'customer_phone': customer_profile.phone_number,
                    'customer_name': customer_profile.name,
                    'scheduled_datetime': callback.scheduled_datetime.isoformat(),
                    'reason': callback.reason,
                    'priority_level': callback.priority_level,
                    'created_at': callback.created_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Failed to schedule callback: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class ScheduledCallbackDetailAPIView(APIView):
    """
    Detailed CRUD operations for specific scheduled callback
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        callback_id = self.kwargs.get('id')
        user = self.request.user
        
        try:
            agent = user.ai_agent
            return get_object_or_404(ScheduledCallback, id=callback_id, ai_agent=agent)
        except AIAgent.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        responses={200: "Callback details"},
        tags=['AI Agents']
    )
    def get(self, request, *args, **kwargs):
        callback = self.get_object()
        if not callback:
            return Response({'error': 'Callback not found'}, status=status.HTTP_404_NOT_FOUND)
        
        callback_data = {
            'id': str(callback.id),
            'customer': {
                'id': str(callback.customer_profile.id),
                'phone_number': callback.customer_profile.phone_number,
                'name': callback.customer_profile.name,
                'email': callback.customer_profile.email,
                'interest_level': callback.customer_profile.interest_level,
                'total_calls': callback.customer_profile.total_calls,
                'last_interaction': callback.customer_profile.last_interaction.isoformat() if callback.customer_profile.last_interaction else None
            },
            'scheduled_datetime': callback.scheduled_datetime.isoformat(),
            'reason': callback.reason,
            'notes': callback.notes,
            'status': callback.status,
            'priority_level': callback.priority_level,
            'expected_outcome': callback.expected_outcome,
            'completed_at': callback.completed_at.isoformat() if callback.completed_at else None,
            'rescheduled_from': callback.rescheduled_from.isoformat() if callback.rescheduled_from else None,
            'is_overdue': callback.scheduled_datetime < timezone.now() and callback.status == 'scheduled',
            'time_until_call': str(callback.scheduled_datetime - timezone.now()) if callback.scheduled_datetime > timezone.now() else 'Overdue',
            'created_at': callback.created_at.isoformat(),
            'updated_at': callback.updated_at.isoformat()
        }
        
        return Response(callback_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'scheduled_datetime': openapi.Schema(type=openapi.TYPE_STRING),
                'reason': openapi.Schema(type=openapi.TYPE_STRING),
                'notes': openapi.Schema(type=openapi.TYPE_STRING),
                'priority_level': openapi.Schema(type=openapi.TYPE_INTEGER),
                'expected_outcome': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['scheduled', 'in_progress', 'completed', 'rescheduled', 'cancelled']
                )
            }
        ),
        responses={200: "Callback updated successfully"},
        tags=['AI Agents']
    )
    def put(self, request, *args, **kwargs):
        callback = self.get_object()
        if not callback:
            return Response({'error': 'Callback not found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        old_datetime = callback.scheduled_datetime
        
        # Update fields
        if 'scheduled_datetime' in data:
            new_datetime = datetime.fromisoformat(data['scheduled_datetime'].replace('Z', '+00:00'))
            if new_datetime != old_datetime:
                callback.rescheduled_from = old_datetime
            callback.scheduled_datetime = new_datetime
            
            # Update customer's next followup
            callback.customer_profile.next_followup = new_datetime
            callback.customer_profile.save()
        
        if 'reason' in data:
            callback.reason = data['reason']
        if 'notes' in data:
            callback.notes = data['notes']
        if 'priority_level' in data:
            callback.priority_level = data['priority_level']
        if 'expected_outcome' in data:
            callback.expected_outcome = data['expected_outcome']
        if 'status' in data:
            callback.status = data['status']
            if data['status'] == 'completed':
                callback.completed_at = timezone.now()
        
        callback.save()
        
        return Response({
            'message': 'Callback updated successfully',
            'callback': {
                'id': str(callback.id),
                'scheduled_datetime': callback.scheduled_datetime.isoformat(),
                'status': callback.status,
                'updated_at': callback.updated_at.isoformat()
            }
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        responses={204: "Callback deleted successfully"},
        tags=['AI Agents']
    )
    def delete(self, request, *args, **kwargs):
        callback = self.get_object()
        if not callback:
            return Response({'error': 'Callback not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            callback_info = {
                'customer_phone': callback.customer_profile.phone_number,
                'scheduled_datetime': callback.scheduled_datetime.isoformat(),
                'reason': callback.reason
            }
            
            # Clear customer's next followup if this was the next callback
            if callback.customer_profile.next_followup == callback.scheduled_datetime:
                # Find next callback for this customer
                next_callback = ScheduledCallback.objects.filter(
                    customer_profile=callback.customer_profile,
                    status='scheduled',
                    scheduled_datetime__gt=timezone.now()
                ).exclude(id=callback.id).order_by('scheduled_datetime').first()
                
                callback.customer_profile.next_followup = next_callback.scheduled_datetime if next_callback else None
                callback.customer_profile.save()
            
            callback.delete()
            
            return Response({
                'message': 'Callback deleted successfully',
                'deleted_callback': callback_info
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response({
                'error': f'Failed to delete callback: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class CallbackBulkActionsAPIView(APIView):
    """Bulk operations on scheduled callbacks"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'action': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['complete', 'reschedule', 'cancel', 'delete_completed'],
                    description='Bulk action to perform'
                ),
                'callback_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description='List of callback IDs'
                ),
                'new_datetime': openapi.Schema(type=openapi.TYPE_STRING, description='For reschedule action'),
                'filters': openapi.Schema(type=openapi.TYPE_OBJECT, description='Filters for bulk action')
            },
            required=['action']
        ),
        responses={200: "Bulk action completed"},
        tags=['AI Agents']
    )
    def post(self, request):
        try:
            agent = request.user.ai_agent
        except AIAgent.DoesNotExist:
            return Response({'error': 'No AI Agent found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        action = data.get('action')
        callback_ids = data.get('callback_ids', [])
        filters = data.get('filters', {})
        
        # Get callbacks based on IDs or filters
        if callback_ids:
            callbacks = ScheduledCallback.objects.filter(id__in=callback_ids, ai_agent=agent)
        else:
            callbacks = ScheduledCallback.objects.filter(ai_agent=agent)
            if filters.get('status'):
                callbacks = callbacks.filter(status=filters['status'])
            if filters.get('overdue'):
                callbacks = callbacks.filter(
                    status='scheduled',
                    scheduled_datetime__lt=timezone.now()
                )
        
        results = []
        
        try:
            with transaction.atomic():
                if action == 'complete':
                    updated = callbacks.update(
                        status='completed',
                        completed_at=timezone.now()
                    )
                    results.append(f'{updated} callbacks marked as completed')
                
                elif action == 'reschedule':
                    new_datetime = data.get('new_datetime')
                    if not new_datetime:
                        return Response({'error': 'new_datetime required for reschedule'}, status=status.HTTP_400_BAD_REQUEST)
                    
                    new_dt = datetime.fromisoformat(new_datetime.replace('Z', '+00:00'))
                    for callback in callbacks:
                        callback.rescheduled_from = callback.scheduled_datetime
                        callback.scheduled_datetime = new_dt
                        callback.save()
                    results.append(f'{callbacks.count()} callbacks rescheduled')
                
                elif action == 'cancel':
                    updated = callbacks.update(status='cancelled')
                    results.append(f'{updated} callbacks cancelled')
                
                elif action == 'delete_completed':
                    completed_callbacks = callbacks.filter(status='completed')
                    count = completed_callbacks.count()
                    completed_callbacks.delete()
                    results.append(f'{count} completed callbacks deleted')
        
            return Response({
                'message': 'Bulk action completed successfully',
                'action': action,
                'results': results,
                'processed_count': callbacks.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Bulk action failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
