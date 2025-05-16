from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MqttClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mqtt_client'
    
    def ready(self):
        """应用就绪时初始化MQTT客户端连接"""
        # 仅在主进程中初始化MQTT连接
        # Django会在自动重载时多次调用ready()，我们需要避免多次连接
        import os
        if os.environ.get('RUN_MAIN', None) != 'true':
            if getattr(settings, 'MQTT_AUTO_CONNECT', False):
                try:
                    from mqtt_client.mqtt import mqtt_client
                    connected = mqtt_client.connect()
                    if connected:
                        logger.info("MQTT客户端已自动连接")
                    else:
                        logger.warning("MQTT客户端自动连接失败")
                except Exception as e:
                    logger.error(f"初始化MQTT客户端时出错: {str(e)}")
