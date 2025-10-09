from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from accounts.models import User
from accounts.serializers import UserSerializer
from .serializers import (
    RegisterSerializer, LoginSerializer, ChangePasswordSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer, UserEmailExistenceCheckSerializer, UserNameExistenceCheckSerializer
)


def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@swagger_auto_schema(
    method='post',
    request_body=RegisterSerializer,
    responses={
        201: openapi.Response(
            description="User registered successfully",
            examples={
                "application/json": {
                    "message": "User registered successfully",
                    "user": {
                        "id": 1,
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "role": "user"
                    },
                    "tokens": {
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                    }
                }
            }
        ),
        400: "Bad request - validation errors"
    },
    operation_description="Register a new user account",
    operation_summary="User Registration",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    """User registration"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        
        # Send verification email (optional)
        # send_verification_email(user)
        
        return Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=LoginSerializer,
    responses={
        200: openapi.Response(
            description="Login successful",
            examples={
                "application/json": {
                    "message": "Login successful",
                    "user": {
                        "id": 1,
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "role": "user"
                    },
                    "tokens": {
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                    }
                }
            }
        ),
        400: "Bad request - Invalid credentials"
    },
    operation_description="Login with email and password to get JWT tokens",
    operation_summary="User Login",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """User login"""
    serializer = LoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        login(request, user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token to blacklist')
        }
    ),
    responses={
        200: "Logout successful",
        400: "Invalid token",
        401: "Unauthorized - Invalid or missing JWT token"
    },
    operation_description="Logout user and blacklist refresh token. Requires JWT Bearer token authentication.",
    operation_summary="User Logout",
    tags=['Authentication'],
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """User logout"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        logout(request)
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=ChangePasswordSerializer,
    responses={
        200: "Password changed successfully",
        400: "Bad request - Invalid old password or validation errors"
    },
    operation_description="Change user password with old password verification",
    operation_summary="Change Password",
    tags=['Authentication']
)
@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """Change user password"""
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'error': 'Invalid old password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=PasswordResetSerializer,
    responses={
        200: "Password reset email sent (if account exists)",
        400: "Bad request - Invalid email format"
    },
    operation_description="Request password reset link via email",
    operation_summary="Password Reset Request",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_view(request):
    """Request password reset"""
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset URL
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            
            # Send email
            subject = 'Password Reset Request'
            message = f'Click the link to reset your password: {reset_url}'
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
        except User.DoesNotExist:
            pass  # Don't reveal whether user exists
        
        return Response({
            'message': 'If an account with this email exists, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=PasswordResetConfirmSerializer,
    responses={
        200: "Password reset successful",
        400: "Invalid token or validation errors"
    },
    operation_description="Confirm password reset with token from email",
    operation_summary="Password Reset Confirm",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm_view(request):
    """Confirm password reset"""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uidb64']))
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, serializer.validated_data['token']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                
                return Response({
                    'message': 'Password reset successful'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid token'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@swagger_auto_schema(
    method='post',
    request_body=UserEmailExistenceCheckSerializer,
    responses={
        200: openapi.Response(
            description="User Email existence check results",
            examples={
                "application/json": {
                    "email_exists": True,
                }
            }
        ),
        400: "Bad request - validation errors"
    },
    operation_description="Check if email or username already exists in the system",
    operation_summary="Check User Existence",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_user_Email_exists_view(request):
    serializer = UserEmailExistenceCheckSerializer(data=request.data)
    if serializer.is_valid():
        # validation ne email_exists and user_name_exists attrs add kar diye hain
        return Response({
            'email_exists': serializer.validated_data.get('email_exists', False),
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='post',
    request_body=UserNameExistenceCheckSerializer,
    responses={
        200: openapi.Response(
            description="User Name existence check results",
            examples={
                "application/json": {
                    "user_name_exists": True
                }
            }
        ),
        400: "Bad request - validation errors"
    },
    operation_description="Check i username already exists in the system",
    operation_summary="Check User name Existence",
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_user_name_exists_view(request):
    serializer = UserNameExistenceCheckSerializer(data=request.data)
    if serializer.is_valid():
        # validation ne email_exists and user_name_exists attrs add kar diye hain
        return Response({
            'user_name_exists': serializer.validated_data.get('user_name_exists', False),
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
