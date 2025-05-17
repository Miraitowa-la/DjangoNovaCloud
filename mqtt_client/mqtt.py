import json
import logging
import uuid
import paho.mqtt.client as mqtt
from django.conf import settings
from django.utils import timezone
from django.db import transaction

# 设置日志
logger = logging.getLogger(__name__)

# 导入设备模型
from iot_devices.models import Device, Sensor, SensorData


class MQTTClient:
    """NovaCloud MQTT客户端类，管理与MQTT Broker的连接和消息处理"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """单例模式获取MQTT客户端实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化MQTT客户端"""
        if MQTTClient._instance is not None:
            raise Exception("MQTTClient是单例类，请使用get_instance()方法获取实例")
        
        # 从settings获取MQTT配置
        self.config = settings.MQTT_CONFIG
        
        # 生成唯一的客户端ID
        client_id = f"{self.config['CLIENT_ID_PREFIX']}{uuid.uuid4().hex[:8]}"
        
        # 创建MQTT客户端实例
        self.client = mqtt.Client(client_id=client_id, clean_session=self.config['CLEAN_SESSION'], 
                                 protocol=mqtt.MQTTv311, transport="tcp")
        
        # 设置认证信息（如果需要）
        # self.client.username_pw_set("用户名", "密码")
        
        # 设置回调函数
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        
        # TLS/SSL设置
        if self.config.get('USE_TLS', False):
            self.client.tls_set()  # 可以根据需要配置CA证书等
            port = self.config.get('BROKER_PORT_TLS', 8883)
        else:
            port = self.config.get('BROKER_PORT', 1883)
        
        # 连接参数
        self.host = self.config.get('BROKER_HOST', 'localhost')
        self.port = port
        self.keepalive = self.config.get('KEEPALIVE', 60)
        
        # 连接状态和主题前缀
        self.connected = False
        self.topic_prefix = self.config.get('TOPIC_PREFIX', 'novacloud/')
    
    def connect(self):
        """连接到MQTT Broker"""
        try:
            logger.info(f"正在连接到MQTT Broker {self.host}:{self.port}")
            self.client.connect(self.host, self.port, self.keepalive)
            
            # 启动后台线程
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT连接失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开与MQTT Broker的连接"""
        if self.connected:
            logger.info("正在断开MQTT连接")
            self.client.loop_stop()
            self.client.disconnect()
    
    def on_connect(self, client, userdata, flags, rc):
        """连接回调函数"""
        if rc == 0:
            self.connected = True
            logger.info("成功连接到MQTT Broker")
            
            # 订阅所有设备的数据主题
            # 使用通配符订阅所有设备
            all_devices_data_topic = f"{self.topic_prefix}devices/+/data"
            all_devices_status_topic = f"{self.topic_prefix}devices/+/status"
            
            logger.info(f"订阅主题: {all_devices_data_topic}")
            self.client.subscribe(all_devices_data_topic, qos=self.config.get('QOS', 1))
            
            logger.info(f"订阅主题: {all_devices_status_topic}")
            self.client.subscribe(all_devices_status_topic, qos=self.config.get('QOS', 1))
        else:
            self.connected = False
            logger.error(f"MQTT连接失败，返回码: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """断开连接回调函数"""
        self.connected = False
        if rc != 0:
            logger.warning(f"意外断开MQTT连接，返回码: {rc}")
        else:
            logger.info("已断开MQTT连接")
    
    def on_message(self, client, userdata, msg):
        """消息接收回调函数"""
        try:
            logger.debug(f"收到MQTT消息: 主题={msg.topic}, 内容={msg.payload.decode()}")
            
            # 解析主题
            topic_parts = msg.topic.split('/')
            
            # 验证主题格式
            if len(topic_parts) < 4:
                logger.warning(f"无效的主题格式: {msg.topic}")
                return
            
            # 确保主题前缀正确
            if not msg.topic.startswith(self.topic_prefix):
                logger.warning(f"未知主题前缀: {msg.topic}")
                return
            
            # 提取设备ID和消息类型
            device_id = topic_parts[2]
            message_type = topic_parts[3]  # data 或 status
            
            # 根据消息类型处理
            if message_type == "data":
                self._handle_device_data(device_id, msg.payload)
            elif message_type == "status":
                self._handle_device_status(device_id, msg.payload)
            else:
                logger.warning(f"未知的消息类型: {message_type}")
        
        except Exception as e:
            logger.error(f"处理MQTT消息时出错: {str(e)}")
    
    def on_publish(self, client, userdata, mid):
        """发布消息回调函数"""
        logger.debug(f"消息已发布，消息ID: {mid}")
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        """订阅主题回调函数"""
        logger.debug(f"已订阅主题，消息ID: {mid}, QoS: {granted_qos}")
    
    def _handle_device_data(self, device_id, payload):
        """处理设备数据消息"""
        try:
            # 解析JSON数据
            data = json.loads(payload)
            logger.info(f"设备 {device_id} 数据: {data}")
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                try:
                    # 查找设备
                    device = Device.objects.get(device_id=device_id)
                    
                    # 更新设备状态
                    device.status = 'online'
                    device.last_seen = timezone.now()
                    device.save()
                    
                    # 处理传感器数据
                    for sensor in Sensor.objects.filter(device=device):
                        if sensor.value_key in data:
                            sensor_value = data[sensor.value_key]
                            logger.info(f"传感器 {sensor.name} 数据: {sensor_value} {sensor.unit}")
                            
                            # 根据数据类型保存到对应字段
                            sensor_data = SensorData(sensor=sensor)
                            
                            if isinstance(sensor_value, (int, float)):
                                sensor_data.value_float = float(sensor_value)
                            elif isinstance(sensor_value, bool):
                                sensor_data.value_boolean = sensor_value
                            else:
                                sensor_data.value_string = str(sensor_value)
                            
                            # 保存数据
                            sensor_data.save()
                            logger.debug(f"保存传感器数据: {sensor_data}")
                
                except Device.DoesNotExist:
                    logger.warning(f"未知设备ID: {device_id}")
        
        except json.JSONDecodeError:
            logger.error(f"无效的JSON数据: {payload}")
        except Exception as e:
            logger.error(f"处理设备数据时出错: {str(e)}")
    
    def _handle_device_status(self, device_id, payload):
        """处理设备状态消息"""
        try:
            # 解析JSON状态
            status_data = json.loads(payload)
            logger.info(f"设备 {device_id} 状态: {status_data}")
            
            # 检查状态字段
            if 'status' not in status_data:
                logger.warning(f"状态消息缺少status字段: {payload}")
                return
            
            status = status_data['status']
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                try:
                    # 查找设备
                    device = Device.objects.get(device_id=device_id)
                    
                    # 更新设备状态
                    device.status = status
                    device.last_seen = timezone.now()
                    device.save()
                    
                    logger.info(f"设备 {device_id} 状态已更新为: {status}")
                
                except Device.DoesNotExist:
                    logger.warning(f"未知设备ID: {device_id}")
        
        except json.JSONDecodeError:
            logger.error(f"无效的JSON数据: {payload}")
        except Exception as e:
            logger.error(f"处理设备状态时出错: {str(e)}")
    
    def publish_command(self, device_id, command, qos=None):
        """向设备发布命令"""
        if not self.connected:
            logger.error("MQTT客户端未连接")
            return False
        
        try:
            # 构建命令主题
            command_topic_template = self.config.get('DEVICE_COMMAND_TOPIC', 'devices/{device_id}/command')
            command_topic = f"{self.topic_prefix}{command_topic_template.format(device_id=device_id)}"
            
            # 确保命令是JSON格式
            if not isinstance(command, str):
                command = json.dumps(command)
            
            # 设置QoS
            if qos is None:
                qos = self.config.get('QOS', 1)
            
            # 发布命令
            result = self.client.publish(command_topic, command, qos=qos)
            
            # 检查发布结果
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"已向设备 {device_id} 发送命令: {command}")
                return True
            else:
                logger.error(f"向设备 {device_id} 发送命令失败，错误码: {result.rc}")
                return False
        
        except Exception as e:
            logger.error(f"发布命令时出错: {str(e)}")
            return False
    
    def publish_config(self, device_id, config, qos=None):
        """向设备发布配置信息"""
        if not self.connected:
            logger.error("MQTT客户端未连接")
            return False
        
        try:
            # 构建配置主题
            config_topic_template = self.config.get('DEVICE_CONFIG_TOPIC', 'devices/{device_id}/config')
            config_topic = f"{self.topic_prefix}{config_topic_template.format(device_id=device_id)}"
            
            # 确保配置是JSON格式
            if not isinstance(config, str):
                config = json.dumps(config)
            
            # 设置QoS
            if qos is None:
                qos = self.config.get('QOS', 1)
            
            # 发布配置
            result = self.client.publish(config_topic, config, qos=qos)
            
            # 检查发布结果
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"已向设备 {device_id} 发送配置: {config}")
                return True
            else:
                logger.error(f"向设备 {device_id} 发送配置失败，错误码: {result.rc}")
                return False
        
        except Exception as e:
            logger.error(f"发布配置时出错: {str(e)}")
            return False


# 导出单例实例
mqtt_client = MQTTClient.get_instance() 