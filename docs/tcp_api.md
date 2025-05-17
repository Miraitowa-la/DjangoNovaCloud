# NovaCloud 物联网平台 - TCP 设备接入指南

## 概述

NovaCloud 物联网平台提供基于原生 TCP 协议的设备接入服务，使物联网设备能够通过简单、高效的方式与云平台进行双向通信。相比MQTT协议，TCP协议具有更低的开销，适合资源受限的设备或需要更简洁实现的场景。

## 连接信息

* **服务器地址**: 默认为 127.0.0.1（本地开发）或 公网IP/域名（生产环境）
* **端口**: 9000（可在平台配置中修改）
* **协议**: TCP
* **帧格式**: 消息以换行符('\n')分隔的JSON字符串

## 认证流程

所有设备必须先完成认证才能上报数据或接收命令：

1. **建立连接**：设备连接到TCP服务器
2. **发送认证消息**：设备发送包含以下字段的JSON认证消息：
   ```json
   {
     "device_id": "DEV-123456",  // 平台分配的设备ID
     "device_key": "your_device_key",  // 平台分配的设备密钥
     "timestamp": 1651234567  // Unix时间戳（秒）
   }
   ```
3. **验证结果**：服务器验证设备凭据并返回响应：
   - 认证成功:
     ```json
     {
       "type": "auth_success",
       "message": "认证成功",
       "timestamp": 1651234567,
       "device_id": "DEV-123456"
     }
     ```
   - 认证失败:
     ```json
     {
       "type": "error",
       "error_code": "auth_failed",
       "message": "设备ID或密钥无效",
       "timestamp": 1651234567
     }
     ```

## 消息格式

所有消息均使用 JSON 格式，每条消息以换行符('\n')结束。每条消息必须包含`type`字段以指明消息类型。

### 设备数据上报

设备通过TCP连接发送传感器数据：

```json
{
  "type": "data",
  "device_id": "DEV-123456",
  "timestamp": 1651234567,
  "temperature": 25.5,  // 传感器值，键名应与平台配置的 value_key 一致
  "humidity": 60.0,
  "light": 500
}
```

服务器响应：

```json
{
  "type": "data_received",
  "timestamp": 1651234567,
  "device_id": "DEV-123456"
}
```

### 设备状态上报

设备应定期上报其运行状态：

```json
{
  "type": "status",
  "device_id": "DEV-123456",
  "status": "online",  // 状态：online, offline, error 等
  "timestamp": 1651234567
}
```

服务器响应：

```json
{
  "type": "status_updated",
  "status": "online",
  "timestamp": 1651234567,
  "device_id": "DEV-123456"
}
```

### 命令响应

设备收到命令后应发送响应：

```json
{
  "type": "response",
  "response": "pong",
  "command": "ping",
  "timestamp": 1651234567,
  "device_id": "DEV-123456",
  "success": true,
  "data": {
    "field1": "value1",
    "field2": 123
  }
}
```

### 错误消息

若处理消息过程中出现错误，服务器会发送错误消息：

```json
{
  "type": "error",
  "error_code": "invalid_format",
  "message": "无效的消息格式",
  "timestamp": 1651234567
}
```

## 错误处理与重连机制

1. **连接断开处理**：
   - 当TCP连接断开时，设备应实施指数退避重连策略
   - 初始等待时间：2秒
   - 最大等待时间：5分钟
   - 退避系数：2（每次重试时间翻倍）

2. **错误码一览**：
   - `auth_failed`: 认证失败，检查设备ID和密钥
   - `invalid_json`: 无效的JSON格式
   - `missing_field`: 缺少必要字段
   - `internal_error`: 服务器内部错误
   - `data_store_failed`: 数据存储失败

3. **缓冲区限制**：
   - 默认消息大小限制为128KB
   - 超出限制会导致连接被服务器主动关闭

## 帧格式与流控制

TCP是面向流的协议，NovaCloud平台采用以下机制来分隔消息：

1. **帧分隔**：每条JSON消息以换行符('\n')结束
2. **缓冲区处理**：
   - 设备和服务器都应实现缓冲区累积机制
   - 接收数据添加到缓冲区
   - 检测换行符分隔完整消息
   - 处理完整消息并清除已处理的缓冲区数据

