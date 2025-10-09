from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta, datetime, timezone as dt_timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import stripe
# Generic exception handling for all Stripe versions
StripeError = Exception

from accounts.permissions import IsAdmin
from .models import SubscriptionPlan, Subscription, BillingHistory

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class UserPackageSelectionAPIView(APIView):
    """
    User Package Selection - Get available packages for users to choose from (Public Access)
    POST requires authentication for subscription creation
    """
    
    def get_permissions(self):
        """
        Allow anyone to view packages (GET), but require authentication for subscription (POST)
        """
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    @swagger_auto_schema(
        tags=['User - Package Selection'],
        operation_summary="Get Available Packages",
        operation_description="Get all active subscription packages available for selection",
        responses={
            200: openapi.Response(
                description="Available packages",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'packages': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'price_monthly': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'minutes_total_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'agents_allowed': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'analytics_access': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'features': openapi.Schema(type=openapi.TYPE_OBJECT),
                                    'is_popular': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        )
                    }
                )
            ),
            401: "Authentication required"
        }
    )
    def get(self, request):
        """Get all available packages for user selection - Same format as admin API"""
        packages = SubscriptionPlan.objects.annotate(
            subscriber_count=Count('subscription')
        ).order_by('-created_at')
        
        package_data = []
        for package in packages:
            # Prepare features object - Same structure as admin API
            features = {
                'campaigns': package.concurrent_calls if package.auto_campaigns else 0,  # number - campaign capacity
                'api_access': package.api_access,  # boolean
                'advanced_analytics': package.advanced_analytics if package.analytics_access else False,  # boolean
            }
            
            # Extended features for comprehensive details - Same as admin API
            extended_features = {
                'ai_agents_allowed': package.ai_agents_allowed,
                'concurrent_calls': package.concurrent_calls,
                'advanced_analytics': package.advanced_analytics,
                'api_access': package.api_access,
                'webhook_access': package.webhook_access,
                'call_recording': package.call_recording,
                'call_transcription': package.call_transcription,
                'sentiment_analysis': package.sentiment_analysis,
                'auto_campaigns': package.auto_campaigns,
                'crm_integration': package.crm_integration,
                'storage_gb': package.storage_gb,
                'backup_retention_days': package.backup_retention_days,
                'priority_support': package.priority_support,
            }
            
            package_data.append({
                'id': str(package.id),  # TypeScript expects string | number
                'name': package.name,
                'price_monthly': float(package.price),  # TypeScript expects number | string
                'minutes_inbound_limit': package.minutes_inbound_limit,
                'minutes_outbound_limit': package.minutes_outbound_limit,
                'minutes_total_limit': package.call_minutes_limit,
                'agents_allowed': package.agents_allowed,
                'analytics_access': package.analytics_access,
                'features': features,  # Main features structure
                'extended_features': extended_features,  # Comprehensive features
                'is_active': package.is_active,
                'created_at': package.created_at.isoformat(),  # ISO string format
                'subscribers': package.subscriber_count,  # Subscriber count
            })
        
        return Response({
            'success': True,
            'message': f'Found {len(package_data)} packages',
            'packages': package_data
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['User - Package Selection'],
        operation_summary="Subscribe to Package",
        operation_description="Subscribe user to selected package using Stripe",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['package_id'],
            properties={
                'package_id': openapi.Schema(type=openapi.TYPE_STRING, description="Selected package ID"),
                'payment_method_id': openapi.Schema(type=openapi.TYPE_STRING, description="Stripe payment method ID"),
            }
        ),
        responses={
            201: "Subscription created successfully",
            400: "Bad request - validation error",
            401: "Authentication required"
        }
    )
    def post(self, request):
        """Subscribe user to selected package"""
        # Check authentication
        if not request.user or request.user.is_anonymous:
            return Response({
                'success': False,
                'error': 'Authentication required. Please provide a valid JWT token in Authorization header.'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        user = request.user
        data = request.data
        package_id = data.get('package_id')
        payment_method_id = data.get('payment_method_id')
        
        if not package_id:
            return Response({
                'success': False,
                'error': 'package_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the selected package
            package = SubscriptionPlan.objects.get(id=package_id, is_active=True)
            
            # Check if user already has any subscription (due to OneToOneField constraint)
            existing_subscription = Subscription.objects.filter(user=user).first()
            
            if existing_subscription:
                # If the existing subscription is inactive, we could potentially update it
                # instead of creating a new one, but for now we'll prevent duplicate creation
                return Response({
                    'success': False,
                    'error': 'User already has a subscription. Please cancel or modify the existing subscription first.',
                    'existing_subscription': {
                        'id': str(existing_subscription.id),
                        'plan_name': existing_subscription.plan.name,
                        'status': existing_subscription.status,
                        'current_period_end': existing_subscription.current_period_end.isoformat() if existing_subscription.current_period_end else None
                    }
                }, status=status.HTTP_409_CONFLICT)
            
            # Create or get Stripe customer
            stripe_customer = None
            if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
                stripe_customer = stripe.Customer.retrieve(user.stripe_customer_id)
            else:
                stripe_customer = stripe.Customer.create(
                    email=user.email,
                    name=user.get_full_name() or user.email,
                )
                user.stripe_customer_id = stripe_customer.id
                user.save()
            
            # Attach payment method if provided
            if payment_method_id:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=stripe_customer.id,
                )
                
                # Set as default payment method
                stripe.Customer.modify(
                    stripe_customer.id,
                    invoice_settings={'default_payment_method': payment_method_id},
                )
                
                # Save payment method to local database
                try:
                    from .models import PaymentMethod
                    stripe_pm = stripe.PaymentMethod.retrieve(payment_method_id)
                    
                    # Check if payment method already exists
                    local_pm, created = PaymentMethod.objects.get_or_create(
                        user=user,
                        stripe_payment_method_id=payment_method_id,
                        defaults={
                            'card_type': stripe_pm.card.brand if stripe_pm.card else 'unknown',
                            'last_four': stripe_pm.card.last4 if stripe_pm.card else '0000',
                            'exp_month': stripe_pm.card.exp_month if stripe_pm.card else 1,
                            'exp_year': stripe_pm.card.exp_year if stripe_pm.card else 2030,
                            'is_default': True,  # First payment method is default
                            'is_active': True,
                        }
                    )
                    
                    if created:
                        print(f"✅ Payment method saved to local DB: {local_pm.id}")
                    else:
                        # Update as default if it's being used for subscription
                        local_pm.is_default = True
                        local_pm.save()
                        print(f"✅ Payment method updated as default: {local_pm.id}")
                        
                except Exception as pm_error:
                    print(f"⚠️ Could not save payment method to local DB: {str(pm_error)}")
                    # Continue anyway, Stripe integration is more important
            
            # Create Stripe subscription with automatic confirmation for frontend compatibility
            subscription_params = {
                'customer': stripe_customer.id,
                'items': [{'price': package.stripe_price_id}],
                'payment_behavior': 'default_incomplete',
                'payment_settings': {'save_default_payment_method': 'on_subscription'},
                'expand': ['latest_invoice.payment_intent'],
            }
            
            # If payment method provided, use it as default
            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id
            
            stripe_subscription = stripe.Subscription.create(**subscription_params)
            
            # Create local subscription record
            # Convert Unix timestamps to datetime objects with safe handling
            try:
                if hasattr(stripe_subscription, 'current_period_start') and stripe_subscription.current_period_start:
                    period_start = datetime.fromtimestamp(stripe_subscription.current_period_start, tz=dt_timezone.utc)
                else:
                    period_start = timezone.now()
                    
                if hasattr(stripe_subscription, 'current_period_end') and stripe_subscription.current_period_end:
                    period_end = datetime.fromtimestamp(stripe_subscription.current_period_end, tz=dt_timezone.utc)
                else:
                    # Default to 1 month from now if not available
                    period_end = timezone.now() + timedelta(days=30)
            except (ValueError, TypeError, OSError) as e:
                # Fallback for timestamp conversion errors
                period_start = timezone.now()
                period_end = timezone.now() + timedelta(days=30)
            
            subscription = Subscription.objects.create(
                user=user,
                plan=package,
                stripe_subscription_id=stripe_subscription.id,
                stripe_customer_id=stripe_customer.id,
                stripe_payment_method_id=payment_method_id if payment_method_id else '',
                status='active',
                current_period_start=period_start,
                current_period_end=period_end,
            )
            
            # Enhanced client_secret extraction with guaranteed PaymentIntent creation
            client_secret = None
            try:
                # Method 1: Extract from subscription's latest invoice
                latest_invoice = getattr(stripe_subscription, 'latest_invoice', None)
                if latest_invoice:
                    payment_intent = getattr(latest_invoice, 'payment_intent', None)
                    if payment_intent:
                        client_secret = getattr(payment_intent, 'client_secret', None)
                
                # Method 2: If no client_secret found, create PaymentIntent manually
                if not client_secret:
                    try:
                        # Create PaymentIntent for the subscription amount
                        payment_intent = stripe.PaymentIntent.create(
                            amount=int(float(package.price) * 100),  # Convert to cents
                            currency='usd',
                            customer=stripe_customer.id,
                            payment_method=payment_method_id if payment_method_id else None,
                            confirmation_method='automatic',  # Changed to automatic for frontend compatibility
                            confirm=False,
                            setup_future_usage='off_session',
                            metadata={
                                'subscription_id': stripe_subscription.id,
                                'package_id': str(package.id),
                                'user_id': str(user.id)
                            }
                        )
                        client_secret = payment_intent.client_secret
                        print(f"✅ Created PaymentIntent manually: {payment_intent.id}")
                        
                    except Exception as pi_error:
                        print(f"⚠️ PaymentIntent creation failed: {str(pi_error)}")
                        
                        # Method 3: Create SetupIntent for future payments if PaymentIntent fails
                        try:
                            setup_intent = stripe.SetupIntent.create(
                                customer=stripe_customer.id,
                                payment_method=payment_method_id if payment_method_id else None,
                                payment_method_types=['card'],
                                usage='off_session',
                                confirm=False,
                                metadata={
                                    'subscription_id': stripe_subscription.id,
                                    'package_id': str(package.id)
                                }
                            )
                            client_secret = setup_intent.client_secret
                            print(f"✅ Created SetupIntent as fallback: {setup_intent.id}")
                        except Exception as si_error:
                            print(f"❌ SetupIntent creation also failed: {str(si_error)}")
                        
            except Exception as e:
                print(f"❌ Client secret extraction error: {str(e)}")
                client_secret = None
            
            # Enhanced response with debugging info
            response_data = {
                'success': True,
                'message': 'Subscription created successfully',
                'subscription': {
                    'id': str(subscription.id),
                    'plan_name': package.name,
                    'status': subscription.status,
                    'client_secret': client_secret,
                    'stripe_subscription_id': stripe_subscription.id,
                    'stripe_subscription_status': stripe_subscription.status,
                    'requires_payment_method': client_secret is not None,
                }
            }
            
            # Add helpful debugging information
            if not client_secret:
                response_data['debug_info'] = {
                    'stripe_subscription_status': stripe_subscription.status,
                    'has_latest_invoice': hasattr(stripe_subscription, 'latest_invoice'),
                    'payment_method_provided': payment_method_id is not None,
                    'suggestion': 'Try providing a payment_method_id or check Stripe dashboard'
                }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Package not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        except StripeError as e:
            return Response({
                'success': False,
                'error': f'Payment error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error creating subscription: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserSubscriptionManagementAPIView(APIView):
    """
    User Subscription Management - View and manage current subscription
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Subscription Management'],
        operation_summary="Get Current Subscription",
        operation_description="Get user's current subscription details and usage",
        responses={
            200: openapi.Response(
                description="Current subscription details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'subscription': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING),
                                'plan_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                'price_monthly': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'current_period_start': openapi.Schema(type=openapi.TYPE_STRING),
                                'current_period_end': openapi.Schema(type=openapi.TYPE_STRING),
                                'minutes_used': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'minutes_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'usage_percentage': openapi.Schema(type=openapi.TYPE_NUMBER),
                            }
                        )
                    }
                )
            ),
            404: "No active subscription found",
            401: "Authentication required"
        }
    )
    def get(self, request):
        """Get user's current subscription details"""
        user = request.user
        
        try:
            subscription = Subscription.objects.select_related('plan').get(
                user=user,
                status='active'
            )
            
            # Calculate usage percentage
            usage_percentage = 0
            if subscription.plan.call_minutes_limit > 0:
                usage_percentage = (subscription.minutes_used_this_month / subscription.plan.call_minutes_limit) * 100
            
            subscription_data = {
                'id': str(subscription.id),
                'plan_name': subscription.plan.name,
                'status': subscription.status,
                'price_monthly': float(subscription.plan.price),
                'current_period_start': subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                'minutes_used': subscription.minutes_used_this_month,
                'minutes_limit': subscription.plan.call_minutes_limit,
                'usage_percentage': round(usage_percentage, 2),
                'agents_allowed': subscription.plan.agents_allowed,
                'analytics_access': subscription.plan.analytics_access,
                'stripe_subscription_id': subscription.stripe_subscription_id,
            }
            
            return Response({
                'success': True,
                'subscription': subscription_data
            }, status=status.HTTP_200_OK)
            
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active subscription found',
                'message': 'Please select a subscription package'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @swagger_auto_schema(
        tags=['User - Subscription Management'],
        operation_summary="Cancel Subscription",
        operation_description="Cancel user's current subscription",
        responses={
            200: "Subscription cancelled successfully",
            404: "No active subscription found",
            401: "Authentication required"
        }
    )
    def delete(self, request):
        """Cancel user's subscription"""
        user = request.user
        
        try:
            subscription = Subscription.objects.get(
                user=user,
                status='active'
            )
            
            # Cancel Stripe subscription
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update local subscription
            subscription.cancel_at_period_end = True
            subscription.save()
            
            return Response({
                'success': True,
                'message': 'Subscription will be cancelled at the end of current billing period',
                'cancellation_date': subscription.current_period_end.isoformat() if subscription.current_period_end else None
            }, status=status.HTTP_200_OK)
            
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
        except StripeError as e:
            return Response({
                'success': False,
                'error': f'Error cancelling subscription: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        tags=['User - Subscription Management'],
        operation_summary="Upgrade/Downgrade Subscription",
        operation_description="Change user's current subscription plan",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['new_package_id', 'action'],
            properties={
                'new_package_id': openapi.Schema(type=openapi.TYPE_STRING, description="New package ID"),
                'action': openapi.Schema(type=openapi.TYPE_STRING, enum=['upgrade', 'downgrade'], description="Action type"),
                'proration_behavior': openapi.Schema(type=openapi.TYPE_STRING, enum=['create_prorations', 'none'], description="How to handle prorations", default='create_prorations'),
            }
        ),
        responses={
            200: "Subscription changed successfully",
            400: "Bad request - validation error",
            404: "No active subscription found",
            401: "Authentication required"
        }
    )
    def put(self, request):
        """Upgrade or downgrade user's subscription plan"""
        user = request.user
        data = request.data
        new_package_id = data.get('new_package_id')
        action = data.get('action')
        proration_behavior = data.get('proration_behavior', 'create_prorations')
        
        if not all([new_package_id, action]):
            return Response({
                'success': False,
                'error': 'new_package_id and action are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if action not in ['upgrade', 'downgrade']:
            return Response({
                'success': False,
                'error': 'action must be either "upgrade" or "downgrade"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get current subscription
            current_subscription = Subscription.objects.select_related('plan').get(
                user=user,
                status='active'
            )
            
            # Get new package
            new_package = SubscriptionPlan.objects.get(id=new_package_id, is_active=True)
            
            # Validate upgrade/downgrade logic
            current_price = float(current_subscription.plan.price)
            new_price = float(new_package.price)
            
            if action == 'upgrade' and new_price <= current_price:
                return Response({
                    'success': False,
                    'error': 'New package price must be higher for upgrade',
                    'current_price': current_price,
                    'new_price': new_price
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if action == 'downgrade' and new_price >= current_price:
                return Response({
                    'success': False,
                    'error': 'New package price must be lower for downgrade',
                    'current_price': current_price,
                    'new_price': new_price
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update Stripe subscription
            stripe.Subscription.modify(
                current_subscription.stripe_subscription_id,
                items=[{
                    'id': stripe.Subscription.retrieve(current_subscription.stripe_subscription_id)['items']['data'][0]['id'],
                    'price': new_package.stripe_price_id,
                }],
                proration_behavior=proration_behavior,
            )
            
            # Update local subscription
            current_subscription.plan = new_package
            current_subscription.save()
            
            # Calculate price difference for prorations
            price_difference = new_price - current_price
            
            return Response({
                'success': True,
                'message': f'Successfully {action}d to {new_package.name}',
                'subscription': {
                    'id': str(current_subscription.id),
                    'plan_name': new_package.name,
                    'new_price': new_price,
                    'price_difference': price_difference,
                    'action': action,
                    'proration_applied': proration_behavior == 'create_prorations'
                }
            }, status=status.HTTP_200_OK)
            
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'New package not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND) 
        except StripeError as e:
            return Response({
                'success': False,
                'error': f'Payment error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error changing subscription: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserInvoiceManagementAPIView(APIView):
    """
    User Invoice Management - View and download invoices
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Invoice Management'],
        operation_summary="Get User Invoices",
        operation_description="Get user's billing history and invoices",
        manual_parameters=[
            openapi.Parameter('limit', openapi.IN_QUERY, description="Number of invoices to return", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING, enum=['paid', 'pending', 'failed']),
        ],
        responses={
            200: openapi.Response(
                description="User invoices",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'invoices': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'invoice_number': openapi.Schema(type=openapi.TYPE_STRING),
                                    'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'currency': openapi.Schema(type=openapi.TYPE_STRING),
                                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                                    'invoice_pdf': openapi.Schema(type=openapi.TYPE_STRING),
                                    'plan_name': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        )
                    }
                )
            ),
            404: "No subscription found",
            401: "Authentication required"
        }
    )
    def get(self, request):
        """Get user's invoices and billing history"""
        user = request.user
        limit = int(request.query_params.get('limit', 10))
        status_filter = request.query_params.get('status')
        
        try:
            # Get user's subscription to access billing history
            subscription = Subscription.objects.get(
                user=user,
                status__in=['active', 'past_due', 'cancelled']  # Include past subscriptions
            )
            
            # Build query
            billing_query = BillingHistory.objects.filter(
                subscription=subscription
            ).select_related('subscription__plan').order_by('-created_at')
            
            if status_filter:
                billing_query = billing_query.filter(status=status_filter)
            
            # Limit results
            billing_history = billing_query[:limit]
            
            # Format invoice data
            invoices = []
            for bill in billing_history:
                invoices.append({
                    'id': str(bill.id),
                    'invoice_number': bill.stripe_invoice_id or f"INV-{bill.id}",
                    'amount': float(bill.amount),
                    'currency': bill.currency or 'usd',
                    'status': bill.status,
                    'description': bill.description,
                    'created_at': bill.created_at.isoformat(),
                    'invoice_pdf': bill.invoice_pdf,
                    'plan_name': bill.subscription.plan.name,
                })
            
            return Response({
                'success': True,
                'message': f'Found {len(invoices)} invoices',
                'invoices': invoices,
                'total_invoices': billing_query.count()
            }, status=status.HTTP_200_OK)
            
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No subscription found for invoice access'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @swagger_auto_schema(
        tags=['User - Invoice Management'],
        operation_summary="Download Invoice PDF",
        operation_description="Get direct download link for invoice PDF",
        manual_parameters=[
            openapi.Parameter('invoice_id', openapi.IN_QUERY, description="Invoice ID", type=openapi.TYPE_STRING, required=True)
        ],
        responses={
            200: openapi.Response(
                description="Invoice download link",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'download_url': openapi.Schema(type=openapi.TYPE_STRING),
                        'invoice_number': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            404: "Invoice not found",
            401: "Authentication required"
        }
    )
    def post(self, request):
        """Get invoice PDF download link"""
        user = request.user
        invoice_id = request.query_params.get('invoice_id')
        
        if not invoice_id:
            return Response({
                'success': False,
                'error': 'invoice_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get invoice belonging to user
            billing_record = BillingHistory.objects.select_related('subscription').get(
                id=invoice_id,
                subscription__user=user
            )
            
            # If we have a Stripe invoice PDF URL, return it
            if billing_record.invoice_pdf:
                return Response({
                    'success': True,
                    'download_url': billing_record.invoice_pdf,
                    'invoice_number': billing_record.stripe_invoice_id or f"INV-{billing_record.id}",
                    'amount': float(billing_record.amount),
                    'status': billing_record.status
                }, status=status.HTTP_200_OK)
            
            # If no PDF URL, try to get it from Stripe
            if billing_record.stripe_invoice_id:
                try:
                    stripe_invoice = stripe.Invoice.retrieve(billing_record.stripe_invoice_id)
                    if stripe_invoice.invoice_pdf:
                        # Update our record with the PDF URL
                        billing_record.invoice_pdf = stripe_invoice.invoice_pdf
                        billing_record.save()
                        
                        return Response({
                            'success': True,
                            'download_url': stripe_invoice.invoice_pdf,
                            'invoice_number': billing_record.stripe_invoice_id,
                            'amount': float(billing_record.amount),
                            'status': billing_record.status
                        }, status=status.HTTP_200_OK)
                except StripeError:
                    pass
            
            return Response({
                'success': False,
                'error': 'Invoice PDF not available for download'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except BillingHistory.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invoice not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)


class UserBillingPortalAPIView(APIView):
    """
    User Billing Portal - Generate Stripe billing portal session for self-service billing
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Billing Management'],
        operation_summary="Access Billing Portal",
        operation_description="Generate Stripe billing portal session URL for self-service billing management",
        responses={
            200: openapi.Response(
                description="Billing portal session created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'portal_url': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "No active subscription or Stripe customer",
            401: "Authentication required"
        }
    )
    def post(self, request):
        """Generate Stripe billing portal session URL"""
        try:
            # Get user's active subscription
            subscription = Subscription.objects.filter(
                user=request.user,
                status='active'
            ).first()
            
            if not subscription or not subscription.stripe_customer_id:
                return Response({
                    'success': False,
                    'error': 'No active subscription with Stripe customer found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create Stripe billing portal session
            portal_session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=f"{settings.FRONTEND_URL}/dashboard/billing"
            )
            
            return Response({
                'success': True,
                'message': 'Billing portal session created successfully',
                'portal_url': portal_session.url
            }, status=status.HTTP_200_OK)
            
        except StripeError as e:
            return Response({
                'success': False,
                'error': f'Stripe error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Failed to create billing portal session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSubscribeAPIView(APIView):
    """
    User Subscription - Subscribe to a package
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Subscription'],
        operation_summary="Subscribe to Package",
        operation_description="Subscribe user to selected package",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['package_id'],
            properties={
                'package_id': openapi.Schema(type=openapi.TYPE_STRING, description="Package ID to subscribe to"),
                'billing_cycle': openapi.Schema(type=openapi.TYPE_STRING, description="Billing cycle", default="month"),
            }
        ),
        responses={
            200: "Subscription successful",
            400: "Bad request",
            401: "Authentication required"
        }
    )
    def post(self, request):
        """Subscribe user to package"""
        user = request.user
        data = request.data
        
        try:
            package_id = data.get('package_id')
            if not package_id:
                return Response({
                    'success': False,
                    'error': 'package_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            package = SubscriptionPlan.objects.get(id=package_id, is_active=True)
            
            # Check existing subscription
            existing = Subscription.objects.filter(user=user, status='active').first()
            if existing:
                return Response({
                    'success': False,
                    'error': f'Already subscribed to {existing.plan.name}',
                    'current_subscription': existing.plan.name
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create subscription (simplified for development)
            subscription = Subscription.objects.create(
                user=user,
                plan=package,
                status='active',
                current_period_start=timezone.now(),
                current_period_end=timezone.now() + timedelta(days=30)
            )
            
            return Response({
                'success': True,
                'message': f'Successfully subscribed to {package.name}',
                'subscription': {
                    'id': str(subscription.id),
                    'plan_name': package.name,
                    'status': subscription.status,
                    'features': {
                        'campaigns': package.concurrent_calls if package.auto_campaigns else 0,  # number
                        'api_access': package.api_access,  # boolean
                        'advanced_analytics': package.advanced_analytics if package.analytics_access else False,  # boolean
                    }
                }
            }, status=status.HTTP_200_OK)
            
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Package not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Subscription failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class AdminStatisticsAPIView(APIView):
    """
    Admin Statistics - Subscription and revenue statistics
    """
    permission_classes = [IsAdmin]
    
    @swagger_auto_schema(
        tags=['Admin - Statistics'],
        operation_summary="Get Subscription Statistics",
        operation_description="Get comprehensive subscription and revenue statistics - ADMIN ONLY",
        responses={
            200: "Statistics retrieved successfully",
            403: "Forbidden - Admin access required"
        }
    )
    def get(self, request):
        """Get subscription statistics"""
        try:
            from django.db.models import Sum, Count
            from datetime import datetime, timedelta
            
            # Total subscriptions
            total_subscriptions = Subscription.objects.count()
            active_subscriptions = Subscription.objects.filter(status='active').count()
            
            # Revenue calculations (simplified)
            monthly_revenue = Subscription.objects.filter(
                status='active'
            ).aggregate(
                total=Sum('plan__price')
            )['total'] or 0
            
            # Active users
            active_users = Subscription.objects.filter(status='active').values('user').distinct().count()
            
            # Package distribution
            package_stats = list(Subscription.objects.values(
                'plan__name'
            ).annotate(
                subscriber_count=Count('id')
            ).order_by('-subscriber_count'))
            
            return Response({
                'success': True,
                'statistics': {
                    'total_subscriptions': total_subscriptions,
                    'active_subscriptions': active_subscriptions,
                    'monthly_revenue': float(monthly_revenue),
                    'active_users': active_users,
                    'package_distribution': package_stats,
                    'generated_at': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error retrieving statistics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    """API for updating existing user subscriptions (upgrade/downgrade)"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'new_package_id': openapi.Schema(type=openapi.TYPE_STRING, description='New subscription package ID'),
                'payment_method_id': openapi.Schema(type=openapi.TYPE_STRING, description='Payment method ID (optional)'),
            },
            required=['new_package_id']
        ),
        responses={
            200: openapi.Response('Subscription updated successfully'),
            400: 'Bad request',
            404: 'Subscription not found',
            409: 'Conflict - cannot update subscription'
        }
    )
    def post(self, request):
        try:
            user = request.user
            new_package_id = request.data.get('new_package_id')
            payment_method_id = request.data.get('payment_method_id')
            
            if not new_package_id:
                return Response({
                    'success': False,
                    'error': 'new_package_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user's existing subscription
            existing_subscription = Subscription.objects.filter(user=user).first()
            if not existing_subscription:
                return Response({
                    'success': False,
                    'error': 'No existing subscription found. Please create a new subscription first.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the new package
            new_package = SubscriptionPlan.objects.get(id=new_package_id, is_active=True)
            
            # Check if it's the same plan
            if existing_subscription.plan.id == new_package.id:
                return Response({
                    'success': False,
                    'error': 'User is already subscribed to this plan'
                }, status=status.HTTP_409_CONFLICT)
            
            # Update the Stripe subscription
            if existing_subscription.stripe_subscription_id:
                stripe_subscription = stripe.Subscription.retrieve(existing_subscription.stripe_subscription_id)
                
                # Update the subscription with new price
                updated_stripe_subscription = stripe.Subscription.modify(
                    existing_subscription.stripe_subscription_id,
                    items=[{
                        'id': stripe_subscription['items']['data'][0]['id'],
                        'price': new_package.stripe_price_id,
                    }],
                    proration_behavior='create_prorations',  # Handle prorations
                )
                
                # Update local subscription record
                existing_subscription.plan = new_package
                existing_subscription.status = 'active'
                existing_subscription.save()
                
                return Response({
                    'success': True,
                    'message': 'Subscription updated successfully',
                    'subscription': {
                        'id': str(existing_subscription.id),
                        'old_plan': existing_subscription.plan.name if existing_subscription.plan else 'Unknown',
                        'new_plan': new_package.name,
                        'status': existing_subscription.status,
                        'current_period_end': existing_subscription.current_period_end.isoformat() if existing_subscription.current_period_end else None
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'No Stripe subscription found for this user'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'New package not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error updating subscription: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
