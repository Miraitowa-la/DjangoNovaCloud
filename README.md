# NovaCloud物联网云平台

NovaCloud是一个功能强大的物联网云平台，专为连接、管理和监控各类物联网设备而设计。平台提供安全、可靠的设备连接服务，支持实时数据采集、可视化展示和远程控制功能。

## 核心功能

- **多级项目管理**：组织和管理多个物联网项目，支持项目分组和权限控制
- **设备生命周期管理**：添加、配置、监控和维护物联网设备的完整生命周期
- **多协议设备接入**：支持MQTT和TCP原生协议，未来将支持HTTP/HTTPS和Modbus TCP/RTU
- **传感器数据采集**：实时收集和存储设备传感器数据，支持多种数据类型
- **执行器远程控制**：通过Web界面或API远程控制设备上的执行器组件
- **数据可视化**：使用Chart.js提供直观的时间序列图表、数据表格和状态指示器
- **自动化策略引擎**：基于传感器数据配置自动化规则和触发器，支持条件组合和多种动作类型
- **安全认证机制**：完善的用户认证和设备认证体系，支持用户名/邮箱登录
- **后台管理界面**：自定义的Django Admin界面，提供直观的系统管理功能

## 系统架构

NovaCloud平台采用模块化设计，主要由以下核心应用组成：

- **核心应用(core)**：提供平台的主页和仪表盘，是用户的主要交互界面
- **账户管理(accounts)**：处理用户注册、登录和身份验证，支持邮箱登录
- **物联网设备(iot_devices)**：管理项目、设备、传感器和执行器的核心模块
- **MQTT客户端(mqtt_client)**：处理与设备的MQTT协议通信，采用单例模式设计
- **TCP服务器(tcp_server)**：提供TCP原生协议支持，适用于资源受限设备
- **策略引擎(strategy_engine)**：实现自动化规则处理，支持条件评估和动作执行

## 技术栈

- **后端框架**：Python 3.12.3+, Django 5.2.1+
- **API框架**：Django REST Framework 3.16.0+
- **数据库**：SQLite (开发环境), PostgreSQL (生产环境推荐)
- **设备通信**：MQTT (Paho-MQTT), TCP Socket
- **前端技术**：HTML5, CSS3, JavaScript, Chart.js
- **部署工具**：Gunicorn/Daphne, Nginx, Redis
- **安全组件**：TLS/SSL, CSRF保护, 输入验证, 密码策略

## 安全特性

NovaCloud平台内置多层安全保护机制：

- **输入验证**：严格验证所有用户输入，防止XSS、SQL注入和命令注入攻击
- **CSRF保护**：所有表单和AJAX请求都包含CSRF令牌，防止跨站请求伪造
- **密码安全**：强密码策略，密码哈希存储，支持密码重置
- **设备认证**：设备使用唯一的device_id和device_key进行认证
- **通信加密**：支持TLS/SSL加密的MQTT连接，保护数据传输安全
- **权限控制**：基于用户的访问控制，确保用户只能访问自己的项目和设备
- **安全日志**：详细的安全事件日志记录，支持审计和异常检测
- **依赖管理**：定期检查和更新依赖库，防范已知漏洞

## 快速开始

### 系统要求

- Python 3.12.3 或更高版本
- pip (Python包管理器)
- 虚拟环境工具 (推荐)
- Git (用于获取代码)

### 安装步骤

1. 克隆代码库:
```bash
git clone https://github.com/your-organization/novacloud.git
cd novacloud
```

2. 创建并激活虚拟环境:
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

3. 安装依赖:
```bash
pip install -r requirements.txt
```

4. 创建环境变量文件(.env):
```
DEBUG=True
SECRET_KEY=your_dev_secret_key_here
ALLOWED_HOSTS=127.0.0.1,localhost
```

5. 初始化数据库:
```bash
python manage.py migrate
```

