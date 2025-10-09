from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import stripe
# Generic exception handling for all Stripe versions
StripeError = Exception
import logging

logger = logging.getLogger(__name__)

from .models import PaymentMethod
from .stripe_service import BillingService, WebhookService

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentMethodsAPIView(APIView):
    """
    Payment Methods Management API - List and Add payment methods
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Payment Methods'],
        operation_summary="List Payment Methods",
        operation_description="Get user's saved payment methods with safe data only",
        responses={
            200: openapi.Response(
                description="Payment methods list",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'payment_methods': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'card_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'last_four': openapi.Schema(type=openapi.TYPE_STRING),
                                    'exp_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'exp_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'is_default': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'display_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'expires': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                        'total_methods': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            401: "Authentication required"
        }
    )
    def get(self, request):
        """List user's payment methods - fetch from Stripe"""
        try:
            user = request.user
            methods_data = []
            
            # First try to get from local database
            local_methods = PaymentMethod.objects.filter(
                user=user,
                is_active=True
            ).order_by('-is_default', '-created_at')
            
            for pm in local_methods:
                methods_data.append({
                    'id': str(pm.id),
                    'stripe_pm_id': pm.stripe_payment_method_id,
                    'card_type': pm.card_type,
                    'last_four': pm.last_four,
                    'exp_month': pm.exp_month,
                    'exp_year': pm.exp_year,
                    'is_default': pm.is_default,
                    'display_name': f"{pm.card_type.title()} •••• {pm.last_four}",
                    'expires': f"{pm.exp_month:02d}/{pm.exp_year}",
                    'created_at': pm.created_at.isoformat(),
                    'source': 'local'
                })
            
            # Also fetch from Stripe if user has subscriptions
            from .models import Subscription
            user_subscription = Subscription.objects.filter(user=user).first()
            
            if user_subscription and user_subscription.stripe_customer_id:
                try:
                    # Fetch payment methods from Stripe
                    stripe_methods = stripe.PaymentMethod.list(
                        customer=user_subscription.stripe_customer_id,
                        type='card',
                    )
                    
                    # Get customer's default payment method
                    customer = stripe.Customer.retrieve(user_subscription.stripe_customer_id)
                    default_pm_id = None
                    if customer.invoice_settings and customer.invoice_settings.default_payment_method:
                        default_pm_id = customer.invoice_settings.default_payment_method
                    
                    # Add Stripe methods that are not in local database
                    existing_stripe_ids = set(pm.stripe_payment_method_id for pm in local_methods if pm.stripe_payment_method_id)
                    
                    for stripe_pm in stripe_methods.data:
                        if stripe_pm.id not in existing_stripe_ids:
                            methods_data.append({
                                'id': stripe_pm.id,  # Use Stripe ID as fallback
                                'stripe_pm_id': stripe_pm.id,
                                'card_type': stripe_pm.card.brand,
                                'last_four': stripe_pm.card.last4,
                                'exp_month': stripe_pm.card.exp_month,
                                'exp_year': stripe_pm.card.exp_year,
                                'is_default': stripe_pm.id == default_pm_id,
                                'display_name': f"{stripe_pm.card.brand.title()} •••• {stripe_pm.card.last4}",
                                'expires': f"{stripe_pm.card.exp_month:02d}/{stripe_pm.card.exp_year}",
                                'created_at': stripe_pm.created,
                                'source': 'stripe'
                            })
                            
                except Exception as stripe_error:
                    logger.warning(f"Could not fetch Stripe payment methods: {str(stripe_error)}")
            
            return Response({
                'success': True,
                'message': f'Found {len(methods_data)} payment methods',
                'payment_methods': methods_data,
                'total_methods': len(methods_data)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching payment methods for user {request.user.id}: {str(e)}")
            return Response({
                'success': False,
                'error': f'Error fetching payment methods: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        tags=['User - Payment Methods'],
        operation_summary="Add Payment Method",
        operation_description="Add new payment method using Stripe payment method ID from frontend",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['payment_method_id'],
            properties={
                'payment_method_id': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="Stripe payment method ID from frontend (e.g., pm_1ABC123xyz)"
                ),
                'set_as_default': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN, 
                    description="Set as default payment method",
                    default=False
                )
            }
        ),
        responses={
            201: "Payment method added successfully",
            400: "Bad request - validation error",
            401: "Authentication required"
        }
    )
    def post(self, request):
        """Add new payment method - receives token from frontend"""
        try:
            payment_method_id = request.data.get('payment_method_id')
            set_as_default = request.data.get('set_as_default', False)
            
            if not payment_method_id:
                return Response({
                    'success': False,
                    'error': 'payment_method_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if payment method already exists
            existing = PaymentMethod.objects.filter(
                user=request.user,
                stripe_payment_method_id=payment_method_id,
                is_active=True
            ).first()
            
            if existing:
                return Response({
                    'success': False,
                    'error': 'Payment method already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use existing service to attach payment method
            result = WebhookService.attach_payment_method(request.user, payment_method_id)
            
            if not result['success']:
                logger.error(f"Failed to attach payment method for user {request.user.id}: {result['error']}")
                return Response({
                    'success': False,
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Store payment method using existing service
            stored_pm = BillingService.store_payment_method(request.user, payment_method_id)
            
            if not stored_pm:
                return Response({
                    'success': False,
                    'error': 'Failed to store payment method details'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Set as default if requested
            if set_as_default:
                # Remove default from all others
                PaymentMethod.objects.filter(
                    user=request.user,
                    is_default=True
                ).exclude(id=stored_pm.id).update(is_default=False)
                
                # Set this as default
                stored_pm.is_default = True
                stored_pm.save()
                
                # Update in Stripe if customer exists
                if hasattr(request.user, 'stripe_customer_id') and request.user.stripe_customer_id:
                    try:
                        stripe.Customer.modify(
                            request.user.stripe_customer_id,
                            invoice_settings={
                                'default_payment_method': payment_method_id
                            }
                        )
                    except StripeError as e:
                        logger.warning(f"Failed to set default in Stripe: {str(e)}")
            
            logger.info(f"Payment method added successfully for user {request.user.id}")
            
            return Response({
                'success': True,
                'message': 'Payment method added successfully',
                'payment_method': {
                    'id': str(stored_pm.id),
                    'display_name': f"{stored_pm.card_type.title()} •••• {stored_pm.last_four}",
                    'is_default': stored_pm.is_default
                },
                'set_as_default': stored_pm.is_default
            }, status=status.HTTP_201_CREATED)
            
        except StripeError as e:
            logger.error(f"Stripe error adding payment method: {str(e)}")
            return Response({
                'success': False,
                'error': f'Payment processing error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error adding payment method for user {request.user.id}: {str(e)}")
            return Response({
                'success': False,
                'error': f'Error adding payment method: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentMethodDetailAPIView(APIView):
    """
    Individual Payment Method Management - Update and Delete
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Payment Methods'],
        operation_summary="Update Payment Method",
        operation_description="Update payment method settings (set as default)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['pm_id'],
            properties={
                'set_as_default': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Set this payment method as default"
                ),
                  'pm_id': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="Stripe payment method ID from frontend (e.g., pm_1ABC123xyz)"
                ),
            }
        ),
        responses={
            200: "Payment method updated successfully",
            400: "Bad request",
            404: "Payment method not found",
            401: "Authentication required"
        }
    )
    def put(self, request):
        """Update user's payment method - set new one as default, keep others active but not default"""
        try:
            new_pm_id = request.data.get('pm_id')
            
            if not new_pm_id:
                return Response({
                    'success': False,
                    'error': 'pm_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = request.user
            logger.info(f"Setting payment method as default for user {user.id} with PM: {new_pm_id}")
            
            # Step 1: Get current user's payment details
            current_methods = PaymentMethod.objects.filter(
                user=user,
                is_active=True
            ).order_by('-is_default', '-created_at')
            
            logger.info(f"Found {current_methods.count()} active payment methods for user {user.id}")
            
            # Step 2: Check if new payment method already exists
            existing_new_pm = PaymentMethod.objects.filter(
                user=user,
                stripe_payment_method_id=new_pm_id
            ).first()
            
            if existing_new_pm:
                if existing_new_pm.is_active and existing_new_pm.is_default:
                    return Response({
                        'success': False,
                        'error': 'This payment method is already the default for this user'
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Activate and set as default
                    existing_new_pm.is_active = True
                    existing_new_pm.is_default = True
                    existing_new_pm.save()
                    new_payment_method = existing_new_pm
                    logger.info(f"Set existing payment method {new_pm_id} as default for user {user.id}")
            else:
                # Step 3: Add new payment method using Stripe API
                try:
                    # Retrieve payment method from Stripe to get details
                    stripe_pm = stripe.PaymentMethod.retrieve(new_pm_id)
                    
                    # Create new payment method record
                    new_payment_method = PaymentMethod.objects.create(
                        user=user,
                        stripe_payment_method_id=new_pm_id,
                        card_type=stripe_pm.card.brand if stripe_pm.card else 'unknown',
                        last_four=stripe_pm.card.last4 if stripe_pm.card else '0000',
                        exp_month=stripe_pm.card.exp_month if stripe_pm.card else 1,
                        exp_year=stripe_pm.card.exp_year if stripe_pm.card else 2030,
                        is_default=True,
                        is_active=True
                    )
                    logger.info(f"Created new payment method {new_pm_id} as default for user {user.id}")
                    
                except StripeError as e:
                    logger.error(f"Failed to retrieve payment method from Stripe: {str(e)}")
                    return Response({
                        'success': False,
                        'error': f'Invalid payment method: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Step 4: First set ALL OTHER existing methods to false, then ensure new one is true
            # Make all OTHER payment methods non-default (exclude the new one)
            existing_updated_count = PaymentMethod.objects.filter(
                user=user,
                is_active=True
            ).exclude(id=new_payment_method.id).update(is_default=False)
            
            # Ensure the new payment method is definitely set as default
            new_payment_method.is_default = True
            new_payment_method.save()
            
            logger.info(f"Set {existing_updated_count} existing payment methods to non-default and confirmed new method as default for user {user.id}")
            
            # Step 5: Update Stripe customer's default payment method
            from .models import Subscription
            user_subscription = Subscription.objects.filter(user=user).first()
            
            if user_subscription and user_subscription.stripe_customer_id:
                try:
                    # Attach payment method to customer if not already attached
                    stripe.PaymentMethod.attach(
                        new_pm_id,
                        customer=user_subscription.stripe_customer_id
                    )
                    
                    # Set as default in Stripe
                    stripe.Customer.modify(
                        user_subscription.stripe_customer_id,
                        invoice_settings={
                            'default_payment_method': new_pm_id
                        }
                    )
                    logger.info(f"Updated Stripe customer default payment method to {new_pm_id}")
                    
                except StripeError as e:
                    logger.warning(f"Failed to update Stripe customer: {str(e)}")
                    # Continue anyway - local database is updated
            
            # Step 6: Return success response with user's payment method summary
            active_methods = PaymentMethod.objects.filter(
                user=user,
                is_active=True
            ).count()
            
            other_methods = PaymentMethod.objects.filter(
                user=user,
                is_active=True,
                is_default=False
            ).count()
            
            return Response({
                'success': True,
                'message': f'Payment method set as default successfully. {other_methods} other methods remain active.',
                'user_summary': {
                    'user_id': user.id,
                    'username': getattr(user, 'user_name', user.email),
                    'total_active_methods': active_methods,
                    'default_method_updated': True,
                    'other_methods_kept_active': other_methods
                },
                'new_default_method': {
                    'id': str(new_payment_method.id),
                    'stripe_id': new_payment_method.stripe_payment_method_id,
                    'display_name': f"{new_payment_method.card_type.title()} •••• {new_payment_method.last_four}",
                    'is_default': new_payment_method.is_default,
                    'is_active': new_payment_method.is_active,
                    'expires': f"{new_payment_method.exp_month:02d}/{new_payment_method.exp_year}"
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error updating default payment method for user {request.user.id}: {str(e)}")
            return Response({
                'success': False,
                'error': f'Error updating default payment method: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        tags=['User - Payment Methods'],
        operation_summary="Remove Payment Method",
        operation_description="Remove payment method from user account (soft delete)",
           request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['pm_id'],
            properties={
                  'pm_id': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="Stripe payment method ID from frontend (e.g., pm_1ABC123xyz)"
                ),
            }
        ),
        responses={
            200: "Payment method removed successfully",
            400: "Cannot remove default or last payment method",
            404: "Payment method not found",
            401: "Authentication required"
        }
    )
    def delete(self, request):
        """Remove payment method (soft delete)"""
        try:
            pm_id = request.data.get('pm_id')
            payment_method = PaymentMethod.objects.get(
                id=pm_id,
                user=request.user,
                is_active=True
            )
            
            # Check if it's the only payment method
            total_methods = PaymentMethod.objects.filter(
                user=request.user,
                is_active=True
            ).count()
            
            if total_methods == 1:
                return Response({
                    'success': False,
                    'error': 'Cannot remove the last payment method. Add another payment method first.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if it's default - user must set another as default first
            if payment_method.is_default:
                return Response({
                    'success': False,
                    'error': 'Cannot remove default payment method. Set another payment method as default first.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Detach from Stripe
            try:
                stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
                logger.info(f"Payment method detached from Stripe: {payment_method.stripe_payment_method_id}")
            except StripeError as e:
                # Continue with local deletion even if Stripe detach fails
                logger.warning(f"Failed to detach from Stripe but continuing: {str(e)}")
            
            # Soft delete - mark as inactive
            payment_method.is_active = False
            payment_method.save()
            
            logger.info(f"Payment method {pm_id} removed for user {request.user.id}")
            
            return Response({
                'success': True,
                'message': 'Payment method removed successfully'
            }, status=status.HTTP_200_OK)
            
        except PaymentMethod.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment method not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error removing payment method {pm_id} for user {request.user.id}: {str(e)}")
            return Response({
                'success': False,
                'error': f'Error removing payment method: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


"""
PAYMENT METHOD DATA STORAGE EXPLANATION
=====================================

This file explains exactly where payment method data is stored:

1. STRIPE STORAGE (Secure, Full Data):
   - Full card numbers (encrypted)
   - CVV codes
   - Billing addresses
   - Payment method tokens
   - Customer relationships

2. YOUR DATABASE STORAGE (Safe Metadata Only):
   - Payment method reference IDs
   - Card brand (visa, mastercard)
   - Last 4 digits only
   - Expiry month/year
   - Default status flags
   - User relationships

SECURITY: No sensitive data in your database!
"""

# Your PaymentMethod model stores ONLY safe data:
# 
# class PaymentMethod(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     
#     # ✅ SAFE DATA STORED IN YOUR DB:
#     stripe_payment_method_id = models.CharField(max_length=100)  # "pm_1ABC123xyz" (just reference)
#     card_type = models.CharField(max_length=20)                  # "visa" 
#     last_four = models.CharField(max_length=4)                   # "4242"
#     exp_month = models.IntegerField()                            # 12
#     exp_year = models.IntegerField()                             # 2025
#     is_default = models.BooleanField(default=False)             # True/False
#     is_active = models.BooleanField(default=True)               # True/False
#     
#     # ❌ SENSITIVE DATA NOT STORED IN YOUR DB:
#     # - Full card number (4242 4242 4242 4242)
#     # - CVV code (123)
#     # - PIN numbers
#     # - Full cardholder name
#     # - Complete billing address
