# NovaCloud平台安全强化指南

## 1. 输入验证强化

为防范XSS、SQL注入、命令注入等攻击，需确保所有用户输入经过严格验证和清理。

### 1.1 表单验证增强

在`iot_devices/forms.py`中的`ProjectForm`添加自定义验证器：

```python
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

在`DeviceForm`中添加设备标识符验证：

```python
def clean_device_identifier(self):
    device_identifier = self.cleaned_data.get('device_identifier')
    # MAC地址格式验证 (XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX)
    import re
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    if not re.match(mac_pattern, device_identifier):
        # 如果不是MAC地址格式，检查是否为其他允许的格式（如UUID或自定义ID）
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        custom_pattern = r'^[A-Za-z0-9\-_:\.]+$'
        if not (re.match(uuid_pattern, device_identifier) or 
                re.match(custom_pattern, device_identifier)):
            raise forms.ValidationError('设备标识格式无效')
    return device_identifier
```

### 1.2 API请求验证

如果使用DRF，在序列化器中添加验证：

```python
# iot_devices/serializers.py
from rest_framework import serializers
from .models import Project, Device

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['project_id', 'name', 'description']
        
    def validate_name(self, value):
        # 防止XSS攻击
        if '<script>' in value.lower() or '</script>' in value.lower():
            raise serializers.ValidationError('项目名称不能包含脚本标签')
        return value
        
    def validate_project_id(self, value):
        import re
        if not re.match(r'^[A-Za-z0-9\-]+$', value):
            raise serializers.ValidationError('项目ID只能包含字母、数字和连字符')
        return value
```

## 2. ORM使用安全

Django ORM通过使用参数化查询自动防止SQL注入。

### 2.1 安全ORM使用示例

```python
# 安全的查询方式
user_id = request.GET.get('user_id')
projects = Project.objects.filter(owner_id=user_id)

# 不安全的原生SQL（避免使用）
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM iot_devices_project WHERE owner_id = %s", [user_id])  # 正确做法
# cursor.execute(f"SELECT * FROM iot_devices_project WHERE owner_id = {user_id}")  # 错误做法！
```

### 2.2 使用Q对象进行复杂查询

```python
from django.db.models import Q

def get_filtered_devices(project_id, status, name_query):
    return Device.objects.filter(
        Q(project_id=project_id),
        Q(status=status) if status else Q(),
        Q(name__icontains=name_query) if name_query else Q()
    )
```

## 3. CSRF保护

Django自带CSRF保护，但需要确保正确使用。

### 3.1 在所有表单中包含CSRF令牌

```html
<form method="post" action="{% url 'project_create' %}">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">创建</button>
</form>
```

### 3.2 AJAX请求时包含CSRF令牌

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
        'device_id': deviceId,
        'command': 'power_on'
    })
});
```

### 3.3 确认CSRF中间件已启用

```python
# DjangoNovaCloud/settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # 确保此行存在
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

## 4. 点击劫持防护

防止恶意网站通过iframe嵌入NovaCloud页面实施点击劫持。

### 4.1 配置X-Frame-Options

```python
# DjangoNovaCloud/settings.py
X_FRAME_OPTIONS = 'DENY'  # 完全禁止在iframe中加载
# 或
X_FRAME_OPTIONS = 'SAMEORIGIN'  # 仅允许同源iframe加载
```

## 5. 密码策略与管理

### 5.1 配置密码验证器

```python
# DjangoNovaCloud/settings.py
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
]
```

### 5.2 强制定期修改密码

创建自定义中间件检查密码最后修改时间：

```python
# accounts/middleware.py
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

class PasswordExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 获取用户最后修改密码的时间，这需要在User模型中添加last_password_change字段
            last_change = getattr(request.user, 'last_password_change', None)
            if last_change and (timezone.now() - last_change) > timedelta(days=90):
                # 密码超过90天未修改
                if request.path != '/accounts/change-password/':
                    return redirect('change_password')
        
        return self.get_response(request)
```

## 6. 会话管理安全

### 6.1 强化会话配置

```python
# DjangoNovaCloud/settings.py

# 使用HTTPS时设置（生产环境）
SESSION_COOKIE_SECURE = True

# 防止XSS获取Cookie
SESSION_COOKIE_HTTPONLY = True

# 设置会话超时（12小时）
SESSION_COOKIE_AGE = 12 * 60 * 60  # 秒数

