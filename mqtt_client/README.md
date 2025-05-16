# NovaCloud MQTT 通信模块

NovaCloud MQTT 通信模块实现了平台与物联网设备之间基于 MQTT 协议的双向通信。该模块使设备能够上报数据，平台能够接收并处理这些数据，并支持向设备发送命令。

## 主要功能

1. **设备数据上报**
   - 设备可以通过MQTT协议上报传感器数据
   - 平台自动接收并处理设备数据，更新设备状态

2. **设备状态监控**
   - 设备可以上报自身状态（在线/离线）
   - 平台自动跟踪设备最后在线时间

3. **平台命令下发**
   - 平台可以向设备发送命令（如ping, reboot等）
   - 设备可以接收并执行这些命令

## MQTT 主题结构

所有主题都以 `novacloud/` 前缀开始，后跟设备特定的主题路径。

1. **上行主题（设备 → 平台）**
   - 数据上报：`novacloud/devices/{device_id}/data`
   - 状态上报：`novacloud/devices/{device_id}/status`

2. **下行主题（平台 → 设备）**
   - 命令下发：`novacloud/devices/{device_id}/command`
   - 配置下发：`novacloud/devices/{device_id}/config`

## 数据格式

所有通信均使用 JSON 格式，示例如下：

### 设备数据上报
```json
{
  "temperature": 25.5,
  "humidity": 60.0,
  "light": 500,
  "timestamp": 1651234567,
  "device_id": "DEV-123456"
}
```

### 设备状态上报
```json
{
  "status": "online",  // 或 "offline"
  "timestamp": 1651234567,
  "device_id": "DEV-123456"
}
```

### 平台命令下发
```json
{
  "command": "ping",  // 或 "reboot" 等
  "timestamp": 1651234567
}
```

## 设备认证

设备连接 MQTT Broker 时使用以下凭证：
- **用户名**：设备ID (device_id)
- **密码**：设备密钥 (device_key)

## 设备模拟器

项目包含一个设备模拟器，用于测试通信功能。使用方法如下：

```bash
python mqtt_client/device_simulator.py --device_id=DEV-XXXXXX --device_key=your_device_key
```

模拟器将：
1. 连接到MQTT Broker
2. 发布设备状态为"online"
3. 每10秒发布一次随机传感器数据
4. 响应平台的ping和reboot命令
5. 退出时发布设备状态为"offline"

## 平台API

平台提供以下API用于发送命令到设备：

1. **通用命令**
   - URL: `/api/devices/{device_id}/command/`
   - 方法: POST
   - 数据: `{"command": "your_command", ...}`

2. **Ping命令**
   - URL: `/api/devices/{device_id}/ping/`
   - 方法: POST

3. **重启命令**
   - URL: `/api/devices/{device_id}/reboot/`
   - 方法: POST

## 安全注意事项

1. 生产环境中建议使用TLS加密MQTT通信
2. 保护设备密钥，避免泄露
3. 实施适当的访问控制，确保用户只能控制自己的设备
