from rest_framework import serializers
from .models import User, UserProfile


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 
                 'phone', 'avatar', 'role', 'is_active', 'is_verified', 'date_joined']
        read_only_fields = ['id', 'is_active', 'is_verified', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['user', 'bio', 'location', 'birth_date', 'website', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
