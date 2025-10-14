from django.urls import re_path
from . import consumers
from .simple_consumer import SimpleCallsConsumer

websocket_urlpatterns = [
    re_path(r'ws/calls/$', SimpleCallsConsumer.as_asgi()),
    re_path(r'ws/calls/full/$', consumers.CallsConsumer.as_asgi()),
]