3. **超大消息处理**：
   - 超过最大消息大小限制的消息会被拒绝
   - 建议将大数据分成多条较小的消息发送

## 标准命令格式

服务器向设备发送的命令格式：

### ping 命令

测试设备连接性：

```json
{
  "type": "command",
  "command": "ping",
  "timestamp": 1651234567,
  "device_id": "DEV-123456"
}
```

### reboot 命令

重启设备：

```json
{
  "type": "command",
  "command": "reboot",
  "timestamp": 1651234567,
  "device_id": "DEV-123456"
}
```

### 执行器控制命令

控制设备执行器：

```json
{
  "type": "command",
  "command": "set_actuator",
  "timestamp": 1651234567,
  "device_id": "DEV-123456",
  "params": {
    "actuator_key": "值"  // 键名应与平台配置的command_key一致
  }
}
```

## 示例代码

### Python 示例

```python
#!/usr/bin/env python3
import socket
import json
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
    """TCP设备客户端"""
    
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
        self.delimiter = b'\n'  # 消息分隔符
    
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
            
            # 发送消息，确保以换行符结尾
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
                messages = self.receive_data(0.1)
                for message in messages:
                    self.process_message(message)
                
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
    
    def process_message(self, message):
        """处理服务器消息"""
        message_type = message.get('type')
        
        if message_type == 'error':
            logger.error(f"收到错误消息: {message.get('message')} (代码: {message.get('error_code')})")
        elif message_type == 'data_received':
            logger.info("服务器确认已接收数据")
        elif message_type == 'status_updated':
            logger.info(f"服务器确认设备状态已更新为: {message.get('status')}")
        elif message_type == 'command':
            self.handle_command(message)
        else:
            logger.debug(f"收到其他类型消息: {message}")
    
    def handle_command(self, message):
        """处理服务器命令"""
        command = message.get('command')
        logger.info(f"收到命令: {command}")
        
        if command == "ping":
            # 响应ping命令
            response = {
                "type": "response",
                "response": "pong",
                "command": "ping",
                "timestamp": int(time.time()),
                "device_id": self.device_id,
                "success": True
            }
            self.send_message(response)


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='NovaCloud TCP客户端示例')
    
    parser.add_argument('--device_id', required=True, help='设备ID')
    parser.add_argument('--device_key', required=True, help='设备密钥')
    parser.add_argument('--host', default='127.0.0.1', help='TCP服务器地址')
    parser.add_argument('--port', type=int, default=9000, help='TCP服务器端口')
    parser.add_argument('--interval', type=int, default=60, help='数据发送间隔（秒）')
    
    args = parser.parse_args()
    
    # 创建并运行客户端
    client = TCPDeviceClient(
        device_id=args.device_id,
        device_key=args.device_key,
        host=args.host,
        port=args.port
    )
    client.run(args.interval)
```

### 使用方法

```bash
python tcp_client.py --device_id=DEV-123456 --device_key=your_device_key --interval=30
```

## 与MQTT协议的对比

| 特性 | TCP | MQTT |
|-----|-----|------|
| 协议复杂度 | 低 | 中 |
| 消息开销 | 小 | 较小 |
| 服务质量保证 | 无内置QoS | 支持3级QoS |
| 主题订阅机制 | 无 | 有 |
| 实现难度 | 简单 | 中等 |
| 适用设备 | 资源极度受限设备 | 一般IoT设备 |
| 内置断线重连 | 需自行实现 | 内置支持 |

## 最佳实践

1. **连接管理**
   - 实施指数退避的重连策略
   - 定期发送心跳/状态消息
   - 正确处理连接异常

2. **消息格式**
   - 始终包含`type`字段指明消息类型
   - 包含设备ID以进行交叉验证
   - 包含时间戳确保消息时序

3. **安全性**
   - 在生产环境中使用TLS加密TCP连接
   - 不要在代码中硬编码设备凭据
   - 验证所有接收到的消息

4. **资源管理**
   - 合理设置超时时间
   - 控制缓冲区大小
   - 考虑网络不稳定情况下的重传策略

5. **错误处理**
   - 优雅处理认证失败
   - 对网络错误进行分类并采取相应措施
   - 记录并定期上报异常情况 