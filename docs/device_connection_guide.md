# NovaCloud物联网平台 - 设备接入指南

## 1. 概述

### 1.1 支持的通信协议

NovaCloud平台目前支持以下通信协议：

- **MQTT**：轻量级发布/订阅消息传输协议，适用于资源受限设备和低带宽、高延迟网络
- **TCP原生**：基于TCP/IP的自定义通信协议，适用于特殊需求的设备

未来计划支持的协议：
- **HTTP/HTTPS**：基于REST API的设备接入
- **Modbus TCP/RTU**：工业自动化设备接入

### 1.2 设备认证机制

所有连接到NovaCloud平台的设备必须通过认证。认证基于以下关键参数：

- **设备ID (`device_id`)**：在平台中注册的设备唯一标识符，格式如 `DEV-123456`
- **设备密钥 (`device_key`)**：平台为每个设备生成的唯一认证密钥

获取这些凭证的途径：
1. 在NovaCloud平台的Web界面创建设备
2. 系统将自动生成设备密钥，**请妥善保存，它只会显示一次**
3. 如果密钥丢失，可以在设备管理页面重置密钥，但这将需要设备重新认证

## 2. MQTT协议接入详解

### 2.1 连接参数

- **Broker地址**：`broker.emqx.io`（公共MQTT服务器，用于测试）
- **端口**：
  - 1883：标准TCP端口（非加密）
  - 8883：TLS/SSL加密端口（推荐用于生产环境）
- **协议版本**：MQTT 3.1.1
- **QoS级别**：建议使用QoS 1（至少一次）确保消息可靠传递

### 2.2 TLS/SSL加密连接

在生产环境中，强烈建议使用TLS加密保护设备通信：

- **服务器证书验证**：默认启用，需要设备信任Broker的CA证书
- **客户端证书验证**：可选，根据安全需求配置
- **TLS版本**：推荐使用TLS 1.2或更高版本

以Python Paho MQTT客户端为例的TLS配置：

```python
import ssl
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.tls_set(
    ca_certs="path/to/ca.crt",     # CA证书路径
    certfile=None,                 # 客户端证书（如需双向认证）
    keyfile=None,                  # 客户端密钥（如需双向认证）
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.connect("broker.emqx.io", 8883, 60)
```

### 2.3 MQTT客户端认证

设备连接到MQTT Broker时，必须提供以下认证信息：

- **Client ID**：建议使用格式 `device_{device_id}_{随机字符串}`，如 `device_DEV-123456_abc123`
- **Username**：必须设置为设备的 `device_id`（例如：`DEV-123456`）
- **Password**：必须设置为设备的 `device_key`

Python示例：

```python
import paho.mqtt.client as mqtt
import random
import string

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"  # 从平台获取的密钥

# 生成随机后缀
suffix = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
client_id = f"device_{device_id}_{suffix}"

# 创建客户端实例
client = mqtt.Client(client_id=client_id)
client.username_pw_set(device_id, device_key)  # 设置用户名和密码

# 连接到MQTT服务器
client.connect("broker.emqx.io", 1883, 60)
```

### 2.4 数据上报 (Device to Cloud)

设备通过以下主题上报数据：

- **主题格式**：`novacloud/devices/{device_id}/data`
  例如：`novacloud/devices/DEV-123456/data`

- **Payload格式**：JSON，包含传感器数据和元数据

```json
{
  "timestamp": 1651234567,      // Unix时间戳（秒）
  "device_id": "DEV-123456",    // 设备ID
  "temperature": 25.5,          // 传感器数据：键名应与平台中传感器的value_key一致
  "humidity": 60.0,
  "light": 500,
  "switch_status": "on"
}
```

- **QoS级别**：建议使用QoS 1
- **Retain标志**：建议设置为false

上报数据的Python示例：

```python
import paho.mqtt.client as mqtt
import json
import time

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 连接回调
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

# 创建客户端
client = mqtt.Client(f"device_{device_id}")
client.username_pw_set(device_id, device_key)
client.on_connect = on_connect

# 连接到服务器
client.connect("broker.emqx.io", 1883, 60)
client.loop_start()

# 数据上报主题
data_topic = f"novacloud/devices/{device_id}/data"

# 上报数据
sensor_data = {
    "timestamp": int(time.time()),
    "device_id": device_id,
    "temperature": 25.5,
    "humidity": 60.0
}

# 发布消息
client.publish(
    topic=data_topic,
    payload=json.dumps(sensor_data),
    qos=1
)

client.loop_stop()
client.disconnect()
```

### 2.5 命令下发 (Cloud to Device)

设备需要订阅以下主题以接收平台下发的命令：

- **主题格式**：`novacloud/devices/{device_id}/command`
  例如：`novacloud/devices/DEV-123456/command`

- **命令Payload格式**：JSON

