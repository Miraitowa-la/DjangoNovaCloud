# NovaCloud平台安全指南

## 一、代码级安全审查与加固

### 1.1 输入验证强化

所有用户输入必须经过严格验证，以防范XSS、SQL注入、命令注入等攻击。以下是关键实现建议：

#### 表单验证

在`iot_devices/forms.py`中的`ProjectForm`和`DeviceForm`添加自定义验证器：

```python
# ProjectForm 中添加
def clean_name(self):
    name = self.cleaned_data.get('name')
    # 防止XSS攻击，检查名称中是否包含脚本标签
    if '<script>' in name.lower() or '</script>' in name.lower():
        raise forms.ValidationError('项目名称不能包含脚本标签')
    return name

def clean_project_id(self):
    project_id = self.cleaned_data.get('project_id')
    # 确保项目ID只包含字母、数字和连字符
    import re
    if not re.match(r'^[A-Za-z0-9\-]+$', project_id):
        raise forms.ValidationError('项目ID只能包含字母、数字和连字符')
    return project_id
```

```python
# DeviceForm 中添加
def clean_device_identifier(self):
    device_identifier = self.cleaned_data.get('device_identifier')
    # MAC地址格式验证 (XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX)
    import re
    if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', device_identifier) and not re.match(r'^[A-Za-z0-9\-]+$', device_identifier):
        raise forms.ValidationError('设备标识格式无效，请使用MAC地址或有效的设备序列号格式')
    return device_identifier
```

#### API数据验证 (DRF Serializer)

在使用Django REST Framework处理API请求时，确保在Serializer中进行严格的数据验证：

```python
# 在 iot_devices/serializers.py 中
class SensorDataSerializer(serializers.ModelSerializer):
    value = serializers.FloatField(required=False)  # 可能是浮点数
    value_string = serializers.CharField(required=False, max_length=100)  # 字符串值有长度限制
    
    class Meta:
        model = SensorData
        fields = ['sensor', 'value', 'value_string', 'value_boolean', 'timestamp']
    
    def validate(self, data):
        # 确保至少提供了一种值类型
        if not any(k in data for k in ['value', 'value_string', 'value_boolean']):
            raise serializers.ValidationError("必须提供value, value_string或value_boolean中的至少一个")
            
        # 如果是字符串值，进行额外清理防止XSS
        if 'value_string' in data:
            import bleach
            data['value_string'] = bleach.clean(data['value_string'])
            
        return data
```

### 1.2 ORM 使用安全

Django ORM 是防SQL注入的有力工具，因为它会自动转义参数。以下是使用ORM的安全注意事项：

- **始终使用ORM方法**：如`filter()`, `get()`, `exclude()`等，避免原生SQL。
- **避免使用`extra()`和`raw()`**：这些方法可能导致SQL注入风险。如果必须使用，确保所有参数都经过严格验证。
- **使用参数化查询**：如果必须执行原生SQL，使用参数化查询并让Django处理参数转义。

```python
# 不安全的方式
User.objects.raw(f"SELECT * FROM auth_user WHERE username = '{username}'")  # 危险！

# 安全的方式
User.objects.raw("SELECT * FROM auth_user WHERE username = %s", [username])  # 参数化，安全
```

### 1.3 CSRF 保护

确保所有修改数据的表单和AJAX请求都包含CSRF令牌：

#### 在模板表单中

```html
<form method="post" action="{% url 'update_device' %}">
    {% csrf_token %}
    <!-- 表单字段 -->
    <button type="submit">更新</button>
</form>
```

#### 在AJAX请求中

```javascript
// 获取CSRF令牌
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// 在AJAX请求中包含令牌
fetch('/api/devices/control/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
        device_id: 'DEV-123456',
        command: 'reboot'
    })
});
```

### 1.4 点击劫持防护

在`settings.py`中启用点击劫持保护：

```python
# 在settings.py中
X_FRAME_OPTIONS = 'DENY'  # 禁止在任何iframe中嵌入
# 或
X_FRAME_OPTIONS = 'SAMEORIGIN'  # 仅允许同源iframe嵌入
```

### 1.5 密码策略与管理

增强用户密码策略，在`settings.py`中配置密码验证器：

```python
# 在settings.py中
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ['username', 'email'],
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    # 可以添加自定义验证器，要求密码包含特殊字符等
]
```

