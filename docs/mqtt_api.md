# NovaCloud 物联网平台 - MQTT 设备接入指南

## 概述

NovaCloud 物联网平台基于 MQTT 协议提供设备接入服务，使物联网设备能够安全、可靠地与云平台进行双向通信。设备可以上报数据、接收命令并获取配置，实现远程管理和控制。

## MQTT服务器信息

* **Broker地址**: broker.emqx.io (公共MQTT服务器)
* **端口**: 
  - 1883 (TCP, 非加密)
  - 8883 (SSL/TLS, 加密)
* **协议版本**: MQTT 3.1.1
* **服务质量(QoS)**: 建议 QoS 1 (至少一次) 用于重要消息

## 设备认证

所有设备必须经过认证才能连接到NovaCloud平台。认证过程如下：

- **客户端ID**: 可自定义，但建议格式为 `device_{device_id}_{随机字符串}`
- **用户名**: 使用平台分配的`device_id`
- **密码**: 使用平台分配的`device_key`

## 通信主题

所有通信主题均以 `novacloud/` 作为前缀，后跟具体的功能主题。

### 设备数据上报 (Uplink)

设备应通过以下主题上报传感器数据：

- **主题**: `novacloud/devices/{device_id}/data`
- **消息格式** (JSON):
  ```json
  {
    "temperature": 25.5,        // 传感器值，键名应与平台配置的 value_key 一致
    "humidity": 60.0,           
    "light": 500,               
    "timestamp": 1651234567,    // Unix时间戳（秒）
    "device_id": "DEV-123456"   // 设备ID
  }
  ```
- **QoS**: 推荐 QoS 1

### 设备状态上报

设备应定期上报其运行状态：

- **主题**: `novacloud/devices/{device_id}/status`
- **消息格式** (JSON):
  ```json
  {
    "status": "online",         // 状态：online, offline, error 等
    "timestamp": 1651234567,    // Unix时间戳（秒）
    "device_id": "DEV-123456"   // 设备ID
  }
  ```
- **QoS**: 推荐 QoS 1

### 设备命令接收 (Downlink)

设备应订阅此主题以接收来自平台的命令：

- **主题**: `novacloud/devices/{device_id}/command`
- **消息格式** (JSON):
  ```json
  {
    "command": "ping",          // 命令名称
    "timestamp": 1651234567,    // Unix时间戳（秒）
    "params": {                 // 可选的命令参数
      "param1": "value1",
      "param2": 123
    }
  }
  ```
- **QoS**: 平台使用 QoS 1 发送命令

### 命令响应

设备执行命令后，应通过数据主题发送响应：

- **主题**: `novacloud/devices/{device_id}/data`
- **消息格式** (JSON):
  ```json
  {
    "response": "pong",         // 响应名称
    "command": "ping",          // 对应的命令名称（可选）
    "timestamp": 1651234567,    // Unix时间戳（秒）
    "device_id": "DEV-123456",  // 设备ID
    "success": true,            // 命令执行结果
    "data": {                   // 响应数据（可选）
      "field1": "value1",
      "field2": 123
    }
  }
  ```

### 设备配置接收

设备应订阅此主题以接收配置更新：

- **主题**: `novacloud/devices/{device_id}/config`
- **消息格式** (JSON):
  ```json
  {
    "config_version": "1.0",    // 配置版本
    "timestamp": 1651234567,    // Unix时间戳（秒）
    "settings": {               // 配置设置
      "reporting_interval": 60,
      "sensor_precision": 2,
      "alert_threshold": 80
    }
  }
  ```

## 标准命令

### ping

用于测试设备连接性：

- **命令**:
  ```json
  {
    "command": "ping",
    "timestamp": 1651234567
  }
  ```

- **响应**:
  ```json
  {
    "response": "pong",
    "command": "ping",
    "timestamp": 1651234567,
    "device_id": "DEV-123456"
  }
  ```

### reboot

重启设备：

- **命令**:
  ```json
  {
    "command": "reboot",
    "timestamp": 1651234567
  }
  ```

- **响应**:
  ```json
  {
    "response": "reboot_complete",
    "command": "reboot",
    "timestamp": 1651234567,
    "device_id": "DEV-123456"
  }
  ```

## 执行器控制

执行器的控制通过command主题实现，格式如下：

- **命令**:
  ```json
  {
    "command": "set_actuator",
    "timestamp": 1651234567,
    "params": {
      "actuator_key": "值"  // 键名应与平台配置的command_key一致
    }
  }
  ```

- **响应**:
  ```json
  {
    "response": "actuator_set",
    "command": "set_actuator",
    "timestamp": 1651234567,
    "device_id": "DEV-123456",
    "success": true,
    "data": {
      "actuator_key": "当前状态"
    }
  }
  ```

## 连接与重连机制

1. **初始连接**: 设备启动时应尝试连接到MQTT Broker。
2. **连接成功**: 连接成功后立即发布online状态，并订阅命令和配置主题。
3. **定期状态上报**: 建议每60秒上报一次在线状态（可配置）。
4. **断线重连**: 在连接断开后，设备应实施指数退避重连策略：
   - 初始等待时间：2秒
   - 最大等待时间：5分钟
   - 退避系数：2（每次重试时间翻倍）