# 或者关闭浏览器时会话过期
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# 防止CSRF
SESSION_COOKIE_SAMESITE = 'Lax'  # 或 'Strict'
```

## 7. 敏感信息处理

### 7.1 设备密钥安全

设备密钥是敏感信息，建议在存储前加密或哈希处理：

```python
# iot_devices/models.py
import uuid
import hmac
import hashlib
from django.conf import settings

class Device(models.Model):
    # ... 其他字段 ...
    device_key = models.CharField('设备密钥', max_length=64, blank=True)
    device_key_hash = models.CharField('设备密钥哈希', max_length=128, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.device_key:
            # 生成新密钥
            self.device_key = uuid.uuid4().hex
            
            # 计算密钥哈希
            self.device_key_hash = hmac.new(
                settings.SECRET_KEY.encode(),
                self.device_key.encode(),
                hashlib.sha256
            ).hexdigest()
            
        super().save(*args, **kwargs)
        
        # 创建后从数据库去除明文密钥（仅返回给用户一次）
        if self.device_key:
            temp_key = self.device_key
            self.__class__.objects.filter(pk=self.pk).update(device_key='')
            self.device_key = temp_key
```

### 7.2 使用环境变量管理敏感配置

使用`python-dotenv`管理环境变量：

```python
# DjangoNovaCloud/settings.py
import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 从环境变量获取敏感配置
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', os.path.join(BASE_DIR, 'db.sqlite3')),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

# MQTT配置
MQTT_CONFIG = {
    'BROKER_HOST': os.environ.get('MQTT_BROKER_HOST', 'broker.emqx.io'),
    'BROKER_PORT': int(os.environ.get('MQTT_BROKER_PORT', 1883)),
    'BROKER_PORT_TLS': int(os.environ.get('MQTT_BROKER_PORT_TLS', 8883)),
    'USE_TLS': os.environ.get('MQTT_USE_TLS', 'False') == 'True',
    'USERNAME': os.environ.get('MQTT_USERNAME', ''),
    'PASSWORD': os.environ.get('MQTT_PASSWORD', ''),
}
```

示例`.env`文件（不要提交到版本控制）：
```
# Django设置
SECRET_KEY=your_very_long_and_random_secret_key_here
DEBUG=False

# 数据库设置
DB_ENGINE=django.db.backends.postgresql
DB_NAME=novacloud_db
DB_USER=novacloud_user
DB_PASSWORD=strong_db_password_here
DB_HOST=localhost
DB_PORT=5432

# MQTT设置
MQTT_BROKER_HOST=broker.emqx.io
MQTT_BROKER_PORT=1883
MQTT_BROKER_PORT_TLS=8883
MQTT_USE_TLS=True
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password
```

## 8. HTTPS强制

### 8.1 配置HTTPS设置

```python
# DjangoNovaCloud/settings.py

# 重定向HTTP请求到HTTPS
SECURE_SSL_REDIRECT = True

# 如果使用代理服务器，设置代理的头信息
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 安全Cookie设置
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS设置 (HTTP严格传输安全)
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 8.2 Nginx配置HTTPS

```nginx
server {
    listen 80;
    server_name your.domain.com;
    
    # 将HTTP请求重定向到HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your.domain.com;
    
    # SSL证书配置
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    # SSL协议配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    
    # HSTS头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 其他安全头
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    
    # ... 其他配置 ...
}
```

## 9. MQTT通信安全

### 9.1 启用MQTT TLS加密

```python
# mqtt_client/mqtt.py

def connect(self):
    """连接到MQTT代理服务器"""
    client = mqtt.Client(client_id=self.client_id)
    
    # 设置用户名和密码
    if self.config.get('USERNAME') and self.config.get('PASSWORD'):
        client.username_pw_set(self.config['USERNAME'], self.config['PASSWORD'])
    
    # 设置TLS/SSL
    if self.config.get('USE_TLS'):
        # 可以配置CA证书路径和客户端证书
        ca_certs = self.config.get('CA_CERTS')
        certfile = self.config.get('CERTFILE')
        keyfile = self.config.get('KEYFILE')
        
        client.tls_set(
            ca_certs=ca_certs,
            certfile=certfile,
            keyfile=keyfile,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
    
    # ... 其他代码 ...
```

### 9.2 MQTT代理服务器安全配置

Mosquitto配置文件示例：

```
# /etc/mosquitto/mosquitto.conf

# 监听未加密端口（可选）
listener 1883
protocol mqtt

# 监听TLS加密端口
listener 8883
protocol mqtt
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
tls_version tlsv1.2

# 启用密码认证
allow_anonymous false
password_file /etc/mosquitto/passwd
```

## 10. API安全

### 10.1 API认证与授权

使用Django REST Framework的Token认证：

```python
# DjangoNovaCloud/settings.py
INSTALLED_APPS = [
    # ... 其他应用 ...
    'rest_framework',
    'rest_framework.authtoken',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### 10.2 API权限控制

```python
# iot_devices/api_views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Project, Device
from .serializers import ProjectSerializer, DeviceSerializer

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限：仅允许对象所有者编辑
    """
    def has_object_permission(self, request, view, obj):
        # 读取权限允许任何请求
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 写入权限仅允许对象所有者
        return obj.owner == request.user

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        # 仅返回当前用户拥有的项目
        return Project.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        # 创建项目时设置所有者为当前用户
        serializer.save(owner=self.request.user)
```

### 10.3 API请求速率限制

```python
# DjangoNovaCloud/settings.py
REST_FRAMEWORK = {
    # ... 其他设置 ...
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}
```

## 11. 安全漏洞扫描工具

推荐的安全扫描工具：

1. **Bandit**: Python代码安全问题扫描
   ```bash
   pip install bandit
   bandit -r .
   ```

2. **OWASP ZAP**: Web应用漏洞扫描
   - 下载：https://www.zaproxy.org/
   - 可以通过代理模式或爬虫模式检测应用

3. **Safety**: 依赖项安全漏洞检查
   ```bash
   pip install safety
   safety check
   ```

4. **Django-security**: Django安全最佳实践检查器
   ```bash
   pip install django-security
   python manage.py checksecurity
   ```

## 12. 安全监控与日志

### 12.1 配置详细日志记录

```python
# DjangoNovaCloud/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
        'security': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/security.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': True,
        },
        'app.security': {  # 自定义安全日志
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 12.2 记录安全相关事件

```python
# accounts/views.py
import logging

security_logger = logging.getLogger('app.security')

class LoginView(auth_views.LoginView):
    # ... 其他代码 ...
    
    def form_valid(self, form):
        security_logger.info(
            f"User login successful: {form.get_user().username} from IP {self.request.META.get('REMOTE_ADDR')}"
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        security_logger.warning(
            f"Failed login attempt for user: {form.data.get('username')} from IP {self.request.META.get('REMOTE_ADDR')}"
        )
        return super().form_invalid(form)
```

### 12.3 安全事件告警

```python
# utils/security.py
import logging
from django.core.mail import mail_admins

security_logger = logging.getLogger('app.security')

def log_security_event(event_type, details, level='INFO', alert_admin=False):
    """记录安全事件并可选择性地通知管理员"""
    message = f"Security event: {event_type} - {details}"
    
    if level == 'INFO':
        security_logger.info(message)
    elif level == 'WARNING':
        security_logger.warning(message)
    elif level == 'ERROR':
        security_logger.error(message)
    elif level == 'CRITICAL':
        security_logger.critical(message)
        # 高危事件强制通知管理员
        alert_admin = True
    
    if alert_admin:
        mail_admins(
            subject=f"Security Alert: {event_type}",
            message=f"Details: {details}",
            fail_silently=True
        )
```

## 13. 安全更新与补丁

### 13.1 定期更新依赖项

创建一个脚本定期检查和更新依赖项：

```bash
#!/bin/bash
# security_updates.sh

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖项安全问题
pip install safety
safety check

# 更新有安全问题的依赖项
if [ $? -ne 0 ]; then
    # 执行安全更新
    pip list --outdated --format=json | \
    python -c "import json, sys; print('\n'.join([pkg['name'] for pkg in json.load(sys.stdin)]))" | \
    xargs -n1 pip install -U
    
    # 更新requirements.txt
    pip freeze > requirements.txt
    
    # 通知管理员
    echo "Security updates applied" | mail -s "NovaCloud Security Update" admin@example.com
fi
```

### 13.2 自动化安全漏洞扫描

配置CI/CD管道以运行安全检查：

```yaml
# .github/workflows/security.yml
name: Security Checks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    # 每周一凌晨运行
    - cron: '0 0 * * 1'

jobs:
  security-scan:
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
        pip install -r requirements.txt
        pip install bandit safety
    - name: Check for security issues with Bandit
      run: bandit -r .
    - name: Check dependencies with Safety
      run: safety check
``` 

## 1. 输入验证强化

为防范XSS、SQL注入、命令注入等攻击，需确保所有用户输入经过严格验证和清理。

### 1.1 表单验证增强

在`iot_devices/forms.py`中的`ProjectForm`添加自定义验证器：

```python
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

在`DeviceForm`中添加设备标识符验证：

```python
def clean_device_identifier(self):
    device_identifier = self.cleaned_data.get('device_identifier')
    # MAC地址格式验证 (XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX)
    import re
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    if not re.match(mac_pattern, device_identifier):
        # 如果不是MAC地址格式，检查是否为其他允许的格式（如UUID或自定义ID）
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        custom_pattern = r'^[A-Za-z0-9\-_:\.]+$'
        if not (re.match(uuid_pattern, device_identifier) or 
                re.match(custom_pattern, device_identifier)):
            raise forms.ValidationError('设备标识格式无效')
    return device_identifier
```

### 1.2 API请求验证

如果使用DRF，在序列化器中添加验证：

```python
# iot_devices/serializers.py
from rest_framework import serializers
from .models import Project, Device

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['project_id', 'name', 'description']
        
    def validate_name(self, value):
        # 防止XSS攻击
        if '<script>' in value.lower() or '</script>' in value.lower():
            raise serializers.ValidationError('项目名称不能包含脚本标签')
        return value
        
    def validate_project_id(self, value):
        import re
        if not re.match(r'^[A-Za-z0-9\-]+$', value):
            raise serializers.ValidationError('项目ID只能包含字母、数字和连字符')
        return value
```

## 2. ORM使用安全

Django ORM通过使用参数化查询自动防止SQL注入。

### 2.1 安全ORM使用示例

```python
# 安全的查询方式
user_id = request.GET.get('user_id')
projects = Project.objects.filter(owner_id=user_id)

# 不安全的原生SQL（避免使用）
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM iot_devices_project WHERE owner_id = %s", [user_id])  # 正确做法
# cursor.execute(f"SELECT * FROM iot_devices_project WHERE owner_id = {user_id}")  # 错误做法！
```

### 2.2 使用Q对象进行复杂查询

```python
from django.db.models import Q

def get_filtered_devices(project_id, status, name_query):
    return Device.objects.filter(
        Q(project_id=project_id),
        Q(status=status) if status else Q(),
        Q(name__icontains=name_query) if name_query else Q()
    )
```

## 3. CSRF保护

Django自带CSRF保护，但需要确保正确使用。

### 3.1 在所有表单中包含CSRF令牌

```html
<form method="post" action="{% url 'project_create' %}">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">创建</button>
</form>
```

### 3.2 AJAX请求时包含CSRF令牌

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
        'device_id': deviceId,
        'command': 'power_on'
    })
});
```

### 3.3 确认CSRF中间件已启用

```python
# DjangoNovaCloud/settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # 确保此行存在
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

## 4. 点击劫持防护

防止恶意网站通过iframe嵌入NovaCloud页面实施点击劫持。

### 4.1 配置X-Frame-Options

```python
# DjangoNovaCloud/settings.py
X_FRAME_OPTIONS = 'DENY'  # 完全禁止在iframe中加载
# 或
X_FRAME_OPTIONS = 'SAMEORIGIN'  # 仅允许同源iframe加载
```

## 5. 密码策略与管理

### 5.1 配置密码验证器

```python
# DjangoNovaCloud/settings.py
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
]
```

### 5.2 强制定期修改密码

创建自定义中间件检查密码最后修改时间：

```python
# accounts/middleware.py
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

class PasswordExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 获取用户最后修改密码的时间，这需要在User模型中添加last_password_change字段
            last_change = getattr(request.user, 'last_password_change', None)
            if last_change and (timezone.now() - last_change) > timedelta(days=90):
                # 密码超过90天未修改
                if request.path != '/accounts/change-password/':
                    return redirect('change_password')
        
        return self.get_response(request)
```

## 6. 会话管理安全

### 6.1 强化会话配置

```python
# DjangoNovaCloud/settings.py

# 使用HTTPS时设置（生产环境）
SESSION_COOKIE_SECURE = True

# 防止XSS获取Cookie
SESSION_COOKIE_HTTPONLY = True

# 设置会话超时（12小时）
SESSION_COOKIE_AGE = 12 * 60 * 60  # 秒数

# 或者关闭浏览器时会话过期
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# 防止CSRF
SESSION_COOKIE_SAMESITE = 'Lax'  # 或 'Strict'
```

## 7. 敏感信息处理

### 7.1 设备密钥安全

设备密钥是敏感信息，建议在存储前加密或哈希处理：

```python
# iot_devices/models.py
import uuid
import hmac
import hashlib
from django.conf import settings

class Device(models.Model):
    # ... 其他字段 ...
    device_key = models.CharField('设备密钥', max_length=64, blank=True)
    device_key_hash = models.CharField('设备密钥哈希', max_length=128, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.device_key:
            # 生成新密钥
            self.device_key = uuid.uuid4().hex
            
            # 计算密钥哈希
            self.device_key_hash = hmac.new(
                settings.SECRET_KEY.encode(),
                self.device_key.encode(),
                hashlib.sha256
            ).hexdigest()
            
        super().save(*args, **kwargs)
        
        # 创建后从数据库去除明文密钥（仅返回给用户一次）
        if self.device_key:
            temp_key = self.device_key
            self.__class__.objects.filter(pk=self.pk).update(device_key='')
            self.device_key = temp_key
```

### 7.2 使用环境变量管理敏感配置

使用`python-dotenv`管理环境变量：

```python
# DjangoNovaCloud/settings.py
import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 从环境变量获取敏感配置
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', os.path.join(BASE_DIR, 'db.sqlite3')),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

# MQTT配置
MQTT_CONFIG = {
    'BROKER_HOST': os.environ.get('MQTT_BROKER_HOST', 'broker.emqx.io'),
    'BROKER_PORT': int(os.environ.get('MQTT_BROKER_PORT', 1883)),
    'BROKER_PORT_TLS': int(os.environ.get('MQTT_BROKER_PORT_TLS', 8883)),
    'USE_TLS': os.environ.get('MQTT_USE_TLS', 'False') == 'True',
    'USERNAME': os.environ.get('MQTT_USERNAME', ''),
    'PASSWORD': os.environ.get('MQTT_PASSWORD', ''),
}
```

示例`.env`文件（不要提交到版本控制）：
```
# Django设置
SECRET_KEY=your_very_long_and_random_secret_key_here
DEBUG=False

# 数据库设置
DB_ENGINE=django.db.backends.postgresql
DB_NAME=novacloud_db
DB_USER=novacloud_user
DB_PASSWORD=strong_db_password_here
DB_HOST=localhost
DB_PORT=5432

# MQTT设置
MQTT_BROKER_HOST=broker.emqx.io
MQTT_BROKER_PORT=1883
MQTT_BROKER_PORT_TLS=8883
MQTT_USE_TLS=True
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password
```

## 8. HTTPS强制

### 8.1 配置HTTPS设置

```python
# DjangoNovaCloud/settings.py

# 重定向HTTP请求到HTTPS
SECURE_SSL_REDIRECT = True

# 如果使用代理服务器，设置代理的头信息
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 安全Cookie设置
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS设置 (HTTP严格传输安全)
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 8.2 Nginx配置HTTPS

```nginx
server {
    listen 80;
    server_name your.domain.com;
    
    # 将HTTP请求重定向到HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your.domain.com;
    
    # SSL证书配置
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    # SSL协议配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    
    # HSTS头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 其他安全头
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    
    # ... 其他配置 ...
}
```

## 9. MQTT通信安全

### 9.1 启用MQTT TLS加密

```python
# mqtt_client/mqtt.py

def connect(self):
    """连接到MQTT代理服务器"""
    client = mqtt.Client(client_id=self.client_id)
    
    # 设置用户名和密码
    if self.config.get('USERNAME') and self.config.get('PASSWORD'):
        client.username_pw_set(self.config['USERNAME'], self.config['PASSWORD'])
    
    # 设置TLS/SSL
    if self.config.get('USE_TLS'):
        # 可以配置CA证书路径和客户端证书
        ca_certs = self.config.get('CA_CERTS')
        certfile = self.config.get('CERTFILE')
        keyfile = self.config.get('KEYFILE')
        
        client.tls_set(
            ca_certs=ca_certs,
            certfile=certfile,
            keyfile=keyfile,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
    
    # ... 其他代码 ...
```

### 9.2 MQTT代理服务器安全配置

Mosquitto配置文件示例：

```
# /etc/mosquitto/mosquitto.conf

# 监听未加密端口（可选）
listener 1883
protocol mqtt

# 监听TLS加密端口
listener 8883
protocol mqtt
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
tls_version tlsv1.2

# 启用密码认证
allow_anonymous false
password_file /etc/mosquitto/passwd
```

## 10. API安全

### 10.1 API认证与授权

使用Django REST Framework的Token认证：

```python
# DjangoNovaCloud/settings.py
INSTALLED_APPS = [
    # ... 其他应用 ...
    'rest_framework',
    'rest_framework.authtoken',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### 10.2 API权限控制

```python
# iot_devices/api_views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Project, Device
from .serializers import ProjectSerializer, DeviceSerializer

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限：仅允许对象所有者编辑
    """
    def has_object_permission(self, request, view, obj):
        # 读取权限允许任何请求
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 写入权限仅允许对象所有者
        return obj.owner == request.user

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        # 仅返回当前用户拥有的项目
        return Project.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        # 创建项目时设置所有者为当前用户
        serializer.save(owner=self.request.user)
```

### 10.3 API请求速率限制

```python
# DjangoNovaCloud/settings.py
REST_FRAMEWORK = {
    # ... 其他设置 ...
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}
```

## 11. 安全漏洞扫描工具

推荐的安全扫描工具：

1. **Bandit**: Python代码安全问题扫描
   ```bash
   pip install bandit
   bandit -r .
   ```

2. **OWASP ZAP**: Web应用漏洞扫描
   - 下载：https://www.zaproxy.org/
   - 可以通过代理模式或爬虫模式检测应用

3. **Safety**: 依赖项安全漏洞检查
   ```bash
   pip install safety
   safety check
   ```

4. **Django-security**: Django安全最佳实践检查器
   ```bash
   pip install django-security
   python manage.py checksecurity
   ```

## 12. 安全监控与日志

### 12.1 配置详细日志记录

```python
# DjangoNovaCloud/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
        'security': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/security.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': True,
        },
        'app.security': {  # 自定义安全日志
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 12.2 记录安全相关事件

```python
# accounts/views.py
import logging

security_logger = logging.getLogger('app.security')

class LoginView(auth_views.LoginView):
    # ... 其他代码 ...
    
    def form_valid(self, form):
        security_logger.info(
            f"User login successful: {form.get_user().username} from IP {self.request.META.get('REMOTE_ADDR')}"
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        security_logger.warning(
            f"Failed login attempt for user: {form.data.get('username')} from IP {self.request.META.get('REMOTE_ADDR')}"
        )
        return super().form_invalid(form)
```

### 12.3 安全事件告警

```python
# utils/security.py
import logging
from django.core.mail import mail_admins

security_logger = logging.getLogger('app.security')

def log_security_event(event_type, details, level='INFO', alert_admin=False):
    """记录安全事件并可选择性地通知管理员"""
    message = f"Security event: {event_type} - {details}"
    
    if level == 'INFO':
        security_logger.info(message)
    elif level == 'WARNING':
        security_logger.warning(message)
    elif level == 'ERROR':
        security_logger.error(message)
    elif level == 'CRITICAL':
        security_logger.critical(message)
        # 高危事件强制通知管理员
        alert_admin = True
    
    if alert_admin:
        mail_admins(
            subject=f"Security Alert: {event_type}",
            message=f"Details: {details}",
            fail_silently=True
        )
```

## 13. 安全更新与补丁

### 13.1 定期更新依赖项

创建一个脚本定期检查和更新依赖项：

```bash
#!/bin/bash
# security_updates.sh

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖项安全问题
pip install safety
safety check

# 更新有安全问题的依赖项
if [ $? -ne 0 ]; then
    # 执行安全更新
    pip list --outdated --format=json | \
    python -c "import json, sys; print('\n'.join([pkg['name'] for pkg in json.load(sys.stdin)]))" | \
    xargs -n1 pip install -U
    
    # 更新requirements.txt
    pip freeze > requirements.txt
    
    # 通知管理员
    echo "Security updates applied" | mail -s "NovaCloud Security Update" admin@example.com
fi
```

### 13.2 自动化安全漏洞扫描

配置CI/CD管道以运行安全检查：

```yaml
# .github/workflows/security.yml
name: Security Checks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    # 每周一凌晨运行
    - cron: '0 0 * * 1'

jobs:
  security-scan:
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
        pip install -r requirements.txt
        pip install bandit safety
    - name: Check for security issues with Bandit
      run: bandit -r .
    - name: Check dependencies with Safety
      run: safety check
``` 