对于首次登录强制修改密码，可以实现以下逻辑：

```python
# 在UserProfile模型中添加字段
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    password_changed = models.BooleanField(default=False)  # 标记是否修改过默认密码

# 在视图中检查并重定向
def some_protected_view(request):
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if not profile.password_changed:
            messages.warning(request, '首次登录请修改密码')
            return redirect('accounts:change_password')
    # 正常视图逻辑...
```

### 1.6 会话管理安全

增强会话安全性，在`settings.py`中进行配置：

```python
# 在settings.py中
# 在生产环境强制使用HTTPS
SESSION_COOKIE_SECURE = True  

# 防止JavaScript访问cookie
SESSION_COOKIE_HTTPONLY = True  

# 会话在浏览器关闭时结束
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  

# 或设置会话过期时间（单位为秒，例如2小时）
# SESSION_COOKIE_AGE = 7200  

# 防止CSRF攻击
SESSION_COOKIE_SAMESITE = 'Lax'  # 或 'Strict'（更严格但可能影响用户体验）
```

## 二、敏感信息处理与存储安全

### 2.1 设备密钥 (Device.device_key) 安全

设备密钥是访问系统的重要凭证，需要特别保护：

#### 当前机制

目前使用`uuid.uuid4().hex`生成设备密钥，存储在数据库的`CharField`中。尽管只有管理员可见，但仍以明文形式存储。

#### 安全建议

考虑到设备端需要使用原始密钥进行连接，最佳实践如下：

1. **仅创建时显示一次**：
   - 当设备被创建时，将生成的密钥显示给用户一次。
   - 提醒用户保存此密钥，因为之后将无法再次完整查看。

2. **存储密钥哈希值**：
   - 在数据库中仅存储密钥的哈希值（使用单向哈希函数，如SHA-256）。
   - 添加随机盐值增强安全性。

3. **验证流程**：
   - 设备使用原始密钥连接。
   - 服务器计算收到的密钥的哈希值并与存储的哈希值比较。

实现示例：

```python
# 修改Device模型
class Device(models.Model):
    # ...其他字段...
    device_key_hash = models.CharField('设备密钥哈希', max_length=128)
    device_key_salt = models.CharField('设备密钥盐值', max_length=32)
    
    def save(self, *args, **kwargs):
        """保存前处理设备密钥"""
        # 如果是新创建的设备或需要重置密钥
        if not self.pk or hasattr(self, '_reset_key') and self._reset_key:
            # 生成新密钥（这将是展示给用户的值）
            import secrets
            self.temp_device_key = secrets.token_hex(16)  # 临时存储，不保存到数据库
            
            # 生成盐值
            import os
            self.device_key_salt = os.urandom(16).hex()
            
            # 生成哈希值
            import hashlib
            hash_obj = hashlib.sha256((self.temp_device_key + self.device_key_salt).encode())
            self.device_key_hash = hash_obj.hexdigest()
            
            # 如果是重置密钥，清除标记
            if hasattr(self, '_reset_key'):
                del self._reset_key
        
        super().save(*args, **kwargs)
    
    def verify_key(self, provided_key):
        """验证提供的密钥是否正确"""
        import hashlib
        hash_obj = hashlib.sha256((provided_key + self.device_key_salt).encode())
        calculated_hash = hash_obj.hexdigest()
        return calculated_hash == self.device_key_hash
```

在视图中展示密钥：

```python
def create_device(request):
    # ... 设备创建逻辑 ...
    device = form.save()
    # 由于密钥只显示一次，需要在会话中传递给模板
    return render(request, 'device_created.html', {'device': device, 'device_key': device.temp_device_key})
```

### 2.2 平台API密钥/令牌管理

对于需要暴露给第三方应用的API，使用令牌认证：

```python
# 在settings.py中
INSTALLED_APPS = [
    # ...现有应用
    'rest_framework.authtoken',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        # ...其他认证类
    ],
}
```

创建并管理令牌的模型和视图：

