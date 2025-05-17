import json
import logging
from channels.consumer import AsyncConsumer
from django.conf import settings
from django.utils import timezone
from django.db import transaction, IntegrityError
from asgiref.sync import sync_to_async
from iot_devices.models import Device, Sensor, SensorData

logger = logging.getLogger(__name__)


class TCPDeviceConsumer(AsyncConsumer):
    """处理设备TCP连接的异步消费者"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = None
        self.device_id = None
        self.buffer = b''
        self.config = settings.TCP_SERVER_CONFIG
        self.authenticated = False
        self.delimiter = self.config.get('FRAME_DELIMITER', b'\n')
        self.max_size = self.config.get('MAX_MESSAGE_SIZE', 131072)  # 默认128KB
    
    async def tcp_connect(self, event):
        """
        处理新的TCP连接请求
        """
        logger.info(f"新的TCP连接: {self.scope['client']}")
        # 不需要显式接受连接，TCP连接已自动建立
        
    async def tcp_receive(self, event):
        """
        接收TCP数据
        """
        data = event.get('data', b'')
        
        # 将数据添加到缓冲区
        self.buffer += data
        
        # 如果缓冲区超过最大大小，则断开连接
        if len(self.buffer) > self.max_size:
            logger.warning(f"缓冲区溢出，断开连接: {self.scope['client']}")
            await self.tcp_close()
            return
        
        # 处理缓冲区中的完整消息
        while self.delimiter in self.buffer:
            pos = self.buffer.find(self.delimiter)
            frame = self.buffer[:pos]
            self.buffer = self.buffer[pos + len(self.delimiter):]
            
            # 处理接收到的帧
            await self.process_frame(frame)
    
    async def tcp_disconnect(self, event):
        """
        处理TCP连接断开
        """
        logger.info(f"TCP连接断开: {self.scope['client']}, code: {event.get('code', '')}")
        
        if self.device and self.authenticated:
            # 更新设备状态为离线
            await self.update_device_status("offline")
    
    async def tcp_close(self):
        """主动关闭TCP连接"""
        await self.send({
            "type": "tcp.close"
        })
    
    async def tcp_send(self, data):
        """发送TCP数据"""
        await self.send({
            "type": "tcp.send",
            "data": data
        })
    
    async def process_frame(self, frame):
        """
        处理单个完整的数据帧
        """
        try:
            # 尝试解析JSON数据
            message = json.loads(frame.decode('utf-8'))
            logger.debug(f"处理TCP数据: {message}")
            
            # 如果尚未认证，则尝试认证
            if not self.authenticated:
                await self.authenticate(message)
            else:
                # 已认证的消息处理
                await self.process_message(message)
        
        except json.JSONDecodeError:
            logger.error(f"无效的JSON数据: {frame}")
            await self.send_error("invalid_json", "无效的JSON格式")
        
        except Exception as e:
            logger.exception(f"处理数据帧时出错: {str(e)}")
            await self.send_error("internal_error", str(e))
    
    async def authenticate(self, message):
        """
        认证设备连接
        """
        # 检查认证消息格式
        if 'device_id' not in message or 'device_key' not in message:
            logger.warning("认证失败: 缺少device_id或device_key")
            await self.send_error("auth_failed", "缺少device_id或device_key")
            await self.tcp_close()
            return
        
        device_id = message['device_id']
        device_key = message['device_key']
        
        # 验证设备认证信息
        try:
            authenticated = await self.validate_device(device_id, device_key)
            
            if authenticated:
                self.authenticated = True
                self.device_id = device_id
                logger.info(f"设备认证成功: {device_id}")
                
                # 更新设备状态为在线
                await self.update_device_status("online")
                
                # 发送认证成功响应
                await self.send_response({
                    "type": "auth_success",
                    "message": "认证成功",
                    "timestamp": int(timezone.now().timestamp())
                })
            else:
                logger.warning(f"设备认证失败: {device_id}")
                await self.send_error("auth_failed", "设备ID或密钥无效")
                await self.tcp_close()
        
        except Exception as e:
            logger.exception(f"认证过程出错: {str(e)}")
            await self.send_error("auth_error", str(e))
            await self.tcp_close()
    
    @sync_to_async
    def validate_device(self, device_id, device_key):
        """
        验证设备ID和密钥
        """
        try:
            self.device = Device.objects.get(device_id=device_id, device_key=device_key)
            return True
        except Device.DoesNotExist:
            return False
    
    @sync_to_async
    def update_device_status(self, status):
        """
        更新设备状态
        """
        if not self.device:
            return
        
        self.device.status = status
        self.device.last_seen = timezone.now()
        self.device.save()
        logger.info(f"设备 {self.device_id} 状态已更新为: {status}")
    
    async def process_message(self, message):
        """
        处理已认证设备的消息
        """
        # 检查消息类型
        msg_type = message.get('type', 'data')
        
        if msg_type == 'data':
            # 处理数据消息
            await self.process_data_message(message)
        elif msg_type == 'status':
            # 处理状态消息
            await self.process_status_message(message)
        else:
            logger.warning(f"未知的消息类型: {msg_type}")
            await self.send_error("unknown_type", f"未知的消息类型: {msg_type}")
    
    async def process_data_message(self, message):
        """
        处理数据消息
        """
        try:
            # 确保消息包含时间戳
            if 'timestamp' not in message:
                message['timestamp'] = int(timezone.now().timestamp())
            
            # 存储传感器数据
            result = await self.store_sensor_data(message)
            
            if result:
                await self.send_response({
                    "type": "data_received",
                    "timestamp": int(timezone.now().timestamp())
                })
            else:
                await self.send_error("data_store_failed", "存储传感器数据失败")
        
        except Exception as e:
            logger.exception(f"处理数据消息时出错: {str(e)}")
            await self.send_error("data_process_error", str(e))
    
    async def process_status_message(self, message):
        """
        处理状态消息
        """
        try:
            # 检查状态字段
            if 'status' not in message:
                await self.send_error("invalid_status", "缺少status字段")
                return
            
            status = message['status']
            await self.update_device_status(status)
            
            await self.send_response({
                "type": "status_updated",
                "status": status,
                "timestamp": int(timezone.now().timestamp())
            })
        
        except Exception as e:
            logger.exception(f"处理状态消息时出错: {str(e)}")
            await self.send_error("status_process_error", str(e))
    
    @sync_to_async
    def store_sensor_data(self, data):
        """
        存储传感器数据
        """
        try:
            with transaction.atomic():
                # 更新设备状态
                self.device.status = 'online'
                self.device.last_seen = timezone.now()
                self.device.save()
                
                # 处理传感器数据
                for sensor in Sensor.objects.filter(device=self.device):
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
                
                return True
        
        except Exception as e:
            logger.exception(f"存储传感器数据时出错: {str(e)}")
            return False
    
    async def send_response(self, data):
        """
        发送响应消息
        """
        try:
            # 确保响应包含设备ID
            if 'device_id' not in data and self.device_id:
                data['device_id'] = self.device_id
            
            response_json = json.dumps(data)
            await self.tcp_send(response_json.encode('utf-8') + self.delimiter)
        except Exception as e:
            logger.exception(f"发送响应失败: {str(e)}")
    
    async def send_error(self, code, message):
        """
        发送错误消息
        """
        try:
            error_data = {
                "type": "error",
                "error_code": code,
                "message": message,
                "timestamp": int(timezone.now().timestamp())
            }
            
            if self.device_id:
                error_data['device_id'] = self.device_id
            
            error_json = json.dumps(error_data)
            await self.tcp_send(error_json.encode('utf-8') + self.delimiter)
        
        except Exception as e:
            logger.exception(f"发送错误消息失败: {str(e)}") 