5. **重连后操作**: 重连成功后，设备应重新发布在线状态并重新订阅主题。

## 数据安全

1. **传输加密**: 推荐使用TLS加密（端口8883）保护数据传输。
2. **设备认证**: 使用`device_id`和`device_key`进行身份验证。
3. **消息验证**: 包含时间戳和设备ID以验证消息有效性。

## 示例代码

### Python 示例 (使用Paho-MQTT)

```python
import paho.mqtt.client as mqtt
import json
import time
import ssl
import uuid
import random

# 设备配置
device_id = "DEV-123456"
device_key = "your_device_key_here"
broker = "broker.emqx.io"
port = 8883  # 使用TLS的端口
use_tls = True

# 主题
topic_prefix = "novacloud/"
data_topic = f"{topic_prefix}devices/{device_id}/data"
status_topic = f"{topic_prefix}devices/{device_id}/status"
command_topic = f"{topic_prefix}devices/{device_id}/command"
config_topic = f"{topic_prefix}devices/{device_id}/config"

# 回调函数
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # 订阅命令和配置主题
        client.subscribe(command_topic)
        client.subscribe(config_topic)
        # 发布在线状态
        publish_status(client, "online")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()}")
    
    try:
        payload = json.loads(msg.payload.decode())
        
        # 处理命令
        if msg.topic == command_topic and "command" in payload:
            handle_command(client, payload)
        # 处理配置
        elif msg.topic == config_topic:
            handle_config(client, payload)
    except json.JSONDecodeError:
        print("Invalid JSON payload")
    except Exception as e:
        print(f"Error processing message: {str(e)}")

def handle_command(client, command_data):
    command = command_data.get("command")
    print(f"Handling command: {command}")
    
    if command == "ping":
        # 响应ping命令
        response = {
            "response": "pong",
            "command": "ping",
            "timestamp": int(time.time()),
            "device_id": device_id
        }
        client.publish(data_topic, json.dumps(response))
    elif command == "reboot":
        # 响应重启命令
        print("Rebooting device...")
        publish_status(client, "offline")
        time.sleep(2)  # 模拟重启
        publish_status(client, "online")
        response = {
            "response": "reboot_complete",
            "command": "reboot",
            "timestamp": int(time.time()),
            "device_id": device_id
        }
        client.publish(data_topic, json.dumps(response))
    elif command == "set_actuator" and "params" in command_data:
        # 处理执行器控制命令
        params = command_data["params"]
        # 在实际设备中，这里应该执行相应的硬件操作
        print(f"Setting actuator: {params}")
        response = {
            "response": "actuator_set",
            "command": "set_actuator",
            "timestamp": int(time.time()),
            "device_id": device_id,
            "success": True,
            "data": params
        }
        client.publish(data_topic, json.dumps(response))

def handle_config(client, config_data):
    print(f"Received config update: {config_data}")
    # 应用配置
    # ...
    
    # 确认配置已应用
    response = {
        "response": "config_applied",
        "timestamp": int(time.time()),
        "device_id": device_id
    }
    client.publish(data_topic, json.dumps(response))

def publish_status(client, status):
    status_data = {
        "status": status,
        "timestamp": int(time.time()),
        "device_id": device_id
    }
    client.publish(status_topic, json.dumps(status_data))

def publish_sensor_data(client):
    # 生成模拟传感器数据
    data = {
        "temperature": round(random.uniform(18, 30), 1),
        "humidity": round(random.uniform(40, 80), 1),
        "light": int(random.uniform(200, 1000)),
        "timestamp": int(time.time()),
        "device_id": device_id
    }
    client.publish(data_topic, json.dumps(data))

# 创建MQTT客户端
client_id = f"device_{device_id}_{uuid.uuid4().hex[:8]}"
client = mqtt.Client(client_id=client_id)

# 设置认证
client.username_pw_set(device_id, device_key)

# TLS设置
if use_tls:
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

# 设置回调
client.on_connect = on_connect
client.on_message = on_message

# 连接到MQTT Broker
client.connect(broker, port, 60)

# 启动网络循环
client.loop_start()

# 主循环
try:
    while True:
        publish_sensor_data(client)
        time.sleep(60)  # 每分钟发送一次数据
except KeyboardInterrupt:
    print("Exiting...")
    publish_status(client, "offline")
    client.disconnect()
    client.loop_stop()
```

## 错误处理

常见错误及处理方法：

1. **连接被拒绝**: 检查设备ID和密钥是否正确。
2. **主题格式错误**: 确认主题格式符合规范。
3. **消息格式错误**: 确保JSON格式正确，包含所有必需字段。
4. **服务器不可达**: 实施重连策略，检查网络连接。

## 限制与最佳实践

1. **消息大小**: 单条消息不应超过128KB。
2. **发送频率**: 正常情况下，设备数据更新间隔不应小于5秒。
3. **避免过度连接**: 避免频繁断开和重连，这可能被视为滥用。
4. **消息批处理**: 可以在一个消息中包含多个时间点的数据，以减少连接次数。
5. **数据验证**: 在发送前验证数据的有效性和完整性。 