```python
# 在一个专门的应用中，如api_auth/models.py
from django.db import models
from django.contrib.auth.models import User
import secrets

class APIToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_tokens')
    name = models.CharField('令牌名称', max_length=100)  # 用于识别令牌用途
    token_hash = models.CharField('令牌哈希', max_length=128)
    salt = models.CharField('盐值', max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # 可选的过期时间
    is_active = models.BooleanField(default=True)
    
    def generate_token(self):
        """生成新令牌"""
        import os
        raw_token = secrets.token_hex(32)
        self.salt = os.urandom(16).hex()
        
        import hashlib
        hash_obj = hashlib.sha256((raw_token + self.salt).encode())
        self.token_hash = hash_obj.hexdigest()
        
        return raw_token  # 返回明文令牌（仅此一次）
    
    def verify_token(self, provided_token):
        """验证令牌"""
        import hashlib
        hash_obj = hashlib.sha256((provided_token + self.salt).encode())
        calculated_hash = hash_obj.hexdigest()
        return calculated_hash == self.token_hash and self.is_active
```

### 2.3 配置文件安全 (settings.py)

使用环境变量存储敏感信息，而非硬编码在代码中。

#### 安装 python-dotenv

```bash
pip install python-dotenv
```

#### 创建 .env 文件

```
# .env
SECRET_KEY=your-very-secure-secret-key
DATABASE_URL=postgresql://user:password@localhost/dbname
MQTT_BROKER_HOST=mqtt.example.com
MQTT_USERNAME=mqttuser
MQTT_PASSWORD=mqttpassword
```

#### 将 .env 添加到 .gitignore

```
# .gitignore
.env
```

#### 修改 settings.py 使用环境变量

```python
# settings.py 顶部
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 使用环境变量
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-insecure-key-for-dev')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'novacloud'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# MQTT配置
MQTT_CONFIG = {
    'BROKER_HOST': os.getenv('MQTT_BROKER_HOST', 'broker.emqx.io'),
    'BROKER_PORT': int(os.getenv('MQTT_BROKER_PORT', '1883')),
    'BROKER_PORT_TLS': int(os.getenv('MQTT_BROKER_PORT_TLS', '8883')),
    'USE_TLS': os.getenv('MQTT_USE_TLS', 'False') == 'True',
    'USERNAME': os.getenv('MQTT_USERNAME', ''),
    'PASSWORD': os.getenv('MQTT_PASSWORD', ''),
    # ...其他配置
}
```

## 三、通信链路安全

### 3.1 HTTPS 强制

在生产环境中，必须使用HTTPS保护所有Web通信：

#### 在 settings.py 中配置

```python
# settings.py - 生产环境设置
# 强制重定向HTTP到HTTPS
SECURE_SSL_REDIRECT = True

# 当使用反向代理处理SSL时的设置
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 确保会话和CSRF cookie通过HTTPS发送
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS设置 - 告诉浏览器只通过HTTPS访问
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

#### Nginx配置HTTPS（示例）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;  # 重定向HTTP到HTTPS
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/fullchain.pem;  # Let's Encrypt证书
    ssl_certificate_key /path/to/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    
    # 应用静态文件
    location /static/ {
        alias /path/to/novacloud/static/;
    }
    
    # 代理到Django应用
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3.2 MQTT 通信安全

保护设备与平台间的MQTT通信：

#### MQTT Broker的TLS配置（以Mosquitto为例）

```
# /etc/mosquitto/mosquitto.conf
listener 1883 localhost  # 仅本地访问非加密端口
listener 8883
certfile /path/to/fullchain.pem
keyfile /path/to/privkey.pem
cafile /path/to/chain.pem
require_certificate false  # 是否要求客户端证书
```

#### 设备认证与ACL配置

```
# mosquitto密码文件设置
password_file /etc/mosquitto/passwd

# ACL配置
acl_file /etc/mosquitto/acl
```

ACL文件示例：

```
# 用户规则 - device_id作为username
user device_DEV-123456
topic read novacloud/devices/DEV-123456/command
topic read novacloud/devices/DEV-123456/config
topic write novacloud/devices/DEV-123456/data
topic write novacloud/devices/DEV-123456/status

# 平台规则 - 平台服务使用特定用户
user novacloud_platform
topic readwrite novacloud/#
```

### 3.3 TCP/Modbus 通信安全

对于TCP和Modbus等固有不安全的协议，建议采取以下缓解措施：

1. **部署在受信任网络**：将TCP服务器部署在防火墙保护的内部网络中。

2. **使用VPN**：设备和平台间通过VPN建立安全隧道。

3. **实现自定义加密**：
   - 在应用层实现数据加密和完整性检查。
   - 使用预共享密钥对传输数据进行对称加密。

4. **网络分段**：将IoT设备网络与核心业务网络分离。

5. **严格的防火墙规则**：仅允许必要的IP地址和端口访问TCP服务器。

## 四、依赖库安全管理

### 定期检查依赖库漏洞

使用`pip-audit`或`safety`工具检查依赖库的已知漏洞：

```bash
# 安装工具
pip install pip-audit

