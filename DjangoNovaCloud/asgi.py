"""
ASGI config for DjangoNovaCloud project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from tcp_server.routing import tcp_routes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoNovaCloud.settings')

# 获取Django ASGI应用
django_asgi_app = get_asgi_application()

# 定义ASGI应用，支持多种协议
application = ProtocolTypeRouter({
    # HTTP请求由Django处理
    "http": django_asgi_app,
})