```json
{
  "command": "set_actuator",    // 命令类型
  "timestamp": 1651234567,      // Unix时间戳（秒）
  "params": {                   // 命令参数
    "relay1": "ON",             // 执行器键名: 值
    "led_brightness": 80
  }
}
```

- **响应**：设备应通过数据主题回复命令执行结果

```json
{
  "response": "actuator_set",   // 响应类型
  "command": "set_actuator",    // 对应的命令
  "timestamp": 1651234570,      // 响应时间戳
  "device_id": "DEV-123456",    // 设备ID
  "success": true,              // 执行结果
  "data": {                     // 执行器当前状态
    "relay1": "ON",
    "led_brightness": 80
  }
}
```

接收命令的Python示例：

```python
import paho.mqtt.client as mqtt
import json
import time

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 全局变量存储设备状态
device_state = {
    "relay1": "OFF",
    "led_brightness": 0
}

# 命令处理函数
def handle_command(payload):
    try:
        cmd = json.loads(payload)
        
        if cmd.get("command") == "set_actuator" and "params" in cmd:
            params = cmd["params"]
            
            # 更新设备状态
            for key, value in params.items():
                if key in device_state:
                    device_state[key] = value
            
            # 构造响应
            response = {
                "response": "actuator_set",
                "command": "set_actuator",
                "timestamp": int(time.time()),
                "device_id": device_id,
                "success": True,
                "data": device_state
            }
            
            # 发送响应
            client.publish(
                topic=f"novacloud/devices/{device_id}/data",
                payload=json.dumps(response),
                qos=1
            )
            
            print(f"Command executed: {params}")
            print(f"Current state: {device_state}")
        
    except Exception as e:
        print(f"Error handling command: {e}")

# 消息回调
def on_message(client, userdata, msg):
    if msg.topic == f"novacloud/devices/{device_id}/command":
        print(f"Command received: {msg.payload.decode()}")
        handle_command(msg.payload)

# 连接回调
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # 订阅命令主题
        client.subscribe(f"novacloud/devices/{device_id}/command", qos=1)
    else:
        print(f"Failed to connect, return code {rc}")

# 创建客户端
client = mqtt.Client(f"device_{device_id}")
client.username_pw_set(device_id, device_key)
client.on_connect = on_connect
client.on_message = on_message

# 连接到服务器并开始循环
client.connect("broker.emqx.io", 1883, 60)
client.loop_forever()
```

### 2.6 设备状态与心跳

设备应定期发送状态消息，确保平台可以监控设备在线状态：

- **主题格式**：`novacloud/devices/{device_id}/status`
  例如：`novacloud/devices/DEV-123456/status`

- **状态Payload格式**：JSON

```json
{
  "status": "online",           // 状态: online, offline, error等
  "timestamp": 1651234567,      // Unix时间戳（秒）
  "device_id": "DEV-123456",    // 设备ID
  "info": {                     // 可选的附加信息
    "ip": "192.168.1.100",
    "version": "1.0.3",
    "rssi": -65
  }
}
```

- **发送频率**：建议60秒一次
- **LWT (Last Will and Testament)**：
  设备应在连接时设置LWT，以便在意外断线时通知平台。LWT应设置为：
  - 主题：`novacloud/devices/{device_id}/status`
  - 消息：`{"status": "offline", "timestamp": 0, "device_id": "{device_id}"}`
  - QoS：1
  - Retain：false

状态上报和LWT配置的Python示例：

```python
import paho.mqtt.client as mqtt
import json
import time
import threading

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 状态主题
status_topic = f"novacloud/devices/{device_id}/status"

# LWT消息
lwt_payload = json.dumps({
    "status": "offline",
    "timestamp": 0,
    "device_id": device_id
})

# 创建客户端
client = mqtt.Client(f"device_{device_id}")
client.username_pw_set(device_id, device_key)

# 设置LWT
client.will_set(
    topic=status_topic,
    payload=lwt_payload,
    qos=1,
    retain=False
)

# 连接到服务器
client.connect("broker.emqx.io", 1883, 60)
client.loop_start()

# 状态上报函数
def report_status():
    while True:
        status_data = {
            "status": "online",
            "timestamp": int(time.time()),
            "device_id": device_id,
            "info": {
                "version": "1.0.3",
                "rssi": -65
            }
        }
        
        client.publish(
            topic=status_topic,
            payload=json.dumps(status_data),
            qos=1
        )
        
        print("Status reported")
        time.sleep(60)  # 60秒上报一次

# 启动状态上报线程
status_thread = threading.Thread(target=report_status)
status_thread.daemon = True
status_thread.start()

# 主循环
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Disconnecting...")
    client.loop_stop()
    client.disconnect()
```

### 2.7 常见MQTT客户端库

以下是各种语言常用的MQTT客户端库：