# 检查已安装的依赖
pip-audit

# 或检查requirements.txt
pip-audit -r requirements.txt
```

### 将漏洞检查集成到CI/CD流程

在GitHub Actions或Jenkins等CI/CD流程中添加安全检查步骤：

```yaml
# GitHub Actions 示例
name: Security Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pip-audit
        pip install -r requirements.txt
    - name: Check for vulnerabilities
      run: pip-audit
```

## 五、日志记录与审计

### 配置详细的安全日志

在`settings.py`中配置详细的日志记录：

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message} {user} {ip}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'novacloud.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {  # 用户认证相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'iot_devices': {  # 设备操作相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'mqtt_client': {  # MQTT通信相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'strategy_engine': {  # 策略执行相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 记录关键安全事件

在关键视图和函数中添加安全日志记录：

```python
# 引入日志模块
import logging
logger = logging.getLogger('accounts')

# 在视图中记录登录尝试
def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            user = form.get_user()
            login(request, user)
            # 记录成功登录
            logger.info(
                f"用户登录成功: {username}",
                extra={
                    'user': username,
                    'ip': get_client_ip(request)
                }
            )
            return redirect('core:index')
        else:
            # 记录失败登录
            username = request.POST.get('username', '')
            logger.warning(
                f"用户登录失败: {username}",
                extra={
                    'user': username,
                    'ip': get_client_ip(request)
                }
            )
    # 视图其余部分...

# 辅助函数获取客户端IP
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

### 定期审计日志

建立日志审计制度和流程：

1. **定期审查**：安排每周或每月的日志审查。
2. **异常监控**：设置自动监控来发现异常模式（例如，短时间内多次失败的登录尝试）。
3. **保留策略**：制定日志保留策略，确定日志需要保留多长时间。
4. **安全备份**：确保关键安全日志有备份。 

## 一、代码级安全审查与加固

### 1.1 输入验证强化

所有用户输入必须经过严格验证，以防范XSS、SQL注入、命令注入等攻击。以下是关键实现建议：

#### 表单验证

在`iot_devices/forms.py`中的`ProjectForm`和`DeviceForm`添加自定义验证器：

```python
# ProjectForm 中添加
def clean_name(self):
    name = self.cleaned_data.get('name')
    # 防止XSS攻击，检查名称中是否包含脚本标签
    if '<script>' in name.lower() or '</script>' in name.lower():
        raise forms.ValidationError('项目名称不能包含脚本标签')
    return name

def clean_project_id(self):
    project_id = self.cleaned_data.get('project_id')
    # 确保项目ID只包含字母、数字和连字符
    import re
    if not re.match(r'^[A-Za-z0-9\-]+$', project_id):
        raise forms.ValidationError('项目ID只能包含字母、数字和连字符')
    return project_id
```

```python
# DeviceForm 中添加
def clean_device_identifier(self):
    device_identifier = self.cleaned_data.get('device_identifier')
    # MAC地址格式验证 (XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX)
    import re
    if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', device_identifier) and not re.match(r'^[A-Za-z0-9\-]+$', device_identifier):
        raise forms.ValidationError('设备标识格式无效，请使用MAC地址或有效的设备序列号格式')
    return device_identifier
```

#### API数据验证 (DRF Serializer)

在使用Django REST Framework处理API请求时，确保在Serializer中进行严格的数据验证：

```python
# 在 iot_devices/serializers.py 中
class SensorDataSerializer(serializers.ModelSerializer):
    value = serializers.FloatField(required=False)  # 可能是浮点数
    value_string = serializers.CharField(required=False, max_length=100)  # 字符串值有长度限制
    
    class Meta:
        model = SensorData
        fields = ['sensor', 'value', 'value_string', 'value_boolean', 'timestamp']
    
    def validate(self, data):
        # 确保至少提供了一种值类型
        if not any(k in data for k in ['value', 'value_string', 'value_boolean']):
            raise serializers.ValidationError("必须提供value, value_string或value_boolean中的至少一个")
            
        # 如果是字符串值，进行额外清理防止XSS
        if 'value_string' in data:
            import bleach
            data['value_string'] = bleach.clean(data['value_string'])
            
        return data
```

