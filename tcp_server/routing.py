from django.urls import path
from channels.routing import ChannelNameRouter, ProtocolTypeRouter
from .consumers import TCPDeviceConsumer

# 定义TCP接口端口
# 注意：在新版的Channels中，需要单独使用监听命令启动TCP端口
# 在ASGI配置中只定义HTTP部分
tcp_routes = {} 