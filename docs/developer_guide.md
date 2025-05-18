# NovaCloud平台开发者指南

## 1. 技术架构概述

NovaCloud平台采用现代化的Web应用架构，以下是核心技术栈：

### 前端技术
- **HTML5/CSS3**: 构建现代化用户界面
- **JavaScript**: 原生JS用于前端交互
- **Chart.js**: 用于数据可视化和图表展示

### 后端技术
- **Python 3.12.3+**: 主要编程语言
- **Django 5.2.1+**: Web应用框架
- **Django REST Framework**: 用于构建API接口
- **SQLite**: 开发环境数据库
- **PostgreSQL**: 推荐的生产环境数据库
- **Redis**: 用于缓存和消息队列
- **MQTT**: 设备通信协议
- **TCP Socket**: 用于设备通信的替代协议

### 部署工具
- **Gunicorn/Daphne**: WSGI/ASGI服务器
- **Nginx**: Web服务器和反向代理
- **Docker** (可选): 容器化部署

## 2. 项目目录结构

NovaCloud平台的核心目录结构如下：

```
DjangoNovaCloud/           # 项目根目录
├── accounts/              # 用户账户管理应用
├── core/                  # 核心功能应用
├── DjangoNovaCloud/       # 项目配置目录
├── docs/                  # 文档目录
├── iot_devices/           # 物联网设备管理应用
├── mqtt_client/           # MQTT客户端实现
├── static/                # 静态资源
├── strategy_engine/       # 策略引擎应用
├── tcp_server/            # TCP服务器实现
├── templates/             # HTML模板
├── .env                   # 环境变量配置(不包含在版本控制中)
├── .gitignore             # Git忽略配置
├── manage.py              # Django管理脚本
└── requirements.txt       # 项目依赖
```

## 3. 开发环境搭建

### 3.1 前置条件

- Python 3.12.3 或更高版本
- pip (Python包管理器)
- Git
- 开发IDE (推荐PyCharm或VSCode)
- (可选) Docker 和 Docker Compose

### 3.2 克隆代码库并设置虚拟环境

```bash
# 克隆代码库
git clone [repository_url] DjangoNovaCloud
cd DjangoNovaCloud

# 创建并激活虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 3.3 配置开发环境

创建`.env`文件(开发环境配置)：

```
# Django设置
DEBUG=True
SECRET_KEY=your_dev_secret_key_here
ALLOWED_HOSTS=127.0.0.1,localhost

# 数据库设置 - 开发环境使用SQLite
# DATABASE_URL=sqlite:///db.sqlite3

# MQTT设置(使用公共MQTT服务器进行测试)
MQTT_BROKER_HOST=broker.emqx.io
MQTT_BROKER_PORT=1883
MQTT_BROKER_PORT_TLS=8883
MQTT_USE_TLS=False
```

### 3.4 初始化数据库

```bash
# 应用数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

### 3.5 启动开发服务器

```bash
python manage.py runserver
```

访问 http://127.0.0.1:8000/ 查看运行中的应用。

## 4. 代码规范

### 4.1 Python代码规范

NovaCloud遵循PEP 8规范，主要约定包括：

- 使用4个空格进行缩进
- 每行最大长度为79个字符
- 使用下划线命名法(snake_case)命名变量和函数
- 使用驼峰命名法(CamelCase)命名类
- 使用双引号表示字符串
- 导入顺序：标准库 > 第三方库 > 本地应用

推荐使用以下工具保证代码质量：
- **flake8**: 代码风格检查
- **black**: 自动代码格式化
- **isort**: 导入语句排序
- **mypy**: 类型检查

```bash
# 安装开发工具
pip install flake8 black isort mypy

# 运行代码检查
flake8 .

# 自动格式化代码
black .
isort .
```

### 4.2 Django最佳实践

