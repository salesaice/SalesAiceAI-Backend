"""
WSGI config for SalesAiceAI project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments (if not using ASGI/WebSockets).

NOTE: Currently using ASGI (core/asgi.py) for WebSocket support.
This file is kept for compatibility/backup purposes.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# ============================================================================
# DJANGO SETTINGS CONFIGURATION
# ============================================================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# ============================================================================
# CREATE WSGI APPLICATION
# ============================================================================
# Note: This is the traditional WSGI application.
# For WebSocket support, we use ASGI (see core/asgi.py)
application = get_wsgi_application()