6. 创建管理员账户:
```bash
python manage.py createsuperuser
```

7. 启动开发服务器:
```bash
python manage.py runserver
```

8. 访问平台: http://127.0.0.1:8000/

## 设备接入

NovaCloud支持两种主要的设备接入协议:

### MQTT接入

MQTT是一种轻量级的发布/订阅消息传输协议，适用于资源受限设备和低带宽网络环境。

```python
import paho.mqtt.client as mqtt
import json
import time
import uuid

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 生成客户端ID (推荐使用设备ID加随机字符串)
client_id = f"device_{device_id}_{uuid.uuid4().hex[:8]}"

# 连接回调
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if rc == 0:
        # 订阅命令主题
        client.subscribe(f"novacloud/devices/{device_id}/command")
        client.subscribe(f"novacloud/devices/{device_id}/config")
        
        # 连接成功后发送在线状态
        status_msg = {
            "status": "online",
            "timestamp": int(time.time()),
            "device_id": device_id,
            "info": {
                "version": "1.0.0",
                "ip": "192.168.1.100"
            }
        }
        client.publish(f"novacloud/devices/{device_id}/status", 
                      json.dumps(status_msg), qos=1)

# 消息回调
def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()}")
    
    if "command" in msg.topic:
        try:
            command = json.loads(msg.payload.decode())
            # 处理命令
            if "command" in command:
                if command["command"] == "set_actuator" and "params" in command:
                    # 执行器控制命令处理
                    handle_actuator_command(command["params"])
                elif command["command"] == "ping":
                    # 响应ping命令
                    response = {
                        "response": "pong",
                        "timestamp": int(time.time()),
                        "device_id": device_id
                    }
                    client.publish(f"novacloud/devices/{device_id}/data", 
                                  json.dumps(response), qos=1)
        except Exception as e:
            print(f"Error processing command: {e}")

# 执行器命令处理
def handle_actuator_command(params):
    # 实际应用中，这里应该控制物理设备的执行器
    print(f"Executing actuator command with params: {params}")
    
    # 执行后上报新状态
    response = {
        "response": "actuator_state",
        "timestamp": int(time.time()),
        "device_id": device_id,
        "actuator_states": params  # 简化示例，实际应返回真实执行结果
    }
    client.publish(f"novacloud/devices/{device_id}/data", 
                  json.dumps(response), qos=1)

# 创建客户端
client = mqtt.Client(client_id=client_id)
client.username_pw_set(device_id, device_key)  # 使用device_id作为用户名，device_key作为密码
client.on_connect = on_connect
client.on_message = on_message

# 设置遗嘱消息(LWT)，设备意外断线时发送
lwt_msg = json.dumps({
    "status": "offline",
    "timestamp": 0,
    "device_id": device_id
})
client.will_set(f"novacloud/devices/{device_id}/status", lwt_msg, qos=1, retain=False)

# 连接到MQTT代理
client.connect("broker.emqx.io", 1883, 60)
client.loop_start()

# 定期上报数据
try:
    while True:
        # 模拟传感器数据
        data = {
            "temperature": 25.5 + (time.time() % 10 - 5) / 10,  # 模拟温度变化
            "humidity": 60 + (time.time() % 10 - 5) / 5,        # 模拟湿度变化
            "light": 500 + (time.time() % 100),                 # 模拟光照变化
            "timestamp": int(time.time()),
            "device_id": device_id
        }
        
        # 发布数据
        client.publish(f"novacloud/devices/{device_id}/data", 
                      json.dumps(data), qos=1)
        print(f"Data published: {data}")
        
        # 每10秒发送一次数据
        time.sleep(10)
except KeyboardInterrupt:
    # 发送离线状态并断开连接
    status_msg = {
        "status": "offline",
        "timestamp": int(time.time()),
        "device_id": device_id
    }
    client.publish(f"novacloud/devices/{device_id}/status", 
                  json.dumps(status_msg), qos=1)
    client.loop_stop()
    client.disconnect()
    print("Disconnected from MQTT broker")
```