- **Python**: [Paho MQTT](https://pypi.org/project/paho-mqtt/)
- **JavaScript/Node.js**: [MQTT.js](https://github.com/mqttjs/MQTT.js)
- **Java**: [Eclipse Paho](https://www.eclipse.org/paho/index.php?page=clients/java/index.php)
- **C/C++**: [Eclipse Paho C](https://www.eclipse.org/paho/index.php?page=clients/c/index.php)
- **Arduino**: [PubSubClient](https://github.com/knolleary/pubsubclient)
- **ESP8266/ESP32**: [ESP8266MQTTClient](https://github.com/tuanpmt/ESP8266MQTTClient) 或 [ESP-IDF MQTT组件](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/protocols/mqtt.html)

## 3. TCP协议接入详解

### 3.1 服务器信息

- **服务器地址**: 根据部署环境配置（默认为平台服务器IP或域名）
- **端口**: 9000（默认）
- **协议**: TCP
- **帧分隔符**: `\n`（换行符，ASCII码10）
- **最大消息大小**: 128KB

### 3.2 连接建立与认证

1. 设备建立TCP连接到服务器
2. 连接成功后，设备必须在10秒内发送认证消息：

```json
{
  "type": "auth",
  "device_id": "DEV-123456",
  "device_key": "your_device_key_here"
}
```

3. 服务器验证认证信息后，将返回认证结果：

```json
{
  "type": "auth_result",
  "result": "success",        // 或 "failed"
  "message": "Authenticated", // 或错误原因
  "timestamp": 1651234567
}
```

4. 如果认证失败，服务器将关闭连接

Python TCP客户端示例：

```python
import socket
import json
import time
import threading

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 服务器信息
server_host = "your.server.domain"
server_port = 9000

# 创建套接字
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_host, server_port))

# 发送认证消息
auth_message = {
    "type": "auth",
    "device_id": device_id,
    "device_key": device_key
}

client_socket.send((json.dumps(auth_message) + "\n").encode('utf-8'))

# 接收认证结果
response = client_socket.recv(1024).decode('utf-8')
auth_result = json.loads(response)

if auth_result.get("result") == "success":
    print("Authentication successful")
else:
    print(f"Authentication failed: {auth_result.get('message')}")
    client_socket.close()
    exit(1)

# 后续与服务器通信...
```

### 3.3 数据帧格式

NovaCloud TCP协议使用JSON格式的消息，每条消息以换行符(`\n`)结束。

#### 设备数据上报

```json
{
  "type": "data",
  "device_id": "DEV-123456",
  "timestamp": 1651234567,
  "values": {
    "temperature": 25.5,
    "humidity": 60.0,
    "light": 500
  }
}
```

#### 设备状态上报

```json
{
  "type": "status",
  "device_id": "DEV-123456",
  "timestamp": 1651234567,
  "status": "online",
  "info": {
    "version": "1.0.3",
    "rssi": -65
  }
}
```

#### 平台发送命令

```json
{
  "type": "command",
  "command_id": "cmd-12345",
  "device_id": "DEV-123456",
  "timestamp": 1651234567,
  "command": "set_actuator",
  "params": {
    "relay1": "ON",
    "led_brightness": 80
  }
}
```

#### 设备响应命令

```json
{
  "type": "command_response",
  "command_id": "cmd-12345",
  "device_id": "DEV-123456",
  "timestamp": 1651234570,
  "result": "success",
  "data": {
    "relay1": "ON",
    "led_brightness": 80
  }
}
```

### 3.4 心跳保活机制

为保持连接活跃，设备和服务器之间定期交换心跳消息：

1. 设备应每60秒（可配置）发送一次心跳消息：

```json
{
  "type": "ping",
  "device_id": "DEV-123456",
  "timestamp": 1651234567
}
```

2. 服务器会回复：

```json
{
  "type": "pong",
  "timestamp": 1651234567
}
```

3. 如果设备180秒（3倍心跳间隔）未收到任何消息，应关闭连接并重新连接
4. 如果服务器180秒未收到设备消息，会关闭连接

完整的TCP客户端示例：

```python
import socket
import json
import time
import threading
import queue

# 设备凭证和服务器信息
device_id = "DEV-123456"
device_key = "your_device_key_here"
server_host = "your.server.domain"
server_port = 9000

# 消息队列和锁
send_queue = queue.Queue()
socket_lock = threading.Lock()

# 创建套接字并连接
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_host, server_port))

# 发送消息函数
def send_message(message):
    with socket_lock:
        client_socket.send((json.dumps(message) + "\n").encode('utf-8'))

# 认证
auth_message = {
    "type": "auth",
    "device_id": device_id,
    "device_key": device_key
}
send_message(auth_message)

# 接收线程
def receiver():
    buffer = ""
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                print("Connection closed by server")
                break
                
            buffer += data
            
            # 处理完整消息
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                message = json.loads(line)
                handle_message(message)
                
        except Exception as e:
            print(f"Receiver error: {e}")
            break
    
    # 连接断开，开始重连
    reconnect()

# 消息处理函数
def handle_message(message):
    msg_type = message.get("type")
    
    if msg_type == "auth_result":
        if message.get("result") == "success":
            print("Authentication successful")
        else:
            print(f"Authentication failed: {message.get('message')}")
            client_socket.close()
            exit(1)
            
    elif msg_type == "pong":
        print("Received heartbeat response")
        
    elif msg_type == "command":
        # 处理命令
        cmd_id = message.get("command_id")
        cmd = message.get("command")
        params = message.get("params", {})
        
        print(f"Received command: {cmd}, params: {params}")
        
        # 构造响应
        response = {
            "type": "command_response",
            "command_id": cmd_id,
            "device_id": device_id,
            "timestamp": int(time.time()),
            "result": "success",
            "data": params  # 实际应用中应根据命令执行结果填充
        }
        
        # 发送响应
        send_queue.put(response)

# 发送线程
def sender():
    while True:
        try:
            # 从队列获取要发送的消息
            message = send_queue.get(timeout=1)
            send_message(message)
            send_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Sender error: {e}")
            break

# 心跳线程
def heartbeat():
    while True:
        try:
            ping_message = {
                "type": "ping",
                "device_id": device_id,
                "timestamp": int(time.time())
            }
            send_queue.put(ping_message)
            print("Heartbeat sent")
            time.sleep(60)  # 心跳间隔
        except Exception as e:
            print(f"Heartbeat error: {e}")
            break

# 状态上报线程
def status_reporter():
    while True:
        try:
            status_message = {
                "type": "status",
                "device_id": device_id,
                "timestamp": int(time.time()),
                "status": "online",
                "info": {
                    "version": "1.0.3"
                }
            }
            send_queue.put(status_message)
            print("Status reported")
            time.sleep(300)  # 每5分钟上报一次状态
        except Exception as e:
            print(f"Status reporter error: {e}")
            break

# 重连函数
def reconnect():
    global client_socket
    
    print("Reconnecting...")
    time.sleep(5)  # 等待5秒再重连
    
    try:
        # 关闭旧连接
        with socket_lock:
            if client_socket:
                try:
                    client_socket.close()
                except:
                    pass
                
        # 创建新连接
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_host, server_port))
        
        # 重新认证
        auth_message = {
            "type": "auth",
            "device_id": device_id,
            "device_key": device_key
        }
        with socket_lock:
            client_socket.send((json.dumps(auth_message) + "\n").encode('utf-8'))
            
        print("Reconnection successful")
        
        # 重启接收线程
        rx_thread = threading.Thread(target=receiver)
        rx_thread.daemon = True
        rx_thread.start()
        
    except Exception as e:
        print(f"Reconnection failed: {e}")
        # 稍后再试
        timer = threading.Timer(30, reconnect)
        timer.daemon = True
        timer.start()

# 启动线程
rx_thread = threading.Thread(target=receiver)
tx_thread = threading.Thread(target=sender)
hb_thread = threading.Thread(target=heartbeat)
st_thread = threading.Thread(target=status_reporter)

rx_thread.daemon = True
tx_thread.daemon = True
hb_thread.daemon = True
st_thread.daemon = True

rx_thread.start()
tx_thread.start()
hb_thread.start()
st_thread.start()

# 主循环
try:
    while True:
        time.sleep(1)
        # 在此可以添加定期数据上报逻辑
except KeyboardInterrupt:
    print("Shutting down...")
    client_socket.close()
```

## 4. HTTP API接入（计划中）

HTTP API接入目前正在规划中，未来版本将支持通过RESTful API进行设备通信。

## 5. 故障排查与支持

### 连接问题

1. **无法连接到MQTT Broker**
   - 检查网络连接和防火墙设置
   - 验证服务器地址和端口是否正确
   - 确认设备ID和密钥是否正确

2. **认证失败**
   - 确认使用正确的设备ID和密钥
   - 检查设备状态是否为"已激活"
   - 如果重置过密钥，确保使用最新密钥

3. **连接不稳定**
   - 检查网络质量和信号强度
   - 实现适当的重连机制
   - 考虑使用QoS 1确保消息可靠传递

### 数据问题

1. **数据未显示在平台**
   - 确认设备认证成功
   - 检查数据格式是否正确
   - 验证传感器"值键名"配置是否与上报数据中的键名一致
   - 确认使用了正确的主题

2. **命令无响应**
   - 确认设备已订阅命令主题
   - 检查命令处理逻辑是否正确
   - 验证设备是否发送了命令响应

### 技术支持

如需进一步的技术支持：
- 查看完整的API文档
- 联系NovaCloud平台技术支持团队
- 在设备调试时启用详细日志，便于诊断问题 

## 1. 概述

### 1.1 支持的通信协议

NovaCloud平台目前支持以下通信协议：

- **MQTT**：轻量级发布/订阅消息传输协议，适用于资源受限设备和低带宽、高延迟网络
- **TCP原生**：基于TCP/IP的自定义通信协议，适用于特殊需求的设备

未来计划支持的协议：
- **HTTP/HTTPS**：基于REST API的设备接入
- **Modbus TCP/RTU**：工业自动化设备接入

### 1.2 设备认证机制

所有连接到NovaCloud平台的设备必须通过认证。认证基于以下关键参数：

- **设备ID (`device_id`)**：在平台中注册的设备唯一标识符，格式如 `DEV-123456`
- **设备密钥 (`device_key`)**：平台为每个设备生成的唯一认证密钥

获取这些凭证的途径：
1. 在NovaCloud平台的Web界面创建设备
2. 系统将自动生成设备密钥，**请妥善保存，它只会显示一次**
3. 如果密钥丢失，可以在设备管理页面重置密钥，但这将需要设备重新认证

## 2. MQTT协议接入详解

### 2.1 连接参数

- **Broker地址**：`broker.emqx.io`（公共MQTT服务器，用于测试）
- **端口**：
  - 1883：标准TCP端口（非加密）
  - 8883：TLS/SSL加密端口（推荐用于生产环境）
- **协议版本**：MQTT 3.1.1
- **QoS级别**：建议使用QoS 1（至少一次）确保消息可靠传递

### 2.2 TLS/SSL加密连接

在生产环境中，强烈建议使用TLS加密保护设备通信：

- **服务器证书验证**：默认启用，需要设备信任Broker的CA证书
- **客户端证书验证**：可选，根据安全需求配置
- **TLS版本**：推荐使用TLS 1.2或更高版本

以Python Paho MQTT客户端为例的TLS配置：

```python
import ssl
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.tls_set(
    ca_certs="path/to/ca.crt",     # CA证书路径
    certfile=None,                 # 客户端证书（如需双向认证）
    keyfile=None,                  # 客户端密钥（如需双向认证）
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.connect("broker.emqx.io", 8883, 60)
```

### 2.3 MQTT客户端认证

设备连接到MQTT Broker时，必须提供以下认证信息：

- **Client ID**：建议使用格式 `device_{device_id}_{随机字符串}`，如 `device_DEV-123456_abc123`
- **Username**：必须设置为设备的 `device_id`（例如：`DEV-123456`）
- **Password**：必须设置为设备的 `device_key`

Python示例：

```python
import paho.mqtt.client as mqtt
import random
import string

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"  # 从平台获取的密钥

# 生成随机后缀
suffix = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
client_id = f"device_{device_id}_{suffix}"

# 创建客户端实例
client = mqtt.Client(client_id=client_id)
client.username_pw_set(device_id, device_key)  # 设置用户名和密码

# 连接到MQTT服务器
client.connect("broker.emqx.io", 1883, 60)
```

### 2.4 数据上报 (Device to Cloud)

设备通过以下主题上报数据：

- **主题格式**：`novacloud/devices/{device_id}/data`
  例如：`novacloud/devices/DEV-123456/data`

- **Payload格式**：JSON，包含传感器数据和元数据

```json
{
  "timestamp": 1651234567,      // Unix时间戳（秒）
  "device_id": "DEV-123456",    // 设备ID
  "temperature": 25.5,          // 传感器数据：键名应与平台中传感器的value_key一致
  "humidity": 60.0,
  "light": 500,
  "switch_status": "on"
}
```

- **QoS级别**：建议使用QoS 1
- **Retain标志**：建议设置为false

上报数据的Python示例：

```python
import paho.mqtt.client as mqtt
import json
import time

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 连接回调
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

# 创建客户端
client = mqtt.Client(f"device_{device_id}")
client.username_pw_set(device_id, device_key)
client.on_connect = on_connect

# 连接到服务器
client.connect("broker.emqx.io", 1883, 60)
client.loop_start()

# 数据上报主题
data_topic = f"novacloud/devices/{device_id}/data"

# 上报数据
sensor_data = {
    "timestamp": int(time.time()),
    "device_id": device_id,
    "temperature": 25.5,
    "humidity": 60.0
}

# 发布消息
client.publish(
    topic=data_topic,
    payload=json.dumps(sensor_data),
    qos=1
)

client.loop_stop()
client.disconnect()
```

### 2.5 命令下发 (Cloud to Device)

设备需要订阅以下主题以接收平台下发的命令：

- **主题格式**：`novacloud/devices/{device_id}/command`
  例如：`novacloud/devices/DEV-123456/command`

- **命令Payload格式**：JSON

```json
{
  "command": "set_actuator",    // 命令类型
  "timestamp": 1651234567,      // Unix时间戳（秒）
  "params": {                   // 命令参数
    "relay1": "ON",             // 执行器键名: 值
    "led_brightness": 80
  }
}
```

- **响应**：设备应通过数据主题回复命令执行结果

```json
{
  "response": "actuator_set",   // 响应类型
  "command": "set_actuator",    // 对应的命令
  "timestamp": 1651234570,      // 响应时间戳
  "device_id": "DEV-123456",    // 设备ID
  "success": true,              // 执行结果
  "data": {                     // 执行器当前状态
    "relay1": "ON",
    "led_brightness": 80
  }
}
```

接收命令的Python示例：

```python
import paho.mqtt.client as mqtt
import json
import time

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 全局变量存储设备状态
device_state = {
    "relay1": "OFF",
    "led_brightness": 0
}

# 命令处理函数
def handle_command(payload):
    try:
        cmd = json.loads(payload)
        
        if cmd.get("command") == "set_actuator" and "params" in cmd:
            params = cmd["params"]
            
            # 更新设备状态
            for key, value in params.items():
                if key in device_state:
                    device_state[key] = value
            
            # 构造响应
            response = {
                "response": "actuator_set",
                "command": "set_actuator",
                "timestamp": int(time.time()),
                "device_id": device_id,
                "success": True,
                "data": device_state
            }
            
            # 发送响应
            client.publish(
                topic=f"novacloud/devices/{device_id}/data",
                payload=json.dumps(response),
                qos=1
            )
            
            print(f"Command executed: {params}")
            print(f"Current state: {device_state}")
        
    except Exception as e:
        print(f"Error handling command: {e}")

# 消息回调
def on_message(client, userdata, msg):
    if msg.topic == f"novacloud/devices/{device_id}/command":
        print(f"Command received: {msg.payload.decode()}")
        handle_command(msg.payload)

# 连接回调
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # 订阅命令主题
        client.subscribe(f"novacloud/devices/{device_id}/command", qos=1)
    else:
        print(f"Failed to connect, return code {rc}")

# 创建客户端
client = mqtt.Client(f"device_{device_id}")
client.username_pw_set(device_id, device_key)
client.on_connect = on_connect
client.on_message = on_message

# 连接到服务器并开始循环
client.connect("broker.emqx.io", 1883, 60)
client.loop_forever()
```

### 2.6 设备状态与心跳

设备应定期发送状态消息，确保平台可以监控设备在线状态：

- **主题格式**：`novacloud/devices/{device_id}/status`
  例如：`novacloud/devices/DEV-123456/status`

- **状态Payload格式**：JSON

```json
{
  "status": "online",           // 状态: online, offline, error等
  "timestamp": 1651234567,      // Unix时间戳（秒）
  "device_id": "DEV-123456",    // 设备ID
  "info": {                     // 可选的附加信息
    "ip": "192.168.1.100",
    "version": "1.0.3",
    "rssi": -65
  }
}
```

- **发送频率**：建议60秒一次
- **LWT (Last Will and Testament)**：
  设备应在连接时设置LWT，以便在意外断线时通知平台。LWT应设置为：
  - 主题：`novacloud/devices/{device_id}/status`
  - 消息：`{"status": "offline", "timestamp": 0, "device_id": "{device_id}"}`
  - QoS：1
  - Retain：false

状态上报和LWT配置的Python示例：

```python
import paho.mqtt.client as mqtt
import json
import time
import threading

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 状态主题
status_topic = f"novacloud/devices/{device_id}/status"

# LWT消息
lwt_payload = json.dumps({
    "status": "offline",
    "timestamp": 0,
    "device_id": device_id
})

# 创建客户端
client = mqtt.Client(f"device_{device_id}")
client.username_pw_set(device_id, device_key)

# 设置LWT
client.will_set(
    topic=status_topic,
    payload=lwt_payload,
    qos=1,
    retain=False
)

# 连接到服务器
client.connect("broker.emqx.io", 1883, 60)
client.loop_start()

# 状态上报函数
def report_status():
    while True:
        status_data = {
            "status": "online",
            "timestamp": int(time.time()),
            "device_id": device_id,
            "info": {
                "version": "1.0.3",
                "rssi": -65
            }
        }
        
        client.publish(
            topic=status_topic,
            payload=json.dumps(status_data),
            qos=1
        )
        
        print("Status reported")
        time.sleep(60)  # 60秒上报一次

# 启动状态上报线程
status_thread = threading.Thread(target=report_status)
status_thread.daemon = True
status_thread.start()

# 主循环
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Disconnecting...")
    client.loop_stop()
    client.disconnect()
```

### 2.7 常见MQTT客户端库

以下是各种语言常用的MQTT客户端库：

- **Python**: [Paho MQTT](https://pypi.org/project/paho-mqtt/)
- **JavaScript/Node.js**: [MQTT.js](https://github.com/mqttjs/MQTT.js)
- **Java**: [Eclipse Paho](https://www.eclipse.org/paho/index.php?page=clients/java/index.php)
- **C/C++**: [Eclipse Paho C](https://www.eclipse.org/paho/index.php?page=clients/c/index.php)
- **Arduino**: [PubSubClient](https://github.com/knolleary/pubsubclient)
- **ESP8266/ESP32**: [ESP8266MQTTClient](https://github.com/tuanpmt/ESP8266MQTTClient) 或 [ESP-IDF MQTT组件](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/protocols/mqtt.html)

## 3. TCP协议接入详解

### 3.1 服务器信息

- **服务器地址**: 根据部署环境配置（默认为平台服务器IP或域名）
- **端口**: 9000（默认）
- **协议**: TCP
- **帧分隔符**: `\n`（换行符，ASCII码10）
- **最大消息大小**: 128KB

### 3.2 连接建立与认证

1. 设备建立TCP连接到服务器
2. 连接成功后，设备必须在10秒内发送认证消息：

```json
{
  "type": "auth",
  "device_id": "DEV-123456",
  "device_key": "your_device_key_here"
}
```

3. 服务器验证认证信息后，将返回认证结果：

```json
{
  "type": "auth_result",
  "result": "success",        // 或 "failed"
  "message": "Authenticated", // 或错误原因
  "timestamp": 1651234567
}
```

4. 如果认证失败，服务器将关闭连接

Python TCP客户端示例：

```python
import socket
import json
import time
import threading

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 服务器信息
server_host = "your.server.domain"
server_port = 9000

# 创建套接字
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_host, server_port))

# 发送认证消息
auth_message = {
    "type": "auth",
    "device_id": device_id,
    "device_key": device_key
}

client_socket.send((json.dumps(auth_message) + "\n").encode('utf-8'))

# 接收认证结果
response = client_socket.recv(1024).decode('utf-8')
auth_result = json.loads(response)

if auth_result.get("result") == "success":
    print("Authentication successful")
else:
    print(f"Authentication failed: {auth_result.get('message')}")
    client_socket.close()
    exit(1)

# 后续与服务器通信...
```

### 3.3 数据帧格式

NovaCloud TCP协议使用JSON格式的消息，每条消息以换行符(`\n`)结束。

#### 设备数据上报

```json
{
  "type": "data",
  "device_id": "DEV-123456",
  "timestamp": 1651234567,
  "values": {
    "temperature": 25.5,
    "humidity": 60.0,
    "light": 500
  }
}
```

#### 设备状态上报

```json
{
  "type": "status",
  "device_id": "DEV-123456",
  "timestamp": 1651234567,
  "status": "online",
  "info": {
    "version": "1.0.3",
    "rssi": -65
  }
}
```

#### 平台发送命令

```json
{
  "type": "command",
  "command_id": "cmd-12345",
  "device_id": "DEV-123456",
  "timestamp": 1651234567,
  "command": "set_actuator",
  "params": {
    "relay1": "ON",
    "led_brightness": 80
  }
}
```

#### 设备响应命令

```json
{
  "type": "command_response",
  "command_id": "cmd-12345",
  "device_id": "DEV-123456",
  "timestamp": 1651234570,
  "result": "success",
  "data": {
    "relay1": "ON",
    "led_brightness": 80
  }
}
```

### 3.4 心跳保活机制

为保持连接活跃，设备和服务器之间定期交换心跳消息：

1. 设备应每60秒（可配置）发送一次心跳消息：

```json
{
  "type": "ping",
  "device_id": "DEV-123456",
  "timestamp": 1651234567
}
```

2. 服务器会回复：

```json
{
  "type": "pong",
  "timestamp": 1651234567
}
```

3. 如果设备180秒（3倍心跳间隔）未收到任何消息，应关闭连接并重新连接
4. 如果服务器180秒未收到设备消息，会关闭连接

完整的TCP客户端示例：

```python
import socket
import json
import time
import threading
import queue

# 设备凭证和服务器信息
device_id = "DEV-123456"
device_key = "your_device_key_here"
server_host = "your.server.domain"
server_port = 9000

# 消息队列和锁
send_queue = queue.Queue()
socket_lock = threading.Lock()

# 创建套接字并连接
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_host, server_port))

# 发送消息函数
def send_message(message):
    with socket_lock:
        client_socket.send((json.dumps(message) + "\n").encode('utf-8'))

# 认证
auth_message = {
    "type": "auth",
    "device_id": device_id,
    "device_key": device_key
}
send_message(auth_message)

# 接收线程
def receiver():
    buffer = ""
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                print("Connection closed by server")
                break
                
            buffer += data
            
            # 处理完整消息
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                message = json.loads(line)
                handle_message(message)
                
        except Exception as e:
            print(f"Receiver error: {e}")
            break
    
    # 连接断开，开始重连
    reconnect()

# 消息处理函数
def handle_message(message):
    msg_type = message.get("type")
    
    if msg_type == "auth_result":
        if message.get("result") == "success":
            print("Authentication successful")
        else:
            print(f"Authentication failed: {message.get('message')}")
            client_socket.close()
            exit(1)
            
    elif msg_type == "pong":
        print("Received heartbeat response")
        
    elif msg_type == "command":
        # 处理命令
        cmd_id = message.get("command_id")
        cmd = message.get("command")
        params = message.get("params", {})
        
        print(f"Received command: {cmd}, params: {params}")
        
        # 构造响应
        response = {
            "type": "command_response",
            "command_id": cmd_id,
            "device_id": device_id,
            "timestamp": int(time.time()),
            "result": "success",
            "data": params  # 实际应用中应根据命令执行结果填充
        }
        
        # 发送响应
        send_queue.put(response)

# 发送线程
def sender():
    while True:
        try:
            # 从队列获取要发送的消息
            message = send_queue.get(timeout=1)
            send_message(message)
            send_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Sender error: {e}")
            break

# 心跳线程
def heartbeat():
    while True:
        try:
            ping_message = {
                "type": "ping",
                "device_id": device_id,
                "timestamp": int(time.time())
            }
            send_queue.put(ping_message)
            print("Heartbeat sent")
            time.sleep(60)  # 心跳间隔
        except Exception as e:
            print(f"Heartbeat error: {e}")
            break

# 状态上报线程
def status_reporter():
    while True:
        try:
            status_message = {
                "type": "status",
                "device_id": device_id,
                "timestamp": int(time.time()),
                "status": "online",
                "info": {
                    "version": "1.0.3"
                }
            }
            send_queue.put(status_message)
            print("Status reported")
            time.sleep(300)  # 每5分钟上报一次状态
        except Exception as e:
            print(f"Status reporter error: {e}")
            break

# 重连函数
def reconnect():
    global client_socket
    
    print("Reconnecting...")
    time.sleep(5)  # 等待5秒再重连
    
    try:
        # 关闭旧连接
        with socket_lock:
            if client_socket:
                try:
                    client_socket.close()
                except:
                    pass
                
        # 创建新连接
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_host, server_port))
        
        # 重新认证
        auth_message = {
            "type": "auth",
            "device_id": device_id,
            "device_key": device_key
        }
        with socket_lock:
            client_socket.send((json.dumps(auth_message) + "\n").encode('utf-8'))
            
        print("Reconnection successful")
        
        # 重启接收线程
        rx_thread = threading.Thread(target=receiver)
        rx_thread.daemon = True
        rx_thread.start()
        
    except Exception as e:
        print(f"Reconnection failed: {e}")
        # 稍后再试
        timer = threading.Timer(30, reconnect)
        timer.daemon = True
        timer.start()

# 启动线程
rx_thread = threading.Thread(target=receiver)
tx_thread = threading.Thread(target=sender)
hb_thread = threading.Thread(target=heartbeat)
st_thread = threading.Thread(target=status_reporter)

rx_thread.daemon = True
tx_thread.daemon = True
hb_thread.daemon = True
st_thread.daemon = True

rx_thread.start()
tx_thread.start()
hb_thread.start()
st_thread.start()

# 主循环
try:
    while True:
        time.sleep(1)
        # 在此可以添加定期数据上报逻辑
except KeyboardInterrupt:
    print("Shutting down...")
    client_socket.close()
```

## 4. HTTP API接入（计划中）

HTTP API接入目前正在规划中，未来版本将支持通过RESTful API进行设备通信。

## 5. 故障排查与支持

### 连接问题

1. **无法连接到MQTT Broker**
   - 检查网络连接和防火墙设置
   - 验证服务器地址和端口是否正确
   - 确认设备ID和密钥是否正确

2. **认证失败**
   - 确认使用正确的设备ID和密钥
   - 检查设备状态是否为"已激活"
   - 如果重置过密钥，确保使用最新密钥

3. **连接不稳定**
   - 检查网络质量和信号强度
   - 实现适当的重连机制
   - 考虑使用QoS 1确保消息可靠传递

### 数据问题

1. **数据未显示在平台**
   - 确认设备认证成功
   - 检查数据格式是否正确
   - 验证传感器"值键名"配置是否与上报数据中的键名一致
   - 确认使用了正确的主题

2. **命令无响应**
   - 确认设备已订阅命令主题
   - 检查命令处理逻辑是否正确
   - 验证设备是否发送了命令响应

### 技术支持

如需进一步的技术支持：
- 查看完整的API文档
- 联系NovaCloud平台技术支持团队
- 在设备调试时启用详细日志，便于诊断问题 