#!/usr/bin/env python3
"""
NovaCloud TCP客户端示例 - 用于测试TCP通信

该脚本模拟一个IoT设备，通过TCP协议与NovaCloud平台通信。
设备会首先发送认证信息，然后定期上报传感器数据。

使用方法:
    python tcp_client_example.py --device_id=DEV-XXXXXX --device_key=your_device_key

参数:
    --device_id: 设备ID，必须和NovaCloud平台上的设备ID匹配
    --device_key: 设备密钥，必须和NovaCloud平台上的设备密钥匹配
    --host: TCP服务器地址，默认为127.0.0.1
    --port: TCP服务器端口，默认为9000
"""

import argparse
import json
import socket
import time
import random
import logging
import sys
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tcp_client")


class TCPDeviceClient:
    """TCP设备客户端模拟类"""
    
    def __init__(self, device_id, device_key, host="127.0.0.1", port=9000):
        """初始化TCP设备客户端"""
        self.device_id = device_id
        self.device_key = device_key
        self.host = host
        self.port = port
        
        # TCP套接字
        self.socket = None
        
        # 设备状态
        self.connected = False
        self.authenticated = False
        self.running = True
        
        # 读取缓冲区
        self.buffer = b''
        self.delimiter = b'\n'  # 消息分隔符，与服务器设置一致
    
    def connect(self):
        """连接到TCP服务器"""
        try:
            logger.info(f"正在连接到TCP服务器 {self.host}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info("已成功连接到TCP服务器")
            return True
        except Exception as e:
            logger.error(f"连接TCP服务器失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开与TCP服务器的连接"""
        if self.socket:
            try:
                # 发送离线状态
                self.send_status("offline")
                
                # 关闭套接字
                self.socket.close()
                self.connected = False
                self.authenticated = False
                logger.info("已断开与TCP服务器的连接")
            except Exception as e:
                logger.error(f"断开连接时出错: {str(e)}")
    
    def authenticate(self):
        """向服务器发送认证信息"""
        if not self.connected:
            logger.error("未连接到服务器，无法进行认证")
            return False
        
        try:
            # 构造认证消息
            auth_message = {
                "device_id": self.device_id,
                "device_key": self.device_key,
                "timestamp": int(time.time())
            }
            
            # 发送认证消息
            self.send_message(auth_message)
            logger.info(f"已发送认证请求: {self.device_id}")
            
            # 等待认证响应
            response = self.wait_for_response(5)
            
            if response and response.get('type') == 'auth_success':
                self.authenticated = True
                logger.info("认证成功")
                return True
            else:
                logger.error(f"认证失败: {response.get('message', '未知错误')}")
                return False
        
        except Exception as e:
            logger.error(f"认证过程出错: {str(e)}")
            return False
    
    def send_message(self, message):
        """发送消息到服务器"""
        if not self.connected:
            logger.error("未连接到服务器，无法发送消息")
            return False
        
        try:
            # 将消息转换为JSON
            message_json = json.dumps(message)
            
            # 发送消息
            self.socket.sendall((message_json + '\n').encode('utf-8'))
            logger.debug(f"已发送消息: {message}")
            return True
        
        except Exception as e:
            logger.error(f"发送消息时出错: {str(e)}")
            self.connected = False
            return False
    
    def receive_data(self, timeout=1):
        """从服务器接收数据并处理完整消息"""
        if not self.connected:
            return []
        
        messages = []
        
        try:
            # 设置接收超时
            self.socket.settimeout(timeout)
            
            # 接收数据
            data = self.socket.recv(1024)
            
            if not data:
                logger.warning("接收到空数据，服务器可能已关闭连接")
                self.connected = False
                return messages
            
            # 添加到缓冲区
            self.buffer += data
            
            # 处理完整消息
            while self.delimiter in self.buffer:
                pos = self.buffer.find(self.delimiter)
                frame = self.buffer[:pos]
                self.buffer = self.buffer[pos + len(self.delimiter):]
                
                try:
                    # 解析消息
                    message = json.loads(frame.decode('utf-8'))
                    messages.append(message)
                    logger.debug(f"收到消息: {message}")
                except json.JSONDecodeError:
                    logger.error(f"无效的JSON消息: {frame}")
            
            return messages
        
        except socket.timeout:
            # 超时不是错误
            return messages
        except Exception as e:
            logger.error(f"接收数据时出错: {str(e)}")
            self.connected = False
            return messages
    
    def wait_for_response(self, timeout=5):
        """等待特定类型的响应"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            messages = self.receive_data(0.5)
            
            for message in messages:
                return message
            
            time.sleep(0.1)
        
        logger.warning(f"等待响应超时 ({timeout}秒)")
        return None
    
    def send_sensor_data(self):
        """发送模拟传感器数据"""
        if not self.connected or not self.authenticated:
            logger.warning("未连接或未认证，无法发送传感器数据")
            return False
        
        try:
            # 生成随机传感器数据
            temperature = round(random.uniform(18, 30), 1)
            humidity = round(random.uniform(40, 80), 1)
            light = int(random.uniform(200, 1000))
            
            # 构造数据消息
            data_message = {
                "type": "data",
                "device_id": self.device_id,
                "timestamp": int(time.time()),
                "temperature": temperature,
                "humidity": humidity,
                "light": light
            }
            
            # 发送数据
            result = self.send_message(data_message)
            
            if result:
                logger.info(f"已发送传感器数据: 温度={temperature}°C, 湿度={humidity}%, 光照={light}")
            
            return result
        
        except Exception as e:
            logger.error(f"发送传感器数据时出错: {str(e)}")
            return False
    
    def send_status(self, status):
        """发送设备状态"""
        if not self.connected:
            logger.warning("未连接，无法发送状态")
            return False
        
        try:
            # 构造状态消息
            status_message = {
                "type": "status",
                "device_id": self.device_id,
                "timestamp": int(time.time()),
                "status": status
            }
            
            # 发送状态
            result = self.send_message(status_message)
            
            if result:
                logger.info(f"已发送设备状态: {status}")
            
            return result
        
        except Exception as e:
            logger.error(f"发送设备状态时出错: {str(e)}")
            return False
    
    def process_responses(self):
        """处理服务器响应"""
        messages = self.receive_data(0.1)
        
        for message in messages:
            message_type = message.get('type')
            
            if message_type == 'error':
                logger.error(f"收到错误消息: {message.get('message')} (代码: {message.get('error_code')})")
            elif message_type == 'data_received':
                logger.info("服务器确认已接收数据")
            elif message_type == 'status_updated':
                logger.info(f"服务器确认设备状态已更新为: {message.get('status')}")
            else:
                logger.debug(f"收到其他类型消息: {message}")
    
    def run(self, data_interval=60):
        """运行TCP客户端"""
        try:
            # 连接服务器
            if not self.connect():
                return
            
            # 认证
            if not self.authenticate():
                self.disconnect()
                return
            
            # 发送在线状态
            self.send_status("online")
            
            # 主循环
            last_data_time = 0
            while self.running and self.connected:
                # 处理服务器响应
                self.process_responses()
                
                # 定期发送传感器数据
                current_time = time.time()
                if current_time - last_data_time >= data_interval:
                    self.send_sensor_data()
                    last_data_time = current_time
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("接收到终止信号，准备退出...")
        finally:
            # 断开连接
            self.disconnect()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='NovaCloud TCP客户端示例')
    
    parser.add_argument('--device_id', required=True, help='设备ID')
    parser.add_argument('--device_key', required=True, help='设备密钥')
    parser.add_argument('--host', default='127.0.0.1', help='TCP服务器地址')
    parser.add_argument('--port', type=int, default=9000, help='TCP服务器端口')
    parser.add_argument('--interval', type=int, default=5, help='数据发送间隔（秒）')
    
    return parser.parse_args()


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 创建TCP客户端
    client = TCPDeviceClient(
        device_id=args.device_id,
        device_key=args.device_key,
        host=args.host,
        port=args.port
    )
    
    # 运行客户端
    try:
        client.run(args.interval)
    except Exception as e:
        logger.critical(f"运行TCP客户端时发生严重错误: {str(e)}")
        sys.exit(1) 