### TCP原生协议接入

TCP原生协议适用于资源更受限的设备，具有更低的协议开销。

```python
import socket
import json
import time
import threading

# 设备凭证
device_id = "DEV-123456"
device_key = "your_device_key_here"

# 创建TCP连接
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ("your.server.domain", 9000)  # 替换为实际服务器地址和端口

try:
    # 连接到服务器
    sock.connect(server_address)
    print(f"Connected to {server_address}")
    
    # 发送认证消息
    auth_message = {
        "type": "auth",
        "device_id": device_id,
        "device_key": device_key
    }
    sock.sendall((json.dumps(auth_message) + "\n").encode())
    
    # 接收线程
    def receive_data():
        buffer = ""
        while True:
            try:
                data = sock.recv(1024).decode()
                if not data:
                    print("Connection closed by server")
                    break
                    
                buffer += data
                
                # 处理完整消息
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    message = json.loads(line)
                    handle_message(message)
            except Exception as e:
                print(f"Error in receive thread: {e}")
                break
        
        # 连接断开，尝试重连
        print("Attempting to reconnect...")
        time.sleep(5)  # 等待5秒后重连
        reconnect()
    
    # 消息处理函数
    def handle_message(message):
        msg_type = message.get("type")
        print(f"Received message of type: {msg_type}")
        
        if msg_type == "auth_result":
            if message.get("result") == "success":
                print("Authentication successful")
                # 认证成功后发送状态
                send_status("online")
            else:
                print(f"Authentication failed: {message.get('message')}")
                sock.close()
                exit(1)
                
        elif msg_type == "command":
            # 处理命令
            cmd = message.get("command")
            params = message.get("params", {})
            command_id = message.get("command_id", "unknown")
            
            print(f"Received command: {cmd}, params: {params}")
            
            # 构造响应
            response = {
                "type": "command_response",
                "command_id": command_id,
                "device_id": device_id,
                "timestamp": int(time.time()),
                "result": "success",
                "data": params  # 实际应用中应根据命令执行结果填充
            }
            
            # 发送响应
            sock.sendall((json.dumps(response) + "\n").encode())
    
    # 发送状态函数
    def send_status(status):
        status_message = {
            "type": "status",
            "device_id": device_id,
            "timestamp": int(time.time()),
            "status": status,
            "info": {
                "version": "1.0.0",
                "ip": "192.168.1.100"
            }
        }
        sock.sendall((json.dumps(status_message) + "\n").encode())
    
    # 发送心跳函数
    def send_heartbeat():
        while True:
            try:
                ping_message = {
                    "type": "ping",
                    "device_id": device_id,
                    "timestamp": int(time.time())
                }
                sock.sendall((json.dumps(ping_message) + "\n").encode())
                print("Heartbeat sent")
                time.sleep(60)  # 每60秒发送一次心跳
            except Exception as e:
                print(f"Error sending heartbeat: {e}")
                break
    
    # 数据上报函数
    def report_data():
        while True:
            try:
                # 模拟传感器数据
                data_message = {
                    "type": "data",
                    "device_id": device_id,
                    "timestamp": int(time.time()),
                    "values": {
                        "temperature": 25.5 + (time.time() % 10 - 5) / 10,
                        "humidity": 60 + (time.time() % 10 - 5) / 5,
                        "light": 500 + (time.time() % 100)
                    }
                }
                sock.sendall((json.dumps(data_message) + "\n").encode())
                print("Data reported")
                time.sleep(30)  # 每30秒上报一次数据
            except Exception as e:
                print(f"Error reporting data: {e}")
                break
    
    # 重连函数
    def reconnect():
        global sock
        try:
            # 关闭旧连接
            sock.close()
            
            # 创建新连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(server_address)
            
            # 重新认证
            auth_message = {
                "type": "auth",
                "device_id": device_id,
                "device_key": device_key
            }
            sock.sendall((json.dumps(auth_message) + "\n").encode())
            
            # 重启接收线程
            rx_thread = threading.Thread(target=receive_data)
            rx_thread.daemon = True
            rx_thread.start()
            
            print("Reconnection successful")
        except Exception as e:
            print(f"Reconnection failed: {e}")
            # 稍后再试
            time.sleep(30)
            reconnect()
    
    # 启动线程
    rx_thread = threading.Thread(target=receive_data)
    hb_thread = threading.Thread(target=send_heartbeat)
    data_thread = threading.Thread(target=report_data)
    
    rx_thread.daemon = True
    hb_thread.daemon = True
    data_thread.daemon = True
    
    rx_thread.start()
    hb_thread.start()
    data_thread.start()
    
    # 主线程保持运行
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("Disconnecting...")
    # 发送离线状态
    send_status("offline")
    sock.close()
    
except Exception as e:
    print(f"Error: {e}")
    sock.close()
```

