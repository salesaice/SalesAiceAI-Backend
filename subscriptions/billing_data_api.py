from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from datetime import datetime, timedelta
import stripe
from django.conf import settings

from .models import SubscriptionPlan, Subscription
from accounts.models import User

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class BillingDataAPIView(APIView):
    """
    Complete Billing Data API - Returns all billing information
    Matches BillingData TypeScript interface exactly
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Billing Data'],
        operation_summary="Get Complete Billing Data",
        operation_description="Get complete billing information including subscription, invoices, payment methods",
        responses={
            200: openapi.Response(
                description="Complete billing data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'billing_data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'subscription': openapi.Schema(type=openapi.TYPE_OBJECT),
                                'upcoming_invoice': openapi.Schema(type=openapi.TYPE_OBJECT),
                                'payment_methods': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                                ),
                                'invoices': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                                ),
                                'billing_address': openapi.Schema(type=openapi.TYPE_OBJECT)
                            }
                        )
                    }
                )
            ),
            401: "Authentication required",
            404: "No subscription found"
        }
    )
    def get(self, request):
        """Get complete billing data for user"""
        user = request.user
        
        try:
            # Get user's current subscription
            try:
                subscription = Subscription.objects.select_related('plan').get(
                    user=user,
                    status__in=['active', 'trialing', 'past_due', 'pending']
                )
            except Subscription.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'No active subscription found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Build subscription data
            subscription_data = {
                'id': str(subscription.id),
                'plan_name': subscription.plan.name,
                'plan_id': str(subscription.plan.id),
                'status': subscription.status,
                'current_period_start': subscription.current_period_start.isoformat(),
                'current_period_end': subscription.current_period_end.isoformat(),
                'price_monthly': float(subscription.plan.price),
                'price_yearly': float(subscription.plan.price * 10) if subscription.plan.billing_cycle == 'year' else None,
                'billing_cycle': subscription.plan.billing_cycle or 'monthly',
                'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'canceled_at': subscription.canceled_at.isoformat() if subscription.canceled_at else None,
                'features': self._get_subscription_features(subscription.plan),
                'usage': {
                    'calls_used': getattr(subscription, 'calls_used_this_month', 0),
                    'calls_limit': subscription.plan.concurrent_calls or 0,
                    'minutes_used': subscription.minutes_used_this_month or 0,
                    'minutes_limit': subscription.plan.call_minutes_limit or 0
                }
            }
            
            # Get upcoming invoice (mock data for now)
            upcoming_invoice = self._get_upcoming_invoice(subscription)
            
            # Get payment methods (mock data for now)
            payment_methods = self._get_payment_methods(user)
            
            # Get invoices (mock data for now)
            invoices = self._get_invoices(subscription)
            
            # Get billing address (mock data for now)
            billing_address = self._get_billing_address(user)
            
            # Build complete billing data
            billing_data = {
                'subscription': subscription_data,
                'upcoming_invoice': upcoming_invoice,
                'payment_methods': payment_methods,
                'invoices': invoices,
                'billing_address': billing_address
            }
            
            return Response({
                'success': True,
                'billing_data': billing_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error fetching billing data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_subscription_features(self, plan):
        """Get subscription features list"""
        features = []
        
        if plan.call_minutes_limit:
            features.append(f"Up to {plan.call_minutes_limit:,} minutes/month")
        
        if plan.agents_allowed:
            if plan.agents_allowed > 1:
                features.append(f"Up to {plan.agents_allowed} agents")
            else:
                features.append(f"{plan.agents_allowed} agent")
        
        if hasattr(plan, 'analytics_access') and plan.analytics_access:
            features.append("Real-time analytics")
        elif plan.price >= 25:
            features.append("Real-time analytics")
        
        if hasattr(plan, 'advanced_analytics') and plan.advanced_analytics:
            features.append("Advanced AI agents")
        elif plan.price >= 50:
            features.append("Advanced AI agents")
        
        if hasattr(plan, 'priority_support') and plan.priority_support:
            features.append("Priority support")
        elif plan.price >= 75:
            features.append("Priority support")
        
        if hasattr(plan, 'custom_integration') and plan.custom_integration:
            features.append("Custom integrations")
        elif plan.price >= 100:
            features.append("Custom integrations")
        
        return features
    
    def _get_upcoming_invoice(self, subscription):
        """Get upcoming invoice data"""
        # Calculate next billing date
        next_billing = subscription.current_period_end
        
        return {
            'amount': float(subscription.plan.price),
            'date': next_billing.isoformat(),
            'description': f"{subscription.plan.name} subscription renewal"
        }
    
    def _get_payment_methods(self, user):
        """Get user's payment methods from Stripe or local DB"""
        # Try Stripe first
        stripe_customer_id = getattr(user, 'stripe_customer_id', None)
        payment_methods = []
        if stripe_customer_id:
            try:
                stripe_methods = stripe.PaymentMethod.list(
                    customer=stripe_customer_id,
                    type="card"
                )
                for pm in stripe_methods.get('data', []):
                    payment_methods.append({
                        'id': pm['id'],
                        'type': pm['type'],
                        'brand': pm['card']['brand'],
                        'last4': pm['card']['last4'],
                        'exp_month': pm['card']['exp_month'],
                        'exp_year': pm['card']['exp_year'],
                        'bank_name': None,
                        'account_last4': None,
                        'email': pm.get('billing_details', {}).get('email'),
                        'is_default': pm.get('id') == getattr(user.subscription, 'stripe_payment_method_id', None),
                        'created_at': pm['created']
                    })
            except Exception:
                pass  # fallback to local
        if not payment_methods:
            # Fallback to local DB
            from .models import PaymentMethod
            for pm in PaymentMethod.objects.filter(user=user, is_active=True):
                payment_methods.append({
                    'id': pm.stripe_payment_method_id,
                    'type': 'card',
                    'brand': pm.card_type,
                    'last4': pm.last_four,
                    'exp_month': pm.exp_month,
                    'exp_year': pm.exp_year,
                    'bank_name': None,
                    'account_last4': None,
                    'email': user.email,
                    'is_default': pm.is_default,
                    'created_at': pm.created_at.isoformat()
                })
        return payment_methods
    
    # def _get_invoices(self, subscription):
    #     """Get user's invoices (mock data for now)"""
    #     # In real implementation, this would fetch from Stripe or your invoice model
    #     current_date = timezone.now()
        
    #     invoices = []
    #     for i in range(3):  # Generate 3 mock invoices
    #         invoice_date = current_date - timedelta(days=30 * (i + 1))
    #         period_start = invoice_date - timedelta(days=30)
    #         period_end = invoice_date
            
    #         base_amount = float(subscription.plan.price)
    #         tax_amount = base_amount * 0.08  # 8% tax
    #         total_amount = base_amount + tax_amount
            
    #         invoice = {
    #             'id': f'inv_{subscription.id}_{i+1}',
    #             'invoice_number': f'INV-{invoice_date.strftime("%Y%m")}-{1000 + i}',
    #             'date': invoice_date.isoformat(),
    #             'due_date': (invoice_date + timedelta(days=7)).isoformat(),
    #             'amount': base_amount,
    #             'tax': tax_amount,
    #             'total': total_amount,
    #             'status': 'paid' if i > 0 else 'pending',
    #             'description': f"{subscription.plan.name} subscription",
    #             'period_start': period_start.isoformat(),
    #             'period_end': period_end.isoformat(),
    #             'download_url': f"/api/invoices/{subscription.id}_{i+1}/download",
    #             'items': [
    #                 {
    #                     'description': f"{subscription.plan.name} Monthly Subscription",
    #                     'quantity': 1,
    #                     'unit_price': base_amount,
    #                     'total': base_amount
    #                 }
    #             ]
    #         }
    #         invoices.append(invoice)
        
    #     return invoices
    
    def _get_invoices(self, subscription):
        """Get user's invoices from Stripe"""
        stripe_customer_id = getattr(subscription.user, 'stripe_customer_id', None)
        if not stripe_customer_id:
            return []
        
        try:
            stripe_invoices = stripe.Invoice.list(
                customer=stripe_customer_id,
                limit=5  # Fetch last 5 invoices
            )
            
            invoice_list = []
            for inv in stripe_invoices.get('data', []):
                invoice_list.append({
                    'id': inv.id,
                    'invoice_number': inv.number,
                    'date': datetime.fromtimestamp(inv.created).isoformat(),
                    'due_date': datetime.fromtimestamp(inv.due_date).isoformat() if inv.due_date else None,
                    'amount': inv.amount_due / 100 if inv.amount_due else 0,
                    'tax': (inv.total - inv.amount_due) / 100 if inv.total and inv.amount_due else 0,
                    'total': inv.total / 100 if inv.total else 0,
                    'status': inv.status,
                    'description': f"Invoice for {subscription.plan.name} subscription",
                    'period_start': datetime.fromtimestamp(inv.period_start).isoformat() if inv.period_start else None,
                    'period_end': datetime.fromtimestamp(inv.period_end).isoformat() if inv.period_end else None,
                    'download_url': inv.invoice_pdf,
                    'items': [{
                        'description': line.description,
                        'quantity': line.quantity,
                        'unit_price': line.unit_amount / 100 if line.unit_amount else 0,
                        'total': line.amount / 100 if line.amount else 0
                    } for line in inv.lines.data]
                })
            return invoice_list
        except Exception as e:
            return []

    def _get_billing_address(self, user):
        """Get user's billing address from Stripe or fallback to user info"""
        stripe_customer_id = getattr(user, 'stripe_customer_id', None)
        if stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(stripe_customer_id)
                address = customer.get('address', {})
                return {
                    'name': customer.get('name') or user.get_full_name() or user.email,
                    'company': customer.get('company'),
                    'address_line1': address.get('line1'),
                    'address_line2': address.get('line2'),
                    'city': address.get('city'),
                    'state': address.get('state'),
                    'postal_code': address.get('postal_code'),
                    'country': address.get('country')
                }
            except Exception:
                pass  # fallback to user info
        # Fallback: minimal info
        return {
            'name': user.get_full_name() or user.email,
            'company': None,
            'address_line1': None,
            'address_line2': None,
            'city': None,
            'state': None,
            'postal_code': None,
            'country': None
        }
