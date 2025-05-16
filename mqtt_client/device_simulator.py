#!/usr/bin/env python3
"""
NovaCloud设备模拟器 - 用于测试MQTT通信

该脚本模拟一个IoT设备，通过MQTT协议与NovaCloud平台通信。
设备会定期上报传感器数据，并响应平台发送的命令。

使用方法:
    python device_simulator.py --device_id=DEV-XXXXXX --device_key=your_device_key

参数:
    --device_id: 设备ID，必须和NovaCloud平台上的设备ID匹配
    --device_key: 设备密钥，必须和NovaCloud平台上的设备密钥匹配
    --broker: MQTT Broker地址，默认为broker.emqx.io
    --port: MQTT Broker端口，默认为1883
    --use_tls: 是否使用TLS，默认为False
"""

import argparse
import json
import logging
import random
import ssl
import time
import uuid
from datetime import datetime

import paho.mqtt.client as mqtt

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("device_simulator")


class DeviceSimulator:
    """模拟IoT设备类"""
    
    def __init__(self, device_id, device_key, broker="broker.emqx.io", port=1883, use_tls=False):
        """初始化设备模拟器"""
        self.device_id = device_id
        self.device_key = device_key
        self.broker = broker
        self.port = port
        self.use_tls = use_tls
        
        # 设备状态
        self.status = "online"
        self.running = True
        
        # 主题配置
        self.topic_prefix = "novacloud/"
        self.data_topic = f"{self.topic_prefix}devices/{self.device_id}/data"
        self.status_topic = f"{self.topic_prefix}devices/{self.device_id}/status"
        self.command_topic = f"{self.topic_prefix}devices/{self.device_id}/command"
        self.config_topic = f"{self.topic_prefix}devices/{self.device_id}/config"
        
        # 创建MQTT客户端
        self.client = mqtt.Client(client_id=f"device_{self.device_id}_{uuid.uuid4().hex[:8]}")
        self.client.username_pw_set(self.device_id, self.device_key)
        
        # 设置回调函数
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        
        # TLS设置
        if self.use_tls:
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        
        # 连接状态
        self.connected = False
    
    def connect(self):
        """连接到MQTT Broker"""
        try:
            logger.info(f"正在连接到MQTT Broker {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, 60)
            
            # 启动网络循环
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"连接MQTT Broker失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开与MQTT Broker的连接"""
        try:
            # 发布离线状态
            self.publish_status("offline")
            
            # 断开连接
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("已断开与MQTT Broker的连接")
        except Exception as e:
            logger.error(f"断开连接时出错: {str(e)}")
    
    def on_connect(self, client, userdata, flags, rc):
        """连接回调函数"""
        if rc == 0:
            self.connected = True
            logger.info("已连接到MQTT Broker")
            
            # 订阅命令和配置主题
            logger.info(f"订阅主题: {self.command_topic}")
            self.client.subscribe(self.command_topic)
            
            logger.info(f"订阅主题: {self.config_topic}")
            self.client.subscribe(self.config_topic)
            
            # 发布在线状态
            self.publish_status("online")
        else:
            self.connected = False
            logger.error(f"连接失败，返回码: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """断开连接回调函数"""
        self.connected = False
        if rc != 0:
            logger.warning(f"意外断开连接，返回码: {rc}")
        else:
            logger.info("已断开连接")
    
    def on_message(self, client, userdata, msg):
        """消息接收回调函数"""
        try:
            logger.info(f"收到消息: 主题={msg.topic}, 内容={msg.payload.decode()}")
            
            # 处理命令
            if msg.topic == self.command_topic:
                self.handle_command(msg.payload)
            # 处理配置
            elif msg.topic == self.config_topic:
                self.handle_config(msg.payload)
        
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
    
    def on_publish(self, client, userdata, mid):
        """发布消息回调函数"""
        logger.debug(f"消息已发布，消息ID: {mid}")
    
    def handle_command(self, payload):
        """处理命令消息"""
        try:
            command_data = json.loads(payload)
            
            # 检查命令字段
            if "command" not in command_data:
                logger.warning("收到的命令消息缺少command字段")
                return
            
            command = command_data["command"]
            logger.info(f"收到命令: {command}")
            
            # 处理ping命令
            if command == "ping":
                logger.info("接收到ping命令，发送响应...")
                response = {
                    "response": "pong",
                    "timestamp": int(time.time()),
                    "device_id": self.device_id
                }
                self.client.publish(self.data_topic, json.dumps(response))
            
            # 处理重启命令
            elif command == "reboot":
                logger.info("接收到重启命令，模拟设备重启...")
                # 发布离线状态
                self.publish_status("offline")
                
                # 等待几秒钟模拟重启过程
                time.sleep(3)
                
                # 发布在线状态
                self.publish_status("online")
                
                # 发布重启完成消息
                response = {
                    "response": "reboot_complete",
                    "timestamp": int(time.time()),
                    "device_id": self.device_id
                }
                self.client.publish(self.data_topic, json.dumps(response))
            
            # 其他命令
            else:
                logger.info(f"未知命令: {command}")
        
        except json.JSONDecodeError:
            logger.error("无效的JSON格式命令")
        except Exception as e:
            logger.error(f"处理命令时出错: {str(e)}")
    
    def handle_config(self, payload):
        """处理配置消息"""
        try:
            config_data = json.loads(payload)
            logger.info(f"收到配置: {config_data}")
            
            # TODO: 处理配置
            # 实际设备应该根据配置更新其行为
            
            # 发送配置确认
            response = {
                "response": "config_applied",
                "timestamp": int(time.time()),
                "device_id": self.device_id,
                "config": config_data
            }
            self.client.publish(self.data_topic, json.dumps(response))
        
        except json.JSONDecodeError:
            logger.error("无效的JSON格式配置")
        except Exception as e:
            logger.error(f"处理配置时出错: {str(e)}")
    
    def publish_status(self, status):
        """发布设备状态"""
        if not self.connected:
            logger.warning("未连接到MQTT Broker，无法发布状态")
            return
        
        self.status = status
        status_data = {
            "status": status,
            "timestamp": int(time.time()),
            "device_id": self.device_id
        }
        
        try:
            logger.info(f"发布状态: {status}")
            self.client.publish(self.status_topic, json.dumps(status_data))
        except Exception as e:
            logger.error(f"发布状态时出错: {str(e)}")
    
    def publish_sensor_data(self):
        """发布模拟传感器数据"""
        if not self.connected:
            logger.warning("未连接到MQTT Broker，无法发布数据")
            return
        
        # 生成随机传感器数据
        temperature = round(random.uniform(18, 30), 1)
        humidity = round(random.uniform(40, 80), 1)
        light = random.randint(100, 1000)
        
        # 创建数据包
        sensor_data = {
            "temperature": temperature,
            "humidity": humidity,
            "light": light,
            "timestamp": int(time.time()),
            "device_id": self.device_id
        }
        
        try:
            logger.info(f"发布传感器数据: {sensor_data}")
            self.client.publish(self.data_topic, json.dumps(sensor_data))
        except Exception as e:
            logger.error(f"发布传感器数据时出错: {str(e)}")
    
    def run(self):
        """运行设备模拟器"""
        if not self.connect():
            logger.error("无法连接到MQTT Broker，退出")
            return
        
        try:
            logger.info("设备模拟器已启动，按Ctrl+C停止...")
            
            while self.running:
                # 发布传感器数据
                self.publish_sensor_data()
                
                # 等待一段时间
                time.sleep(10)
        
        except KeyboardInterrupt:
            logger.info("接收到停止信号")
        finally:
            self.running = False
            self.disconnect()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="NovaCloud设备模拟器")
    parser.add_argument("--device_id", required=True, help="设备ID")
    parser.add_argument("--device_key", required=True, help="设备密钥")
    parser.add_argument("--broker", default="broker.emqx.io", help="MQTT Broker地址")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker端口")
    parser.add_argument("--use_tls", action="store_true", help="是否使用TLS")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    simulator = DeviceSimulator(
        device_id=args.device_id,
        device_key=args.device_key,
        broker=args.broker,
        port=args.port,
        use_tls=args.use_tls
    )
    
    simulator.run() 