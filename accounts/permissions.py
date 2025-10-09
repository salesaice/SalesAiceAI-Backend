from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Permission class for admin users only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class IsAgent(BasePermission):
    """Permission class for agent users only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'agent'
        )


class IsAdminOrOwner(BasePermission):
    """Permission class for admin users or object owner"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.role == 'admin':
            return True
        
        # User can only access their own objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For User objects
        if hasattr(obj, 'email'):
            return obj == request.user
        
        return False


class IsOwnerOrReadOnly(BasePermission):
    """Permission class for owner to edit, others read-only"""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions only to owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user
