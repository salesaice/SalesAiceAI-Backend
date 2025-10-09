from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .custom_schema_generator import CustomSchemaGenerator

# API Documentation with JWT Bearer Authentication
schema_view = get_schema_view(
    openapi.Info(
        title="Voice AI Backend API",
        default_version='v1',
        description="Complete Voice AI Backend - 6 Core Modules: Dashboard, Authentication, User Management, Subscriptions, AI Agents, Calls\n\n**Authentication:** This API uses JWT Bearer token authentication. Get your token from `/api/auth/admin-token/` or `/api/auth/quick-token/` endpoints.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="admin@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
    generator_class=CustomSchemaGenerator
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API URLs
    path('api/auth/', include('authentication.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/calls/', include('calls.urls')),
    path('api/agents/', include('agents.urls')),
    
    # Allauth URLs
    path('accounts/', include('allauth.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
