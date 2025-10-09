from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import stripe
from django.conf import settings

from accounts.permissions import IsAdmin
from .models import SubscriptionPlan, Subscription

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class AdminPackageManagementAPIView(APIView):
    """
    Package Management - GET is public, CRUD operations require admin access
    Based on AdminPackage TypeScript interface
    """
    permission_classes = [permissions.AllowAny]  # Allow public access, check admin in individual methods
    
    @swagger_auto_schema(
        tags=['Package Management - Public'],
        operation_summary="Get All Packages (Public)",
        operation_description="Get all subscription packages with subscriber counts - PUBLIC ACCESS (No Auth Required)",
        responses={
            200: openapi.Response(
                description="List of packages",
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
                                    'minutes_inbound_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'minutes_outbound_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'minutes_total_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'agents_allowed': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'analytics_access': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'features': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'campaigns': openapi.Schema(type=openapi.TYPE_INTEGER, description="Campaign capacity (number)"),
                                            'api_access': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="API access permission"),
                                            'advanced_analytics': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Advanced analytics access"),
                                        }
                                    ),
                                    'extended_features': openapi.Schema(type=openapi.TYPE_OBJECT, description="Comprehensive feature details"),
                                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                                    'subscribers': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        )
                    }
                )
            ),
            403: "Forbidden - Admin access required"
        }
    )
    def get(self, request):
        """Get all packages with subscriber counts - Public access allowed"""
        # No authentication required for viewing packages
        packages = SubscriptionPlan.objects.annotate(
            subscriber_count=Count('subscription')
        ).order_by('-created_at')
        
        package_data = []
        for package in packages:
            # Prepare features object - Updated structure for frontend
            features = {
                'campaigns': package.concurrent_calls if package.auto_campaigns else 0,  # number - campaign capacity
                'api_access': package.api_access,  # boolean
                'advanced_analytics': package.advanced_analytics if package.analytics_access else False,  # boolean
            }
            
            # Extended features for comprehensive details  
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
                'subscribers': package.subscriber_count,  # Optional field
            })
        
        return Response({
            'success': True,
            'message': f'Found {len(package_data)} packages',
            'packages': package_data
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['Admin - Package Management'],
        operation_summary="Create New Package",
        operation_description="Create a new subscription package - ADMIN ONLY",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'price_monthly', 'minutes_total_limit', 'agents_allowed'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description="Package name"),
                'price_monthly': openapi.Schema(type=openapi.TYPE_NUMBER, description="Monthly price"),
                'minutes_inbound_limit': openapi.Schema(type=openapi.TYPE_INTEGER, description="Inbound call minutes"),
                'minutes_outbound_limit': openapi.Schema(type=openapi.TYPE_INTEGER, description="Outbound call minutes"),
                'minutes_total_limit': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total call minutes"),
                'agents_allowed': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of agents allowed"),
                'analytics_access': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Analytics access", default=False),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Package active status", default=True),
                'features': openapi.Schema(
                    type=openapi.TYPE_OBJECT, 
                    description="Package features",
                    properties={
                        'campaigns': openapi.Schema(type=openapi.TYPE_INTEGER, description="Campaign capacity (number of campaigns allowed)"),
                        'api_access': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="API access permission"),
                        'advanced_analytics': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Advanced analytics access"),
                    }
                ),
            }
        ),
        responses={
            201: openapi.Response(
                description="Package created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'package': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_STRING),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                'price_monthly': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'minutes_inbound_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'minutes_outbound_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'minutes_total_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'agents_allowed': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'analytics_access': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'features': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'campaigns': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                        'api_access': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                        'advanced_analytics': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    }
                                ),
                                'stripe_product_id': openapi.Schema(type=openapi.TYPE_STRING),
                                'stripe_price_id': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    }
                )
            ),
            400: "Bad request - validation error",
            403: "Forbidden - Admin access required"
        }
    )
    def post(self, request):
        """Create new subscription package - Admin only"""
        # Check admin permission
        if not request.user.is_authenticated or request.user.role != 'admin':
            return Response({
                "error": "Admin access required for package creation"
            }, status=status.HTTP_403_FORBIDDEN)
            
        data = request.data
        
        try:
            # Try to create Stripe product if keys are configured
            stripe_product_id = None
            stripe_price_id = None
            
            if settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY != 'sk_test_placeholder':
                try:
                    # Create Stripe product
                    stripe_product = stripe.Product.create(
                        name=data['name'],
                        description=f"Subscription package: {data['name']}"
                    )
                    
                    # Create Stripe price
                    stripe_price = stripe.Price.create(
                        unit_amount=int(float(data['price_monthly']) * 100),  # Convert to cents
                        currency='usd',
                        recurring={'interval': 'month'},
                        product=stripe_product.id,
                    )
                    
                    stripe_product_id = stripe_product.id
                    stripe_price_id = stripe_price.id
                    
                except stripe.error.StripeError as e:
                    print(f"Stripe error (continuing without Stripe): {str(e)}")
                    # Continue without Stripe integration
            else:
                print("Stripe keys not configured, creating package without Stripe integration")
            
            # Extract features - Support both structures
            features = data.get('features', {})
            
            # Main features (campaigns as number, api_access, advanced_analytics)
            campaigns_count = features.get('campaigns', 0)  # number of campaigns allowed
            api_access = features.get('api_access', False)  # boolean
            analytics_access = data.get('analytics_access', False)
            advanced_analytics = features.get('advanced_analytics', False)  # boolean
            
            # Set auto_campaigns based on campaigns count
            auto_campaigns_enabled = campaigns_count > 0
            
            # Create package
            package = SubscriptionPlan.objects.create(
                name=data['name'],
                plan_type='custom',
                price=data['price_monthly'],
                call_minutes_limit=data['minutes_total_limit'],
                minutes_inbound_limit=data.get('minutes_inbound_limit', data['minutes_total_limit'] // 2),
                minutes_outbound_limit=data.get('minutes_outbound_limit', data['minutes_total_limit'] // 2),
                agents_allowed=data['agents_allowed'],
                analytics_access=analytics_access,
                
                # Main features mapping
                auto_campaigns=auto_campaigns_enabled,  # campaigns -> auto_campaigns (boolean)
                api_access=api_access,  # api_access -> api_access (boolean)
                advanced_analytics=advanced_analytics if analytics_access else False,  # advanced_analytics (boolean)
                
                # Extended features from features object (backward compatibility)
                ai_agents_allowed=features.get('ai_agents_allowed', 1),
                concurrent_calls=max(campaigns_count, features.get('concurrent_calls', 5)),  # Use campaigns count as concurrent calls
                webhook_access=features.get('webhook_access', False),
                call_recording=features.get('call_recording', False),
                call_transcription=features.get('call_transcription', False),
                sentiment_analysis=features.get('sentiment_analysis', False),
                crm_integration=features.get('crm_integration', False),
                storage_gb=features.get('storage_gb', 1),
                backup_retention_days=features.get('backup_retention_days', 30),
                priority_support=features.get('priority_support', False),
                
                # Stripe integration (optional)
                stripe_product_id=stripe_product_id,
                stripe_price_id=stripe_price_id,
                
                is_active=data.get('is_active', True)
            )
            
            # Prepare features response
            package_features = {
                'campaigns': package.concurrent_calls if package.auto_campaigns else 0,  # number
                'api_access': package.api_access,  # boolean
                'advanced_analytics': package.advanced_analytics if package.analytics_access else False,  # boolean
            }
            
            return Response({
                'success': True,
                'message': 'Package created successfully',
                'package': {
                    'id': str(package.id),
                    'name': package.name,
                    'price_monthly': float(package.price),
                    'minutes_inbound_limit': package.minutes_inbound_limit,
                    'minutes_outbound_limit': package.minutes_outbound_limit,
                    'minutes_total_limit': package.call_minutes_limit,
                    'agents_allowed': package.agents_allowed,
                    'analytics_access': package.analytics_access,
                    'features': package_features,
                    'stripe_product_id': package.stripe_product_id or 'Not configured',
                    'stripe_price_id': package.stripe_price_id or 'Not configured', 
                    'is_active': package.is_active,
                    'created_at': package.created_at.isoformat(),
                }
            }, status=status.HTTP_201_CREATED)
            
        except stripe.error.StripeError as e:
            return Response({
                'success': False,
                'error': f'Stripe error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error creating package: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class AdminIndividualPackageAPIView(APIView):
    """
    Individual Package Management - GET is public, PUT/DELETE require admin access
    """
    permission_classes = [permissions.AllowAny]  # Allow public access, check admin in individual methods
    
    @swagger_auto_schema(
        tags=['Package Management - Public'],
        operation_summary="Get Single Package (Public)",
        operation_description="Get details of a specific package - PUBLIC ACCESS (No Auth Required)",
        responses={
            200: "Package details",
            404: "Package not found",
            403: "Forbidden - Admin access required"
        }
    )
    def get(self, request, package_id):
        """Get single package details - Public access allowed"""
        # No authentication required for viewing single package
        try:
            package = SubscriptionPlan.objects.get(id=package_id)
            
            # Prepare features
            features = {
                'campaigns': package.concurrent_calls if package.auto_campaigns else 0,  # number
                'api_access': package.api_access,  # boolean
                'advanced_analytics': package.advanced_analytics if package.analytics_access else False,  # boolean
            }
            
            package_data = {
                'id': str(package.id),
                'name': package.name,
                'price_monthly': float(package.price),
                'minutes_inbound_limit': package.minutes_inbound_limit,
                'minutes_outbound_limit': package.minutes_outbound_limit,
                'minutes_total_limit': package.call_minutes_limit,
                'agents_allowed': package.agents_allowed,
                'analytics_access': package.analytics_access,
                'features': features,
                'is_active': package.is_active,
                'created_at': package.created_at.isoformat(),
            }
            
            return Response({
                'success': True,
                'package': package_data
            }, status=status.HTTP_200_OK)
            
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Package not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @swagger_auto_schema(
        tags=['Admin - Package Management'],
        operation_summary="Update Package",
        operation_description="Update specific package - ADMIN ONLY",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'price_monthly': openapi.Schema(type=openapi.TYPE_NUMBER),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Package active status"),
                'features': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'campaigns': openapi.Schema(type=openapi.TYPE_INTEGER, description="Campaign capacity (number)"),
                        'api_access': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="API access permission"),
                        'advanced_analytics': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Advanced analytics access"),
                    }
                ),
            }
        ),
        responses={
            200: "Package updated successfully",
            404: "Package not found",
            403: "Forbidden - Admin access required"
        }
    )
    def put(self, request, package_id):
        """Update package - Admin only"""
        # Check admin permission
        if not request.user.is_authenticated or request.user.role != 'admin':
            return Response({
                "error": "Admin access required for package updates"
            }, status=status.HTTP_403_FORBIDDEN)
            
        try:
            package = SubscriptionPlan.objects.get(id=package_id)
            data = request.data
            
            # Update basic fields
            if 'name' in data:
                package.name = data['name']
            if 'price_monthly' in data:
                package.price = data['price_monthly']
            if 'is_active' in data:
                package.is_active = data['is_active']
            
            # Update features if provided
            if 'features' in data:
                features = data['features']
                if 'campaigns' in features:
                    campaigns_count = features['campaigns']  # number
                    package.auto_campaigns = campaigns_count > 0  # boolean
                    package.concurrent_calls = max(campaigns_count, package.concurrent_calls)  # Update concurrent calls
                if 'api_access' in features:
                    package.api_access = features['api_access']  # boolean
                if 'advanced_analytics' in features:
                    package.advanced_analytics = features['advanced_analytics']  # boolean
            
            package.save()
            
            # Prepare response features
            response_features = {
                'campaigns': package.concurrent_calls if package.auto_campaigns else 0,  # number
                'api_access': package.api_access,  # boolean
                'advanced_analytics': package.advanced_analytics if package.analytics_access else False,  # boolean
            }
            
            return Response({
                'success': True,
                'message': 'Package updated successfully',
                'package': {
                    'id': str(package.id),
                    'name': package.name,
                    'price_monthly': float(package.price),
                    'features': response_features,
                    'updated_at': package.updated_at.isoformat(),
                }
            }, status=status.HTTP_200_OK)
            
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Package not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @swagger_auto_schema(
        tags=['Admin - Package Management'],
        operation_summary="Delete Package",
        operation_description="Delete specific package - ADMIN ONLY",
        responses={
            204: "Package deleted successfully",
            404: "Package not found",
            403: "Forbidden - Admin access required"
        }
    )
    def delete(self, request, package_id):
        """Delete package - Admin only"""
        # Check admin permission
        if not request.user.is_authenticated or request.user.role != 'admin':
            return Response({
                "error": "Admin access required for package deletion"
            }, status=status.HTTP_403_FORBIDDEN)
            
        try:
            package = SubscriptionPlan.objects.get(id=package_id)
            package_name = package.name
            package.delete()
            
            return Response({
                'success': True,
                'message': f'Package "{package_name}" deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
            
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Package not found'
            }, status=status.HTTP_404_NOT_FOUND)
