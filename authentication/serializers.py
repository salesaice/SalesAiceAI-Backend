from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from accounts.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password],
        help_text="Enter a strong password (minimum 8 characters)",
        style={'input_type': 'password'}
    )
    # password_confirm = serializers.CharField(
    #     write_only=True,
    #     help_text="Confirm your password",
    #     style={'input_type': 'password'}
    # )
    
    class Meta:
        model = User
        fields = ['email', 'password','user_name']
        extra_kwargs = {
            'email': {'help_text': 'Enter your email address'},
            # 'first_name': {'help_text': 'Enter your first name', 'required': False},
            # 'last_name': {'help_text': 'Enter your last name', 'required': False},
            # 'phone': {'help_text': 'Enter your phone number (optional)', 'required': False},
            'user_name': {'help_text': 'Enter your user name', 'required': True},
        }
    
    # def validate(self, attrs):
    #     if attrs['password'] != attrs['password_confirm']:
    #         raise serializers.ValidationError("Passwords don't match.")
    #     return attrs
    
    def create(self, validated_data):
        # validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data,password=password)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Enter your email address")
    password = serializers.CharField(
        help_text="Enter your password",
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        required=True,
        help_text="Enter your current password",
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True, 
        validators=[validate_password],
        help_text="Enter your new password (minimum 8 characters)",
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        help_text="Confirm your new password",
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Enter your email address to receive reset link")
    
    def validate_email(self, value):
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            # Don't reveal whether user exists or not
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        validators=[validate_password],
        help_text="Enter your new password",
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        help_text="Confirm your new password",
        style={'input_type': 'password'}
    )
    token = serializers.CharField(help_text="Reset token from email")
    uidb64 = serializers.CharField(help_text="User ID from email")
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

class UserNameExistenceCheckSerializer(serializers.Serializer):
    user_name = serializers.CharField(required=False, help_text="Username to check if exists")
    

    def validate(self, attrs):
        user_name = attrs.get('user_name', None)

        user_name_exists = False

        if user_name:
            user_name_exists = User.objects.filter(user_name=user_name).exists()

        attrs['user_name_exists'] = user_name_exists
        return attrs
    
class UserEmailExistenceCheckSerializer(serializers.Serializer):
     email = serializers.EmailField(required=False, help_text="Email to check if exists")
    

     def validate(self, attrs):
        email = attrs.get('email', None)

        email_exists = False

        if email:
            email_exists = User.objects.filter(email=email).exists()

        attrs['email_exists'] = email_exists
        return attrs