### 1.2 ORM 使用安全

Django ORM 是防SQL注入的有力工具，因为它会自动转义参数。以下是使用ORM的安全注意事项：

- **始终使用ORM方法**：如`filter()`, `get()`, `exclude()`等，避免原生SQL。
- **避免使用`extra()`和`raw()`**：这些方法可能导致SQL注入风险。如果必须使用，确保所有参数都经过严格验证。
- **使用参数化查询**：如果必须执行原生SQL，使用参数化查询并让Django处理参数转义。

```python
# 不安全的方式
User.objects.raw(f"SELECT * FROM auth_user WHERE username = '{username}'")  # 危险！

# 安全的方式
User.objects.raw("SELECT * FROM auth_user WHERE username = %s", [username])  # 参数化，安全
```

### 1.3 CSRF 保护

确保所有修改数据的表单和AJAX请求都包含CSRF令牌：

#### 在模板表单中

```html
<form method="post" action="{% url 'update_device' %}">
    {% csrf_token %}
    <!-- 表单字段 -->
    <button type="submit">更新</button>
</form>
```

#### 在AJAX请求中

```javascript
// 获取CSRF令牌
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// 在AJAX请求中包含令牌
fetch('/api/devices/control/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
        device_id: 'DEV-123456',
        command: 'reboot'
    })
});
```

### 1.4 点击劫持防护

在`settings.py`中启用点击劫持保护：

```python
# 在settings.py中
X_FRAME_OPTIONS = 'DENY'  # 禁止在任何iframe中嵌入
# 或
X_FRAME_OPTIONS = 'SAMEORIGIN'  # 仅允许同源iframe嵌入
```

### 1.5 密码策略与管理

增强用户密码策略，在`settings.py`中配置密码验证器：

```python
# 在settings.py中
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ['username', 'email'],
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    # 可以添加自定义验证器，要求密码包含特殊字符等
]
```

对于首次登录强制修改密码，可以实现以下逻辑：

```python
# 在UserProfile模型中添加字段
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    password_changed = models.BooleanField(default=False)  # 标记是否修改过默认密码

# 在视图中检查并重定向
def some_protected_view(request):
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if not profile.password_changed:
            messages.warning(request, '首次登录请修改密码')
            return redirect('accounts:change_password')
    # 正常视图逻辑...
```

### 1.6 会话管理安全

增强会话安全性，在`settings.py`中进行配置：

```python
# 在settings.py中
# 在生产环境强制使用HTTPS
SESSION_COOKIE_SECURE = True  

# 防止JavaScript访问cookie
SESSION_COOKIE_HTTPONLY = True  

# 会话在浏览器关闭时结束
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  

# 或设置会话过期时间（单位为秒，例如2小时）
# SESSION_COOKIE_AGE = 7200  

# 防止CSRF攻击
SESSION_COOKIE_SAMESITE = 'Lax'  # 或 'Strict'（更严格但可能影响用户体验）
```

## 二、敏感信息处理与存储安全

### 2.1 设备密钥 (Device.device_key) 安全

设备密钥是访问系统的重要凭证，需要特别保护：

#### 当前机制

目前使用`uuid.uuid4().hex`生成设备密钥，存储在数据库的`CharField`中。尽管只有管理员可见，但仍以明文形式存储。

#### 安全建议

考虑到设备端需要使用原始密钥进行连接，最佳实践如下：

1. **仅创建时显示一次**：
   - 当设备被创建时，将生成的密钥显示给用户一次。
   - 提醒用户保存此密钥，因为之后将无法再次完整查看。

2. **存储密钥哈希值**：
   - 在数据库中仅存储密钥的哈希值（使用单向哈希函数，如SHA-256）。
   - 添加随机盐值增强安全性。

3. **验证流程**：
   - 设备使用原始密钥连接。
   - 服务器计算收到的密钥的哈希值并与存储的哈希值比较。

实现示例：

