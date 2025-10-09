from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import User, UserProfile
from .serializers import UserSerializer, UserProfileSerializer
from .permissions import IsAdmin, IsAdminOrOwner


class UserListView(generics.ListAPIView):
    """List all users (Admin only)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]  # Only admins can list all users


class UserDetailView(generics.RetrieveUpdateAPIView):
    """Get or update user details"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrOwner]  # Admin or owner can access


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


@swagger_auto_schema(
    method='get',
    responses={
        200: UserSerializer,
        401: "Unauthorized - Authentication required"
    },
    operation_description="Get current authenticated user information",
    operation_summary="Get Current User",
    tags=['User Management']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """Get current user info"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    operation_description="Change user role (Admin only)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['user_id', 'role'],
        properties={
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'role': openapi.Schema(type=openapi.TYPE_STRING, enum=['admin', 'user']),
        },
    ),
    responses={200: "Role changed successfully"}
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def change_user_role(request):
    """Change user role (Admin only)"""
    user_id = request.data.get('user_id')
    new_role = request.data.get('role')
    
    if not user_id or not new_role:
        return Response({
            'error': 'user_id and role are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if new_role not in ['admin', 'user']:
        return Response({
            'error': 'role must be either admin or user'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        user.role = new_role
        
        # Set staff status for admin role
        if new_role == 'admin':
            user.is_staff = True
        else:
            user.is_staff = False
            
        user.save()
        
        return Response({
            'message': f'User role changed to {new_role} successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='get',
    operation_description="Get all admin users",
    responses={200: UserSerializer(many=True)},
    tags=['User Management']
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_users(request):
    """Get all admin users"""
    admins = User.objects.filter(role='admin')
    serializer = UserSerializer(admins, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_description="Get all regular users",
    responses={200: UserSerializer(many=True)},
    tags=['User Management']
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def regular_users(request):
    """Get all regular users"""
    users = User.objects.filter(role='user')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    operation_description="Deactivate user account (Admin only)",
    tags=['User Management'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['user_id'],
        properties={
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    ),
    responses={200: "User deactivated successfully"}
)
@api_view(['POST'])
@permission_classes([IsAdmin])
def deactivate_user(request):
    """Deactivate user account (Admin only)"""
    user_id = request.data.get('user_id')
    
    if not user_id:
        return Response({
            'error': 'user_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent deactivating self
        if user == request.user:
            return Response({
                'error': 'You cannot deactivate your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = False
        user.save()
        
        return Response({
            'message': 'User deactivated successfully'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
