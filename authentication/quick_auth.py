"""
Simple Authentication and Token Generation
Quick setup for API testing
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import check_password
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()


class QuickTokenAPIView(APIView):
    """Generate JWT token for testing - Quick setup"""
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['email', 'password']
        ),
        responses={
            200: openapi.Response(
                description="Token generated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access_token': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh_token': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            401: "Invalid credentials"
        },
        operation_description="Generate JWT tokens for API access",
        tags=['Authentication']
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get user
            user = User.objects.get(email=email)
            
            # Check password
            if check_password(password, user.password):
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                
                return Response({
                    'success': True,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer',
                    'expires_in': 3600,  # 1 hour
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'role': user.role,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_staff': user.is_staff,
                        'is_superuser': user.is_superuser,
                    }
                })
            else:
                return Response({
                    'error': 'Invalid password'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminTokenAPIView(APIView):
    """Quick admin token generation"""
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        responses={
            200: "Admin token generated",
            404: "Admin user not found"
        },
        operation_description="Generate admin token for testing (admin@gmail.com)",
        tags=['Authentication']
    )
    def get(self, request):
        try:
            # Get admin user
            admin_user = User.objects.get(email='admin@gmail.com')
            
            # Generate tokens
            refresh = RefreshToken.for_user(admin_user)
            access_token = str(refresh.access_token)
            
            return Response({
                'success': True,
                'message': 'Admin token generated successfully',
                'access_token': access_token,
                'token_type': 'Bearer',
                'user': {
                    'email': admin_user.email,
                    'role': admin_user.role,
                    'is_staff': admin_user.is_staff,
                    'is_superuser': admin_user.is_superuser,
                },
                'usage': {
                    'header': 'Authorization: Bearer ' + access_token,
                    'example_curl': f'curl -H "Authorization: Bearer {access_token}" http://127.0.0.1:8000/api/accounts/admin/dashboard/'
                }
            })
            
        except User.DoesNotExist:
            return Response({
                'error': 'Admin user not found. Run: python manage.py createsuperuser'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Token generation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_all_users_with_tokens(request):
    """Debug endpoint - Get all users with their tokens"""
    try:
        users = User.objects.all()
        users_data = []
        
        for user in users:
            # Generate token for each user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            users_data.append({
                'email': user.email,
                'role': user.role,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'access_token': access_token,
                'header': f'Authorization: Bearer {access_token}'
            })
        
        return Response({
            'success': True,
            'total_users': len(users_data),
            'users': users_data,
            'note': 'Use these tokens for API testing'
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