```python
# 修改Device模型
class Device(models.Model):
    # ...其他字段...
    device_key_hash = models.CharField('设备密钥哈希', max_length=128)
    device_key_salt = models.CharField('设备密钥盐值', max_length=32)
    
    def save(self, *args, **kwargs):
        """保存前处理设备密钥"""
        # 如果是新创建的设备或需要重置密钥
        if not self.pk or hasattr(self, '_reset_key') and self._reset_key:
            # 生成新密钥（这将是展示给用户的值）
            import secrets
            self.temp_device_key = secrets.token_hex(16)  # 临时存储，不保存到数据库
            
            # 生成盐值
            import os
            self.device_key_salt = os.urandom(16).hex()
            
            # 生成哈希值
            import hashlib
            hash_obj = hashlib.sha256((self.temp_device_key + self.device_key_salt).encode())
            self.device_key_hash = hash_obj.hexdigest()
            
            # 如果是重置密钥，清除标记
            if hasattr(self, '_reset_key'):
                del self._reset_key
        
        super().save(*args, **kwargs)
    
    def verify_key(self, provided_key):
        """验证提供的密钥是否正确"""
        import hashlib
        hash_obj = hashlib.sha256((provided_key + self.device_key_salt).encode())
        calculated_hash = hash_obj.hexdigest()
        return calculated_hash == self.device_key_hash
```

在视图中展示密钥：

```python
def create_device(request):
    # ... 设备创建逻辑 ...
    device = form.save()
    # 由于密钥只显示一次，需要在会话中传递给模板
    return render(request, 'device_created.html', {'device': device, 'device_key': device.temp_device_key})
```

### 2.2 平台API密钥/令牌管理

对于需要暴露给第三方应用的API，使用令牌认证：

```python
# 在settings.py中
INSTALLED_APPS = [
    # ...现有应用
    'rest_framework.authtoken',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        # ...其他认证类
    ],
}
```

创建并管理令牌的模型和视图：

```python
# 在一个专门的应用中，如api_auth/models.py
from django.db import models
from django.contrib.auth.models import User
import secrets

class APIToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_tokens')
    name = models.CharField('令牌名称', max_length=100)  # 用于识别令牌用途
    token_hash = models.CharField('令牌哈希', max_length=128)
    salt = models.CharField('盐值', max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # 可选的过期时间
    is_active = models.BooleanField(default=True)
    
    def generate_token(self):
        """生成新令牌"""
        import os
        raw_token = secrets.token_hex(32)
        self.salt = os.urandom(16).hex()
        
        import hashlib
        hash_obj = hashlib.sha256((raw_token + self.salt).encode())
        self.token_hash = hash_obj.hexdigest()
        
        return raw_token  # 返回明文令牌（仅此一次）
    
    def verify_token(self, provided_token):
        """验证令牌"""
        import hashlib
        hash_obj = hashlib.sha256((provided_token + self.salt).encode())
        calculated_hash = hash_obj.hexdigest()
        return calculated_hash == self.token_hash and self.is_active
```

### 2.3 配置文件安全 (settings.py)

使用环境变量存储敏感信息，而非硬编码在代码中。

#### 安装 python-dotenv

```bash
pip install python-dotenv
```

#### 创建 .env 文件

```
# .env
SECRET_KEY=your-very-secure-secret-key
DATABASE_URL=postgresql://user:password@localhost/dbname
MQTT_BROKER_HOST=mqtt.example.com
MQTT_USERNAME=mqttuser
MQTT_PASSWORD=mqttpassword
```

#### 将 .env 添加到 .gitignore

```
# .gitignore
.env
```

#### 修改 settings.py 使用环境变量

```python
# settings.py 顶部
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 使用环境变量
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-insecure-key-for-dev')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'novacloud'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# MQTT配置
MQTT_CONFIG = {
    'BROKER_HOST': os.getenv('MQTT_BROKER_HOST', 'broker.emqx.io'),
    'BROKER_PORT': int(os.getenv('MQTT_BROKER_PORT', '1883')),
    'BROKER_PORT_TLS': int(os.getenv('MQTT_BROKER_PORT_TLS', '8883')),
    'USE_TLS': os.getenv('MQTT_USE_TLS', 'False') == 'True',
    'USERNAME': os.getenv('MQTT_USERNAME', ''),
    'PASSWORD': os.getenv('MQTT_PASSWORD', ''),
    # ...其他配置
}
```

## 三、通信链路安全

### 3.1 HTTPS 强制

在生产环境中，必须使用HTTPS保护所有Web通信：