- 使用Django的ORM，避免原生SQL(除非必要)
- 优先使用基于类的视图(Class-Based Views)
- 使用Django的表单系统进行数据验证
- 使用Django的中间件系统进行横切关注点处理
- 遵循DRY(Don't Repeat Yourself)原则
- 保持视图(views)简洁，将业务逻辑放在模型方法或专用服务中

### 4.3 前端代码规范

- HTML/CSS遵循语义化原则
- 使用4个空格缩进
- 为功能完整的JS代码添加JSDoc注释
- 使用camelCase命名JS变量和函数
- 使用kebab-case命名CSS类

## 5. 核心模块详解

### 5.1 用户认证系统(accounts)

主要文件:
- `accounts/forms.py`: 包含用户注册和登录表单
- `accounts/views.py`: 包含认证相关视图
- `accounts/urls.py`: 定义认证相关URL

关键功能:
- 用户注册、登录、登出
- 支持用户名或邮箱登录
- 密码重置(开发中)

扩展建议:
- 添加社交媒体登录
- 实现多因素认证
- 添加用户资料管理

### 5.2 物联网设备管理(iot_devices)

主要文件:
- `iot_devices/models.py`: 定义项目、设备、传感器和执行器模型
- `iot_devices/views.py`: 设备管理视图
- `iot_devices/forms.py`: 设备相关表单

关键对象:
- **Project**: 最高级别的组织单元，包含多个设备
- **Device**: 表示一个物理设备，具有唯一标识和认证密钥
- **Sensor**: 设备上的传感器组件
- **Actuator**: 设备上的执行器组件

重要方法:
- `Device.save()`: 重写以确保自动生成设备密钥
- `SensorData.get_latest_data()`: 获取传感器最新数据

扩展建议:
- 添加设备分组功能
- 实现设备固件更新机制
- 添加设备健康监控

### 5.3 MQTT客户端(mqtt_client)

主要文件:
- `mqtt_client/mqtt.py`: MQTT客户端单例实现
- `mqtt_client/apps.py`: 应用配置(启动时连接MQTT)

关键功能:
- 管理MQTT连接
- 处理设备上报数据
- 发送命令到设备

重要方法:
- `MQTTClient.connect()`: 连接到MQTT代理服务器
- `MQTTClient.on_message()`: 处理接收到的MQTT消息
- `MQTTClient.publish_command()`: 向设备发送命令

扩展建议:
- 添加消息重试机制
- 实现QoS级别配置
- 增强连接故障恢复

### 5.4 TCP服务器(tcp_server)

主要文件:
- `tcp_server/tcp_server.py`: TCP服务器实现
- `tcp_server/apps.py`: 应用配置(启动时启动TCP服务器)

关键功能:
- 监听TCP连接
- 处理设备认证
- 接收设备数据和发送命令

关键类:
- `TCPServer`: 服务器主类
- `ClientHandler`: 处理单个客户端连接

扩展建议:
- 添加更多协议解析器
- 实现TLS/SSL支持
- 添加连接限流机制

### 5.5 策略引擎(strategy_engine)

主要文件:
- `strategy_engine/models.py`: 策略相关模型
- `strategy_engine/evaluator.py`: 条件评估器
- `strategy_engine/executor.py`: 动作执行器

关键对象:
- **Strategy**: 自动化策略定义
- **Condition**: 触发条件
- **Action**: 执行的动作
- **ExecutionLog**: 策略执行日志

工作流程:
1. 数据更新时触发条件评估
2. 满足条件时执行相应动作
3. 记录执行结果

扩展建议:
- 添加更多条件类型(时间条件、复合条件)
- 实现更多动作类型(HTTP回调、SMS通知)
- 添加策略调度和优先级

## 6. 数据库设计

### 6.1 ER图

```
Project(1) --< Device(n)
Device(1) --< Sensor(n)
Device(1) --< Actuator(n)
Sensor(1) --< SensorData(n)
Actuator(1) --< ActuatorCommand(n)
```

### 6.2 主要模型字段

**Project**:
- project_id: CharField (唯一标识符)
- name: CharField
- description: TextField
- owner: ForeignKey(User)
- created_at/updated_at: DateTimeField

**Device**:
- device_id: CharField (唯一标识符)
- device_identifier: CharField (物理标识)
- device_key: CharField (自动生成的认证密钥)
- name: CharField
- project: ForeignKey(Project)
- status: CharField (在线状态)

**Sensor**:
- name: CharField
- sensor_type: CharField
- unit: CharField
- device: ForeignKey(Device)
- value_key: CharField (数据键名)

**Actuator**:
- name: CharField
- actuator_type: CharField
- device: ForeignKey(Device)
- command_key: CharField (命令键名)
- current_state: CharField

## 7. API接口文档

### 7.1 REST API

设备数据API:
- `GET /api/sensors/{sensor_id}/data/`: 获取传感器数据
- `POST /api/sensors/{sensor_id}/data/`: 添加传感器数据
- `GET /api/actuators/{actuator_id}/commands/`: 获取执行器命令历史
- `POST /api/actuators/{actuator_id}/command/`: 向执行器发送命令

设备管理API:
- `GET /api/projects/`: 获取项目列表
- `GET /api/projects/{project_id}/`: 获取项目详情
- `GET /api/projects/{project_id}/devices/`: 获取项目的设备列表
- `GET /api/devices/{device_id}/`: 获取设备详情

认证API:
- `POST /api/auth/token/`: 获取访问令牌
- `POST /api/auth/token/refresh/`: 刷新访问令牌

### 7.2 MQTT主题

数据上报:
- `novacloud/devices/{device_id}/data`: 设备数据上报
- `novacloud/devices/{device_id}/status`: 设备状态上报

命令下发:
- `novacloud/devices/{device_id}/command`: 平台发送命令
- `novacloud/devices/{device_id}/config`: 设备配置下发

### 7.3 TCP协议

消息格式: JSON
分隔符: 换行符(\n)

消息类型:
- `auth`: 设备认证
- `data`: 数据上报
- `status`: 状态上报
- `command`: 命令下发
- `command_response`: 命令响应

## 8. 测试指南

### 8.1 单元测试

使用Django的测试框架或pytest进行单元测试:

```bash
# 运行所有测试
python manage.py test

# 运行特定应用的测试
python manage.py test iot_devices

# 运行特定测试
python manage.py test iot_devices.tests.test_models
```

关键测试文件:
- `accounts/tests/`: 用户认证测试
- `iot_devices/tests/`: 设备管理测试
- `mqtt_client/tests/`: MQTT功能测试
- `strategy_engine/tests/`: 策略引擎测试

### 8.2 设备模拟器

NovaCloud包含设备模拟器用于测试和演示:

- `mqtt_client/device_simulator.py`: MQTT设备模拟器
- `tcp_server/tcp_simulator.py`: TCP设备模拟器

启动MQTT设备模拟器:
```bash
python -m mqtt_client.device_simulator --device DEV-123456 --key device_key_here
```

### 8.3 API测试

使用Postman或curl测试API端点:

```bash
# 获取认证令牌
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin", "password":"password"}'

# 使用令牌获取项目列表
curl -X GET http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer {token}"
```

## 9. 前端开发

### 9.1 模板结构

- `templates/base.html`: 基础模板
- `templates/accounts/`: 账户相关模板
- `templates/core/`: 核心应用模板
- `templates/iot_devices/`: 设备管理模板
- `templates/strategy_engine/`: 策略引擎模板

### 9.2 静态资源

- `static/css/style.css`: 主样式表
- `static/js/`: JavaScript文件
- `static/img/`: 图片资源

### 9.3 JavaScript功能

主要JS文件和功能:
- `static/js/charts.js`: 数据可视化图表
- `static/js/device-control.js`: 设备控制
- `static/js/sensor-data.js`: 传感器数据处理

数据可视化示例:
```javascript
// 创建传感器数据图表
function createSensorChart(canvasId, data, options) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.timestamps,
            datasets: [{
                label: options.label,
                data: data.values,
                borderColor: options.color || 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: options.beginAtZero || false,
                    title: {
                        display: true,
                        text: options.unit
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                }
            }
        }
    });
}
```

## 10. 扩展与集成

### 10.1 添加新应用

步骤:
1. 创建新的Django应用: `python manage.py startapp new_app`
2. 在`DjangoNovaCloud/settings.py`的`INSTALLED_APPS`中添加应用
3. 定义模型、视图和URL
4. 创建迁移并应用: `python manage.py makemigrations new_app && python manage.py migrate`
5. 添加测试: `new_app/tests.py`

### 10.2 支持新设备协议

步骤:
1. 在`DjangoNovaCloud/settings.py`中定义新协议配置
2. 创建协议处理模块: `new_protocol/`
3. 实现协议解析器和处理程序
4. 更新设备模型以支持新协议
5. 添加新协议的设备模拟器

### 10.3 第三方服务集成

常见集成:
- **通知服务**: 邮件、SMS、Push通知
- **云存储**: Amazon S3、Google Cloud Storage
- **数据分析**: InfluxDB、Grafana
- **监控**: Prometheus、Sentry

集成示例(添加邮件通知):
1. 配置邮件设置(`.env`):
   ```
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.example.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your_email@example.com
   EMAIL_HOST_PASSWORD=your_password
   ```

2. 创建通知服务(`notifications/services.py`):
   ```python
   from django.core.mail import send_mail
   
   def send_alert_email(recipient, subject, message):
       """发送警报邮件"""
       send_mail(
           subject=subject,
           message=message,
           from_email=None,  # 使用默认发件人
           recipient_list=[recipient],
           fail_silently=False,
       )
   ```

3. 在策略引擎中使用:
   ```python
   from notifications.services import send_alert_email
   
   def execute_email_action(action, context):
       """执行邮件通知动作"""
       config = json.loads(action.config)
       recipient = config.get('recipient')
       subject = config.get('subject', '设备警报')
       message = config.get('message', '').format(**context)
       send_alert_email(recipient, subject, message)
   ```

## 11. 常见问题与解决方案

### 11.1 开发常见问题

1. **数据库迁移冲突**
   - 问题: 合并分支时出现迁移冲突
   - 解决: 使用`python manage.py makemigrations --merge`合并迁移

2. **静态文件不加载**
   - 问题: 开发服务器找不到静态文件
   - 解决: 检查`settings.py`中的`STATIC_URL`和`STATICFILES_DIRS`配置

3. **MQTT连接失败**
   - 问题: 无法连接到MQTT Broker
   - 解决: 检查Broker地址和端口，确认防火墙设置

### 11.2 生产环境常见问题

1. **服务器内存使用过高**
   - 问题: 应用服务器内存泄漏
   - 解决: 调整Gunicorn worker配置，添加`max_requests`参数

2. **数据库性能下降**
   - 问题: 随着数据增长，查询变慢
   - 解决: 添加适当的索引，优化查询，实现数据归档

3. **设备连接数爆炸**
   - 问题: 大量设备同时连接导致服务崩溃
   - 解决: 实现设备连接限流，增加MQTT/TCP服务器实例

## 12. 版本控制与发布流程

### 12.1 分支策略

- `main`: 稳定的生产分支
- `develop`: 开发分支，合并所有功能分支
- `feature/*`: 功能开发分支
- `hotfix/*`: 热修复分支
- `release/*`: 发布准备分支

### 12.2 版本命名

采用语义化版本命名: `主版本.次版本.修订号`
- 主版本: 不兼容的API变更
- 次版本: 向后兼容的功能新增
- 修订号: 向后兼容的问题修复

### 12.3 发布流程

1. 从`develop`分支创建`release/x.y.z`分支
2. 在发布分支上进行最终测试和修复
3. 完成后，将发布分支合并到`main`和`develop`
4. 在`main`分支上打标签`vX.Y.Z`
5. 部署到生产环境

## 13. 文档维护

### 13.1 代码文档

使用Sphinx生成代码文档:

```bash
# 安装Sphinx
pip install sphinx sphinx_rtd_theme

# 初始化Sphinx
sphinx-quickstart docs

# 生成API文档
sphinx-apidoc -o docs/source .

# 构建文档
cd docs
make html
```

### 13.2 API文档

使用drf-yasg生成Swagger/OpenAPI文档:

```bash
# 安装drf-yasg
pip install drf-yasg

# 添加到INSTALLED_APPS
# 'drf_yasg',

# 添加URL配置
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="NovaCloud API",
      default_version='v1',
      description="NovaCloud IoT Platform API",
   ),
   public=True,
   permission_classes=(permissions.IsAuthenticated,),
)

urlpatterns = [
   path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
```

### 13.3 用户文档

用户文档位于`docs/`目录下:
- `user_manual.md`: 用户手册
- `device_connection_guide.md`: 设备接入指南
- `deployment_guide.md`: 部署指南

## 14. 贡献指南

### 14.1 提交Pull Request

1. Fork项目仓库
2. 创建功能分支: `git checkout -b feature/your-feature`
3. 编写代码和测试
4. 提交更改: `git commit -am 'Add some feature'`
5. 推送到分支: `git push origin feature/your-feature`
6. 提交PR到`develop`分支

### 14.2 代码审查标准

- 遵循代码规范
- 包含单元测试
- 更新相关文档
- 通过持续集成检查
- 代码变更逻辑清晰

### 14.3 报告问题

报告Bug时请包含:
- 问题描述和复现步骤
- 预期行为和实际行为
- 环境信息(操作系统、Python版本等)
- 相关日志和截图

## 15. 学习资源

### 15.1 推荐阅读

- [Django官方文档](https://docs.djangoproject.com/)
- [Django REST Framework文档](https://www.django-rest-framework.org/)
- [MQTT协议规范](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
- [Python编程风格指南(PEP 8)](https://www.python.org/dev/peps/pep-0008/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)

### 15.2 社区资源

- Django社区: [Django Forum](https://forum.djangoproject.com/)
- MQTT社区: [MQTT Community](https://mqtt.org/community/)
- Python社区: [Python Forum](https://discuss.python.org/)

## 16. 附录

### 16.1 Git钩子配置

创建`.git/hooks/pre-commit`脚本自动检查代码质量:

```bash
#!/bin/sh
# 运行代码格式检查
flake8 .
if [ $? -ne 0 ]; then
    echo "代码格式检查失败。请运行 'black .' 格式化代码后再提交。"
    exit 1
fi

# 运行测试
python manage.py test
if [ $? -ne 0 ]; then
    echo "测试失败，请修复测试后再提交。"
    exit 1
fi

exit 0
```

添加执行权限:
```bash
chmod +x .git/hooks/pre-commit
```

### 16.2 常用开发命令速查表

数据库操作:
```bash
# 创建迁移
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 导出数据
python manage.py dumpdata app_name > data.json

# 导入数据
python manage.py loaddata data.json
```

Django管理:
```bash
# 创建超级用户
python manage.py createsuperuser

# 列出URL
python manage.py show_urls

# 启动shell
python manage.py shell

# 收集静态文件
python manage.py collectstatic
```

优化启动:
```bash
# 使用debugpy进行远程调试
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client manage.py runserver 0.0.0.0:8000
``` 

## 1. 技术架构概述

NovaCloud平台采用现代化的Web应用架构，以下是核心技术栈：

### 前端技术
- **HTML5/CSS3**: 构建现代化用户界面
- **JavaScript**: 原生JS用于前端交互
- **Chart.js**: 用于数据可视化和图表展示

### 后端技术
- **Python 3.12.3+**: 主要编程语言
- **Django 5.2.1+**: Web应用框架
- **Django REST Framework**: 用于构建API接口
- **SQLite**: 开发环境数据库
- **PostgreSQL**: 推荐的生产环境数据库
- **Redis**: 用于缓存和消息队列
- **MQTT**: 设备通信协议
- **TCP Socket**: 用于设备通信的替代协议

### 部署工具
- **Gunicorn/Daphne**: WSGI/ASGI服务器
- **Nginx**: Web服务器和反向代理
- **Docker** (可选): 容器化部署

## 2. 项目目录结构

NovaCloud平台的核心目录结构如下：

```
DjangoNovaCloud/           # 项目根目录
├── accounts/              # 用户账户管理应用
├── core/                  # 核心功能应用
├── DjangoNovaCloud/       # 项目配置目录
├── docs/                  # 文档目录
├── iot_devices/           # 物联网设备管理应用
├── mqtt_client/           # MQTT客户端实现
├── static/                # 静态资源
├── strategy_engine/       # 策略引擎应用
├── tcp_server/            # TCP服务器实现
├── templates/             # HTML模板
├── .env                   # 环境变量配置(不包含在版本控制中)
├── .gitignore             # Git忽略配置
├── manage.py              # Django管理脚本
└── requirements.txt       # 项目依赖
```

## 3. 开发环境搭建

### 3.1 前置条件

- Python 3.12.3 或更高版本
- pip (Python包管理器)
- Git
- 开发IDE (推荐PyCharm或VSCode)
- (可选) Docker 和 Docker Compose

### 3.2 克隆代码库并设置虚拟环境

```bash
# 克隆代码库
git clone [repository_url] DjangoNovaCloud
cd DjangoNovaCloud

# 创建并激活虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 3.3 配置开发环境

创建`.env`文件(开发环境配置)：

```
# Django设置
DEBUG=True
SECRET_KEY=your_dev_secret_key_here
ALLOWED_HOSTS=127.0.0.1,localhost

# 数据库设置 - 开发环境使用SQLite
# DATABASE_URL=sqlite:///db.sqlite3

# MQTT设置(使用公共MQTT服务器进行测试)
MQTT_BROKER_HOST=broker.emqx.io
MQTT_BROKER_PORT=1883
MQTT_BROKER_PORT_TLS=8883
MQTT_USE_TLS=False
```

### 3.4 初始化数据库

```bash
# 应用数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

### 3.5 启动开发服务器

```bash
python manage.py runserver
```

访问 http://127.0.0.1:8000/ 查看运行中的应用。

## 4. 代码规范

### 4.1 Python代码规范

NovaCloud遵循PEP 8规范，主要约定包括：

- 使用4个空格进行缩进
- 每行最大长度为79个字符
- 使用下划线命名法(snake_case)命名变量和函数
- 使用驼峰命名法(CamelCase)命名类
- 使用双引号表示字符串
- 导入顺序：标准库 > 第三方库 > 本地应用

推荐使用以下工具保证代码质量：
- **flake8**: 代码风格检查
- **black**: 自动代码格式化
- **isort**: 导入语句排序
- **mypy**: 类型检查

```bash
# 安装开发工具
pip install flake8 black isort mypy

# 运行代码检查
flake8 .

# 自动格式化代码
black .
isort .
```

### 4.2 Django最佳实践

- 使用Django的ORM，避免原生SQL(除非必要)
- 优先使用基于类的视图(Class-Based Views)
- 使用Django的表单系统进行数据验证
- 使用Django的中间件系统进行横切关注点处理
- 遵循DRY(Don't Repeat Yourself)原则
- 保持视图(views)简洁，将业务逻辑放在模型方法或专用服务中

### 4.3 前端代码规范

- HTML/CSS遵循语义化原则
- 使用4个空格缩进
- 为功能完整的JS代码添加JSDoc注释
- 使用camelCase命名JS变量和函数
- 使用kebab-case命名CSS类

## 5. 核心模块详解

### 5.1 用户认证系统(accounts)

主要文件:
- `accounts/forms.py`: 包含用户注册和登录表单
- `accounts/views.py`: 包含认证相关视图
- `accounts/urls.py`: 定义认证相关URL

关键功能:
- 用户注册、登录、登出
- 支持用户名或邮箱登录
- 密码重置(开发中)

扩展建议:
- 添加社交媒体登录
- 实现多因素认证
- 添加用户资料管理

### 5.2 物联网设备管理(iot_devices)

主要文件:
- `iot_devices/models.py`: 定义项目、设备、传感器和执行器模型
- `iot_devices/views.py`: 设备管理视图
- `iot_devices/forms.py`: 设备相关表单

关键对象:
- **Project**: 最高级别的组织单元，包含多个设备
- **Device**: 表示一个物理设备，具有唯一标识和认证密钥
- **Sensor**: 设备上的传感器组件
- **Actuator**: 设备上的执行器组件

重要方法:
- `Device.save()`: 重写以确保自动生成设备密钥
- `SensorData.get_latest_data()`: 获取传感器最新数据

扩展建议:
- 添加设备分组功能
- 实现设备固件更新机制
- 添加设备健康监控

### 5.3 MQTT客户端(mqtt_client)

主要文件:
- `mqtt_client/mqtt.py`: MQTT客户端单例实现
- `mqtt_client/apps.py`: 应用配置(启动时连接MQTT)

关键功能:
- 管理MQTT连接
- 处理设备上报数据
- 发送命令到设备

重要方法:
- `MQTTClient.connect()`: 连接到MQTT代理服务器
- `MQTTClient.on_message()`: 处理接收到的MQTT消息
- `MQTTClient.publish_command()`: 向设备发送命令

扩展建议:
- 添加消息重试机制
- 实现QoS级别配置
- 增强连接故障恢复

### 5.4 TCP服务器(tcp_server)

主要文件:
- `tcp_server/tcp_server.py`: TCP服务器实现
- `tcp_server/apps.py`: 应用配置(启动时启动TCP服务器)

关键功能:
- 监听TCP连接
- 处理设备认证
- 接收设备数据和发送命令

关键类:
- `TCPServer`: 服务器主类
- `ClientHandler`: 处理单个客户端连接

扩展建议:
- 添加更多协议解析器
- 实现TLS/SSL支持
- 添加连接限流机制

### 5.5 策略引擎(strategy_engine)

主要文件:
- `strategy_engine/models.py`: 策略相关模型
- `strategy_engine/evaluator.py`: 条件评估器
- `strategy_engine/executor.py`: 动作执行器

关键对象:
- **Strategy**: 自动化策略定义
- **Condition**: 触发条件
- **Action**: 执行的动作
- **ExecutionLog**: 策略执行日志

工作流程:
1. 数据更新时触发条件评估
2. 满足条件时执行相应动作
3. 记录执行结果

扩展建议:
- 添加更多条件类型(时间条件、复合条件)
- 实现更多动作类型(HTTP回调、SMS通知)
- 添加策略调度和优先级

## 6. 数据库设计

### 6.1 ER图

```
Project(1) --< Device(n)
Device(1) --< Sensor(n)
Device(1) --< Actuator(n)
Sensor(1) --< SensorData(n)
Actuator(1) --< ActuatorCommand(n)
```

### 6.2 主要模型字段

**Project**:
- project_id: CharField (唯一标识符)
- name: CharField
- description: TextField
- owner: ForeignKey(User)
- created_at/updated_at: DateTimeField

**Device**:
- device_id: CharField (唯一标识符)
- device_identifier: CharField (物理标识)
- device_key: CharField (自动生成的认证密钥)
- name: CharField
- project: ForeignKey(Project)
- status: CharField (在线状态)

**Sensor**:
- name: CharField
- sensor_type: CharField
- unit: CharField
- device: ForeignKey(Device)
- value_key: CharField (数据键名)

**Actuator**:
- name: CharField
- actuator_type: CharField
- device: ForeignKey(Device)
- command_key: CharField (命令键名)
- current_state: CharField

## 7. API接口文档

### 7.1 REST API

设备数据API:
- `GET /api/sensors/{sensor_id}/data/`: 获取传感器数据
- `POST /api/sensors/{sensor_id}/data/`: 添加传感器数据
- `GET /api/actuators/{actuator_id}/commands/`: 获取执行器命令历史
- `POST /api/actuators/{actuator_id}/command/`: 向执行器发送命令

设备管理API:
- `GET /api/projects/`: 获取项目列表
- `GET /api/projects/{project_id}/`: 获取项目详情
- `GET /api/projects/{project_id}/devices/`: 获取项目的设备列表
- `GET /api/devices/{device_id}/`: 获取设备详情

认证API:
- `POST /api/auth/token/`: 获取访问令牌
- `POST /api/auth/token/refresh/`: 刷新访问令牌

### 7.2 MQTT主题

数据上报:
- `novacloud/devices/{device_id}/data`: 设备数据上报
- `novacloud/devices/{device_id}/status`: 设备状态上报

命令下发:
- `novacloud/devices/{device_id}/command`: 平台发送命令
- `novacloud/devices/{device_id}/config`: 设备配置下发

### 7.3 TCP协议

消息格式: JSON
分隔符: 换行符(\n)

消息类型:
- `auth`: 设备认证
- `data`: 数据上报
- `status`: 状态上报
- `command`: 命令下发
- `command_response`: 命令响应

## 8. 测试指南

### 8.1 单元测试

使用Django的测试框架或pytest进行单元测试:

```bash
# 运行所有测试
python manage.py test

# 运行特定应用的测试
python manage.py test iot_devices

# 运行特定测试
python manage.py test iot_devices.tests.test_models
```

关键测试文件:
- `accounts/tests/`: 用户认证测试
- `iot_devices/tests/`: 设备管理测试
- `mqtt_client/tests/`: MQTT功能测试
- `strategy_engine/tests/`: 策略引擎测试

### 8.2 设备模拟器

NovaCloud包含设备模拟器用于测试和演示:

- `mqtt_client/device_simulator.py`: MQTT设备模拟器
- `tcp_server/tcp_simulator.py`: TCP设备模拟器

启动MQTT设备模拟器:
```bash
python -m mqtt_client.device_simulator --device DEV-123456 --key device_key_here
```

### 8.3 API测试

使用Postman或curl测试API端点:

```bash
# 获取认证令牌
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin", "password":"password"}'

# 使用令牌获取项目列表
curl -X GET http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer {token}"
```

## 9. 前端开发

### 9.1 模板结构

- `templates/base.html`: 基础模板
- `templates/accounts/`: 账户相关模板
- `templates/core/`: 核心应用模板
- `templates/iot_devices/`: 设备管理模板
- `templates/strategy_engine/`: 策略引擎模板

### 9.2 静态资源

- `static/css/style.css`: 主样式表
- `static/js/`: JavaScript文件
- `static/img/`: 图片资源

### 9.3 JavaScript功能

主要JS文件和功能:
- `static/js/charts.js`: 数据可视化图表
- `static/js/device-control.js`: 设备控制
- `static/js/sensor-data.js`: 传感器数据处理

数据可视化示例:
```javascript
// 创建传感器数据图表
function createSensorChart(canvasId, data, options) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.timestamps,
            datasets: [{
                label: options.label,
                data: data.values,
                borderColor: options.color || 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: options.beginAtZero || false,
                    title: {
                        display: true,
                        text: options.unit
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                }
            }
        }
    });
}
```

## 10. 扩展与集成

### 10.1 添加新应用

步骤:
1. 创建新的Django应用: `python manage.py startapp new_app`
2. 在`DjangoNovaCloud/settings.py`的`INSTALLED_APPS`中添加应用
3. 定义模型、视图和URL
4. 创建迁移并应用: `python manage.py makemigrations new_app && python manage.py migrate`
5. 添加测试: `new_app/tests.py`

### 10.2 支持新设备协议

步骤:
1. 在`DjangoNovaCloud/settings.py`中定义新协议配置
2. 创建协议处理模块: `new_protocol/`
3. 实现协议解析器和处理程序
4. 更新设备模型以支持新协议
5. 添加新协议的设备模拟器

### 10.3 第三方服务集成

常见集成:
- **通知服务**: 邮件、SMS、Push通知
- **云存储**: Amazon S3、Google Cloud Storage
- **数据分析**: InfluxDB、Grafana
- **监控**: Prometheus、Sentry

集成示例(添加邮件通知):
1. 配置邮件设置(`.env`):
   ```
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.example.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your_email@example.com
   EMAIL_HOST_PASSWORD=your_password
   ```

2. 创建通知服务(`notifications/services.py`):
   ```python
   from django.core.mail import send_mail
   
   def send_alert_email(recipient, subject, message):
       """发送警报邮件"""
       send_mail(
           subject=subject,
           message=message,
           from_email=None,  # 使用默认发件人
           recipient_list=[recipient],
           fail_silently=False,
       )
   ```

3. 在策略引擎中使用:
   ```python
   from notifications.services import send_alert_email
   
   def execute_email_action(action, context):
       """执行邮件通知动作"""
       config = json.loads(action.config)
       recipient = config.get('recipient')
       subject = config.get('subject', '设备警报')
       message = config.get('message', '').format(**context)
       send_alert_email(recipient, subject, message)
   ```

## 11. 常见问题与解决方案

### 11.1 开发常见问题

1. **数据库迁移冲突**
   - 问题: 合并分支时出现迁移冲突
   - 解决: 使用`python manage.py makemigrations --merge`合并迁移

2. **静态文件不加载**
   - 问题: 开发服务器找不到静态文件
   - 解决: 检查`settings.py`中的`STATIC_URL`和`STATICFILES_DIRS`配置

3. **MQTT连接失败**
   - 问题: 无法连接到MQTT Broker
   - 解决: 检查Broker地址和端口，确认防火墙设置

### 11.2 生产环境常见问题

1. **服务器内存使用过高**
   - 问题: 应用服务器内存泄漏
   - 解决: 调整Gunicorn worker配置，添加`max_requests`参数

2. **数据库性能下降**
   - 问题: 随着数据增长，查询变慢
   - 解决: 添加适当的索引，优化查询，实现数据归档

3. **设备连接数爆炸**
   - 问题: 大量设备同时连接导致服务崩溃
   - 解决: 实现设备连接限流，增加MQTT/TCP服务器实例

## 12. 版本控制与发布流程

### 12.1 分支策略

- `main`: 稳定的生产分支
- `develop`: 开发分支，合并所有功能分支
- `feature/*`: 功能开发分支
- `hotfix/*`: 热修复分支
- `release/*`: 发布准备分支

### 12.2 版本命名

采用语义化版本命名: `主版本.次版本.修订号`
- 主版本: 不兼容的API变更
- 次版本: 向后兼容的功能新增
- 修订号: 向后兼容的问题修复

### 12.3 发布流程

1. 从`develop`分支创建`release/x.y.z`分支
2. 在发布分支上进行最终测试和修复
3. 完成后，将发布分支合并到`main`和`develop`
4. 在`main`分支上打标签`vX.Y.Z`
5. 部署到生产环境

## 13. 文档维护

### 13.1 代码文档

使用Sphinx生成代码文档:

```bash
# 安装Sphinx
pip install sphinx sphinx_rtd_theme

# 初始化Sphinx
sphinx-quickstart docs

# 生成API文档
sphinx-apidoc -o docs/source .

# 构建文档
cd docs
make html
```

### 13.2 API文档

使用drf-yasg生成Swagger/OpenAPI文档:

```bash
# 安装drf-yasg
pip install drf-yasg

# 添加到INSTALLED_APPS
# 'drf_yasg',

# 添加URL配置
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="NovaCloud API",
      default_version='v1',
      description="NovaCloud IoT Platform API",
   ),
   public=True,
   permission_classes=(permissions.IsAuthenticated,),
)

urlpatterns = [
   path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
```

### 13.3 用户文档

用户文档位于`docs/`目录下:
- `user_manual.md`: 用户手册
- `device_connection_guide.md`: 设备接入指南
- `deployment_guide.md`: 部署指南

## 14. 贡献指南

### 14.1 提交Pull Request

1. Fork项目仓库
2. 创建功能分支: `git checkout -b feature/your-feature`
3. 编写代码和测试
4. 提交更改: `git commit -am 'Add some feature'`
5. 推送到分支: `git push origin feature/your-feature`
6. 提交PR到`develop`分支

### 14.2 代码审查标准

- 遵循代码规范
- 包含单元测试
- 更新相关文档
- 通过持续集成检查
- 代码变更逻辑清晰

### 14.3 报告问题

报告Bug时请包含:
- 问题描述和复现步骤
- 预期行为和实际行为
- 环境信息(操作系统、Python版本等)
- 相关日志和截图

## 15. 学习资源

### 15.1 推荐阅读

- [Django官方文档](https://docs.djangoproject.com/)
- [Django REST Framework文档](https://www.django-rest-framework.org/)
- [MQTT协议规范](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
- [Python编程风格指南(PEP 8)](https://www.python.org/dev/peps/pep-0008/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)

### 15.2 社区资源

- Django社区: [Django Forum](https://forum.djangoproject.com/)
- MQTT社区: [MQTT Community](https://mqtt.org/community/)
- Python社区: [Python Forum](https://discuss.python.org/)

## 16. 附录

### 16.1 Git钩子配置

创建`.git/hooks/pre-commit`脚本自动检查代码质量:

```bash
#!/bin/sh
# 运行代码格式检查
flake8 .
if [ $? -ne 0 ]; then
    echo "代码格式检查失败。请运行 'black .' 格式化代码后再提交。"
    exit 1
fi

# 运行测试
python manage.py test
if [ $? -ne 0 ]; then
    echo "测试失败，请修复测试后再提交。"
    exit 1
fi

exit 0
```

添加执行权限:
```bash
chmod +x .git/hooks/pre-commit
```

### 16.2 常用开发命令速查表

数据库操作:
```bash
# 创建迁移
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 导出数据
python manage.py dumpdata app_name > data.json

# 导入数据
python manage.py loaddata data.json
```

Django管理:
```bash
# 创建超级用户
python manage.py createsuperuser

# 列出URL
python manage.py show_urls

# 启动shell
python manage.py shell

# 收集静态文件
python manage.py collectstatic
```

优化启动:
```bash
# 使用debugpy进行远程调试
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client manage.py runserver 0.0.0.0:8000
``` 
 