## 自动化策略引擎

NovaCloud平台的策略引擎允许用户创建基于条件的自动化规则，当满足特定条件时触发相应动作。

### 策略类型

1. **传感器阈值触发**：当传感器数据超过或低于设定阈值时触发
2. **定时执行**：按照设定的时间计划定期执行
3. **设备状态变化**：当设备状态发生变化时触发

### 动作类型

1. **控制执行器**：向设备的执行器发送命令
2. **发送通知**：向用户发送邮件或消息通知
3. **调用Webhook**：向外部系统发送HTTP请求

### 策略示例

温度控制策略：当温度传感器读数超过28°C时，自动开启空调：

```json
{
  "name": "高温开启空调",
  "description": "当温度超过28°C时自动开启空调",
  "conditions": [
    {
      "sensor_id": "SENSOR-TEMP-001",
      "operator": "gt",
      "value": 28.0,
      "value_type": "float"
    }
  ],
  "actions": [
    {
      "action_type": "actuator_control",
      "config": {
        "actuator_id": "ACTUATOR-AC-001",
        "command": "power_on",
        "params": {"mode": "cool", "temperature": 24}
      }
    }
  ],
  "is_enabled": true
}
```

## 数据可视化

NovaCloud平台提供多种数据可视化功能：

1. **时间序列图表**：展示传感器数据随时间的变化趋势
2. **实时数据面板**：显示设备最新状态和传感器读数
3. **历史数据表格**：提供详细的历史数据记录和导出功能
4. **状态指示器**：直观显示设备在线状态和执行器状态
5. **统计分析图表**：数据聚合视图，如平均值、最大/最小值等

## 开发流程

NovaCloud采用标准的Django应用开发流程：

1. **环境设置**：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

2. **创建新应用**：
   ```bash
   python manage.py startapp new_app_name
   ```

3. **定义模型**：在`models.py`中创建数据模型

4. **创建迁移**：
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **编写视图**：在`views.py`中实现功能逻辑

6. **配置URL**：在`urls.py`中定义路由

7. **创建模板**：在`templates/`目录中添加HTML模板

8. **运行测试**：
   ```bash
   python manage.py test
   ```

9. **启动开发服务器**：
   ```bash
   python manage.py runserver
   ```

## 文档

详细文档请查看:

- [用户手册](docs/user_manual.md) - 详细介绍平台功能和使用方法
- [设备接入指南](docs/device_connection_guide.md) - 指导如何将设备连接到平台
- [部署指南](docs/deployment_guide.md) - 平台部署和配置说明
- [开发者指南](docs/developer_guide.md) - 代码架构和开发规范
- [安全指南](docs/security_guide.md) - 安全特性和最佳实践
- [测试指南](docs/testing_guide.md) - 测试方法和流程

## 贡献指南

我们欢迎社区贡献，请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交Pull Request

## 许可证

该项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。 
 