#### 在 settings.py 中配置

```python
# settings.py - 生产环境设置
# 强制重定向HTTP到HTTPS
SECURE_SSL_REDIRECT = True

# 当使用反向代理处理SSL时的设置
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 确保会话和CSRF cookie通过HTTPS发送
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS设置 - 告诉浏览器只通过HTTPS访问
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

#### Nginx配置HTTPS（示例）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;  # 重定向HTTP到HTTPS
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/fullchain.pem;  # Let's Encrypt证书
    ssl_certificate_key /path/to/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    
    # 应用静态文件
    location /static/ {
        alias /path/to/novacloud/static/;
    }
    
    # 代理到Django应用
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3.2 MQTT 通信安全

保护设备与平台间的MQTT通信：

#### MQTT Broker的TLS配置（以Mosquitto为例）

```
# /etc/mosquitto/mosquitto.conf
listener 1883 localhost  # 仅本地访问非加密端口
listener 8883
certfile /path/to/fullchain.pem
keyfile /path/to/privkey.pem
cafile /path/to/chain.pem
require_certificate false  # 是否要求客户端证书
```

#### 设备认证与ACL配置

```
# mosquitto密码文件设置
password_file /etc/mosquitto/passwd

# ACL配置
acl_file /etc/mosquitto/acl
```

ACL文件示例：

```
# 用户规则 - device_id作为username
user device_DEV-123456
topic read novacloud/devices/DEV-123456/command
topic read novacloud/devices/DEV-123456/config
topic write novacloud/devices/DEV-123456/data
topic write novacloud/devices/DEV-123456/status

# 平台规则 - 平台服务使用特定用户
user novacloud_platform
topic readwrite novacloud/#
```

### 3.3 TCP/Modbus 通信安全

对于TCP和Modbus等固有不安全的协议，建议采取以下缓解措施：

1. **部署在受信任网络**：将TCP服务器部署在防火墙保护的内部网络中。

2. **使用VPN**：设备和平台间通过VPN建立安全隧道。

3. **实现自定义加密**：
   - 在应用层实现数据加密和完整性检查。
   - 使用预共享密钥对传输数据进行对称加密。

4. **网络分段**：将IoT设备网络与核心业务网络分离。

5. **严格的防火墙规则**：仅允许必要的IP地址和端口访问TCP服务器。

## 四、依赖库安全管理

### 定期检查依赖库漏洞

使用`pip-audit`或`safety`工具检查依赖库的已知漏洞：

```bash
# 安装工具
pip install pip-audit

# 检查已安装的依赖
pip-audit

# 或检查requirements.txt
pip-audit -r requirements.txt
```

### 将漏洞检查集成到CI/CD流程

在GitHub Actions或Jenkins等CI/CD流程中添加安全检查步骤：

```yaml
# GitHub Actions 示例
name: Security Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pip-audit
        pip install -r requirements.txt
    - name: Check for vulnerabilities
      run: pip-audit
```

## 五、日志记录与审计

### 配置详细的安全日志

在`settings.py`中配置详细的日志记录：

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message} {user} {ip}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'novacloud.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {  # 用户认证相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'iot_devices': {  # 设备操作相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'mqtt_client': {  # MQTT通信相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'strategy_engine': {  # 策略执行相关日志
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 记录关键安全事件

在关键视图和函数中添加安全日志记录：

```python
# 引入日志模块
import logging
logger = logging.getLogger('accounts')

# 在视图中记录登录尝试
def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            user = form.get_user()
            login(request, user)
            # 记录成功登录
            logger.info(
                f"用户登录成功: {username}",
                extra={
                    'user': username,
                    'ip': get_client_ip(request)
                }
            )
            return redirect('core:index')
        else:
            # 记录失败登录
            username = request.POST.get('username', '')
            logger.warning(
                f"用户登录失败: {username}",
                extra={
                    'user': username,
                    'ip': get_client_ip(request)
                }
            )
    # 视图其余部分...

# 辅助函数获取客户端IP
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

### 定期审计日志

建立日志审计制度和流程：

1. **定期审查**：安排每周或每月的日志审查。
2. **异常监控**：设置自动监控来发现异常模式（例如，短时间内多次失败的登录尝试）。
3. **保留策略**：制定日志保留策略，确定日志需要保留多长时间。
4. **安全备份**：确保关键安全日志有备份。 
 