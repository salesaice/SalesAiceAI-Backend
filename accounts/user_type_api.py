from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import User
from .permissions import IsAdmin
from subscriptions.models import Subscription


class UserTypeAPIView(APIView):
    """
    User Type API - Returns users in simple TypeScript UserType format
    """
    permission_classes = [permissions.IsAuthenticated]  # Any authenticated user can access
    
    @swagger_auto_schema(
        tags=['User Management - Authenticated'],
        operation_summary="Get Users in UserType Format (All Authenticated Users)",
        operation_description="Get all users in the exact TypeScript UserType interface format - Any authenticated user can access",
        responses={
            200: openapi.Response(
                description="List of users in UserType format",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='User full name'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email address'),
                            'role': openapi.Schema(
                                type=openapi.TYPE_STRING, 
                                enum=['admin', 'user'],
                                description='User role'
                            ),
                            'has_subscription': openapi.Schema(
                                type=openapi.TYPE_BOOLEAN, 
                                description='Whether user has a subscription',
                                default=False
                            ),
                            'subscription_status': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                enum=['active', 'inactive', 'expired', None],
                                description='Subscription status',
                                nullable=True
                            ),
                        },
                        required=['name', 'email', 'role']
                    )
                ),
                examples={
                    "application/json": [
                        {
                            "name": "John Doe",
                            "email": "john@example.com",
                            "role": "user",
                            "has_subscription": True,
                            "subscription_status": "active"
                        },
                        {
                            "name": "Admin User",
                            "email": "admin@gmail.com",
                            "role": "admin",
                            "has_subscription": False,
                            "subscription_status": None
                        }
                    ]
                }
            ),
            401: openapi.Response(description="Authentication required")
        }
    )
    # def get(self, request):
    #     """Get all users in UserType format"""
        
    #     try:
    #         # Get all users with their subscription data
    #         users = User.objects.select_related('subscription').all()
            
    #         user_list = []
            
    #         for user in users:
    #             # Get user's full name or use email prefix if no name
    #             full_name = user.get_full_name()
    #             if not full_name.strip():
    #                 full_name = user.email.split('@')[0] if user.email else 'Unknown User'
                
    #             # Check subscription status
    #             has_subscription = False
    #             subscription_status = None
                
    #             try:
    #                 subscription = getattr(user, 'subscription', None)
    #                 if subscription:
    #                     has_subscription = True
    #                     # Map Django subscription status to your format
    #                     if subscription.status == 'active':
    #                         subscription_status = 'active'
    #                     elif subscription.status in ['canceled', 'cancelled', 'unpaid']:
    #                         subscription_status = 'inactive'
    #                     elif subscription.status == 'expired':
    #                         subscription_status = 'expired'
    #                     else:
    #                         subscription_status = 'inactive'
    #                 else:
    #                     has_subscription = False
    #                     subscription_status = None
    #             except Exception:
    #                 has_subscription = False
    #                 subscription_status = None
                
    #             # Format user data according to TypeScript interface
    #             user_data = {
    #                 "name": full_name,
    #                 "email": user.email,
    #                 "role": "admin" if user.role == "admin" else "user",
    #                 "has_subscription": has_subscription,
    #                 "subscription_status": subscription_status
    #             }
                
    #             user_list.append(user_data)
            
    #         return Response(user_list, status=status.HTTP_200_OK)
            
    #     except Exception as e:
    #         return Response({
    #             "error": f"Failed to fetch users: {str(e)}"
    #         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def get(self, request):
     try:
        user = request.user

        # Get user's full name or use email prefix if no name
        full_name = user.get_full_name()
        if not full_name.strip():
            full_name = user.email.split('@')[0] if user.email else 'Unknown User'

        # Check subscription status
        has_subscription = False
        subscription_status = None

        try:
            subscription = getattr(user, 'subscription', None)
            if subscription:
                has_subscription = True
                # Map Django subscription status to your format
                if subscription.status == 'active':
                    subscription_status = 'active'
                elif subscription.status in ['canceled', 'cancelled', 'unpaid']:
                    subscription_status = 'inactive'
                elif subscription.status == 'expired':
                    subscription_status = 'expired'
                else:
                    subscription_status = 'inactive'
            else:
                has_subscription = False
                subscription_status = None
        except Exception:
            has_subscription = False
            subscription_status = None

        # Format user data according to TypeScript interface
        user_data = {
            "name": full_name,
            "email": user.email,
            "role": "admin" if getattr(user, "role", "") == "admin" else "user",
            "has_subscription": has_subscription,
            "subscription_status": subscription_status
        }

        return Response(user_data, status=status.HTTP_200_OK)
     except Exception as e:
        return Response({
            "error": f"Failed to fetch user: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        tags=['User Management - Authenticated'],
        operation_summary="Update User Subscription Status (Authenticated Users)",
        operation_description="Update a user's subscription status - Any authenticated user can access",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'subscription_status'],
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='User email to update'
                ),
                'subscription_status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['active', 'inactive', 'expired'],
                    description='New subscription status'
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="User updated successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "User subscription status updated successfully",
                        "user": {
                            "name": "John Doe",
                            "email": "john@example.com",
                            "role": "user",
                            "has_subscription": True,
                            "subscription_status": "active"
                        }
                    }
                }
            ),
            400: openapi.Response(description="Bad request"),
            404: openapi.Response(description="User not found")
        }
    )
    def post(self, request):
        """Update user subscription status"""
        
        email = request.data.get('email')
        new_status = request.data.get('subscription_status')
        
        if not email or not new_status:
            return Response({
                "error": "email and subscription_status are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in ['active', 'inactive', 'expired']:
            return Response({
                "error": "subscription_status must be 'active', 'inactive', or 'expired'"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "error": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Get or create subscription
            subscription = getattr(user, 'subscription', None)
            if subscription:
                # Map your status to Django status
                if new_status == 'active':
                    subscription.status = 'active'
                elif new_status == 'inactive':
                    subscription.status = 'canceled'
                elif new_status == 'expired':
                    subscription.status = 'expired'
                subscription.save()
            else:
                # User doesn't have a subscription, so we can't update status
                return Response({
                    "error": "User does not have a subscription to update"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return updated user data
            full_name = user.get_full_name()
            if not full_name.strip():
                full_name = user.email.split('@')[0] if user.email else 'Unknown User'
            
            updated_user = {
                "name": full_name,
                "email": user.email,
                "role": "admin" if user.role == "admin" else "user",
                "has_subscription": True,
                "subscription_status": new_status
            }
            
            return Response({
                "success": True,
                "message": "User subscription status updated successfully",
                "user": updated_user
            })
            
        except Exception as e:
            return Response({
                "error": f"Failed to update user: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
