# NovaCloud平台测试指南

## 一、测试框架与工具

### 推荐的测试工具

NovaCloud平台的测试工作建议使用以下工具组合：

- **pytest**: 现代化的测试框架，比Django内置的unittest更加灵活和易用。
- **pytest-django**: 为pytest提供Django集成功能。
- **pytest-cov**: 用于生成测试覆盖率报告。

### 为何选择pytest

pytest相比Django默认的unittest框架有以下优势：

1. **更简洁的语法**：不需要创建测试类，可以直接使用函数编写测试。
2. **强大的fixture机制**：更灵活的依赖注入和测试资源管理。
3. **参数化测试**：可以用不同参数集运行相同的测试。
4. **丰富的插件生态**：如pytest-django, pytest-cov等，提供专业功能。
5. **更友好的错误报告**：展示详细的错误比较和上下文信息。

### 安装测试工具

```bash
pip install pytest pytest-django pytest-cov
```

然后创建一个`pytest.ini`文件配置pytest：

```ini
[pytest]
DJANGO_SETTINGS_MODULE = DjangoNovaCloud.settings
python_files = test_*.py
testpaths = accounts iot_devices mqtt_client strategy_engine
```

## 二、单元测试 (Unit Tests)

单元测试是测试系统最小可测试单元（函数、方法、类）的过程。下面是各模块的单元测试示例。

### 用户认证模块测试

#### 测试 UserRegisterForm

```python
# accounts/tests/test_forms.py
import pytest
from accounts.forms import UserRegisterForm
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_user_register_form_valid():
    """测试有效的用户注册表单"""
    form_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    form = UserRegisterForm(data=form_data)
    assert form.is_valid(), f"表单验证失败: {form.errors}"

@pytest.mark.django_db
def test_user_register_form_duplicate_email():
    """测试使用已存在的邮箱注册"""
    # 创建一个用户
    User.objects.create_user(username='existinguser', email='exists@example.com', password='password123')
    
    # 使用相同的邮箱尝试注册
    form_data = {
        'username': 'newuser',
        'email': 'exists@example.com',  # 这个邮箱已经被使用
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    form = UserRegisterForm(data=form_data)
    assert not form.is_valid()
    assert 'email' in form.errors
    assert '该邮箱已被注册' in str(form.errors['email'])
```

#### 测试 UserLoginForm

```python
# accounts/tests/test_forms.py
import pytest
from accounts.forms import UserLoginForm
from django.contrib.auth.models import User
from django.test import RequestFactory

@pytest.mark.django_db
def test_user_login_with_username():
    """测试使用用户名登录"""
    # 创建用户
    User.objects.create_user(username='testuser', email='test@example.com', password='password123')
    
    # 创建请求对象
    factory = RequestFactory()
    request = factory.get('/')
    
    # 使用用户名登录
    form_data = {
        'username': 'testuser',
        'password': 'password123',
    }
    form = UserLoginForm(request=request, data=form_data)
    assert form.is_valid(), f"用户名登录验证失败: {form.errors}"

@pytest.mark.django_db
def test_user_login_with_email():
    """测试使用邮箱登录"""
    # 创建用户
    User.objects.create_user(username='testuser', email='test@example.com', password='password123')
    
    # 创建请求对象
    factory = RequestFactory()
    request = factory.get('/')
    
    # 使用邮箱登录
    form_data = {
        'username': 'test@example.com',  # 使用邮箱而非用户名
        'password': 'password123',
    }
    form = UserLoginForm(request=request, data=form_data)
    assert form.is_valid(), f"邮箱登录验证失败: {form.errors}"

@pytest.mark.django_db
def test_user_login_invalid_credentials():
    """测试无效的登录凭据"""
    # 创建用户
    User.objects.create_user(username='testuser', email='test@example.com', password='password123')
    
    # 创建请求对象
    factory = RequestFactory()
    request = factory.get('/')
    
    # 使用错误的密码尝试登录
    form_data = {
        'username': 'testuser',
        'password': 'wrongpassword',
    }
    form = UserLoginForm(request=request, data=form_data)
    assert not form.is_valid()
    assert '用户名/邮箱或密码不正确' in str(form.errors)
```

#### 测试注册视图

```python
# accounts/tests/test_views.py
import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_register_view_get(client):
    """测试GET请求注册视图"""
    url = reverse('accounts:register')
    response = client.get(url)
    assert response.status_code == 200
    assert 'form' in response.context
    assert 'accounts/register.html' in [t.name for t in response.templates]

@pytest.mark.django_db
def test_register_view_post_success(client):
    """测试成功注册"""
    url = reverse('accounts:register')
    data = {
        'username': 'newuser',
        'email': 'new@example.com',
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    response = client.post(url, data)
    # 检查是否重定向到登录页面
    assert response.status_code == 302
    assert response.url == reverse('accounts:login')
    # 验证用户是否被创建
    assert User.objects.filter(username='newuser').exists()

@pytest.mark.django_db
def test_register_view_post_invalid(client):
    """测试无效注册数据"""
    url = reverse('accounts:register')
    data = {
        'username': 'newuser',
        'email': 'invalid-email',  # 无效的邮箱格式
        'password1': 'pass1',
        'password2': 'pass2',  # 密码不匹配
    }
    response = client.post(url, data)
    assert response.status_code == 200  # 表单有错误，返回同一页面
    assert 'form' in response.context
    assert response.context['form'].errors  # 表单包含错误
    # 验证用户未被创建
    assert not User.objects.filter(username='newuser').exists()
```

### IoT设备模块测试

#### 测试 Device 模型

```python
# iot_devices/tests/test_models.py
import pytest
from iot_devices.models import Project, Device
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_device_key_generation():
    """测试设备密钥自动生成"""
    # 创建用户和项目
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=user
    )
    
    # 创建设备，不提供device_key
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    
    # 验证密钥已生成
    assert device.device_key is not None
    assert len(device.device_key) == 32  # uuid4().hex 生成32个字符
```

#### 测试 ProjectForm 和 DeviceForm

```python
# iot_devices/tests/test_forms.py
import pytest
from django.contrib.auth.models import User
from iot_devices.models import Project
from iot_devices.forms import ProjectForm, DeviceForm

@pytest.mark.django_db
def test_project_form_valid():
    """测试有效的项目表单"""
    user = User.objects.create_user(username='testuser', password='password123')
    form_data = {
        'project_id': 'PRJ-TEST',
        'name': 'Test Project',
        'description': 'This is a test project'
    }
    form = ProjectForm(data=form_data, user=user)
    assert form.is_valid(), f"表单验证失败: {form.errors}"

@pytest.mark.django_db
def test_project_form_invalid_id():
    """测试无效的项目ID"""
    user = User.objects.create_user(username='testuser', password='password123')
    form_data = {
        'project_id': 'PRJ TEST',  # 包含空格，不合法
        'name': 'Test Project',
    }
    form = ProjectForm(data=form_data, user=user)
    assert not form.is_valid()
    assert 'project_id' in form.errors

@pytest.mark.django_db
def test_device_form_with_project():
    """测试有效的设备表单，指定项目"""
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=user
    )
    
    form_data = {
        'device_id': 'DEV-TEST',
        'device_identifier': 'AA:BB:CC:DD:EE:FF',
        'name': 'Test Device',
        'project': project.id,
        'status': 'offline'
    }
    form = DeviceForm(data=form_data, user=user)
    assert form.is_valid(), f"表单验证失败: {form.errors}"

@pytest.mark.django_db
def test_device_form_invalid_identifier():
    """测试无效的设备标识符"""
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=user
    )
    
    form_data = {
        'device_id': 'DEV-TEST',
        'device_identifier': 'INVALID MAC',  # 无效的MAC地址格式
        'name': 'Test Device',
        'project': project.id,
        'status': 'offline'
    }
    form = DeviceForm(data=form_data, user=user)
    assert not form.is_valid()
    assert 'device_identifier' in form.errors
```

#### 测试项目列表视图（权限）

```python
# iot_devices/tests/test_views.py
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from iot_devices.models import Project

@pytest.mark.django_db
def test_project_list_view_authenticated(client):
    """测试已登录用户可以访问项目列表"""
    # 创建用户
    user = User.objects.create_user(username='testuser', password='password123')
    # 创建一些项目
    Project.objects.create(project_id='PRJ-1', name='Project 1', owner=user)
    Project.objects.create(project_id='PRJ-2', name='Project 2', owner=user)
    
    # 登录
    client.login(username='testuser', password='password123')
    
    # 访问项目列表
    url = reverse('iot_devices:project_list')
    response = client.get(url)
    
    # 验证响应
    assert response.status_code == 200
    assert 'projects' in response.context
    assert len(response.context['projects']) == 2

@pytest.mark.django_db
def test_project_list_view_unauthenticated(client):
    """测试未登录用户被重定向到登录页面"""
    url = reverse('iot_devices:project_list')
    response = client.get(url)
    
    # 验证重定向
    assert response.status_code == 302
    assert reverse('accounts:login') in response.url

@pytest.mark.django_db
def test_project_list_view_only_shows_user_projects(client):
    """测试用户只能看到自己的项目"""
    # 创建两个用户
    user1 = User.objects.create_user(username='user1', password='password123')
    user2 = User.objects.create_user(username='user2', password='password123')
    
    # 为每个用户创建项目
    Project.objects.create(project_id='PRJ-U1', name='User1 Project', owner=user1)
    Project.objects.create(project_id='PRJ-U2', name='User2 Project', owner=user2)
    
    # 用户1登录
    client.login(username='user1', password='password123')
    
    # 访问项目列表
    url = reverse('iot_devices:project_list')
    response = client.get(url)
    
    # 验证用户1只能看到自己的项目
    assert response.status_code == 200
    assert 'projects' in response.context
    assert len(response.context['projects']) == 1
    assert response.context['projects'][0].project_id == 'PRJ-U1'
```

### MQTT消息处理测试

#### 测试数据上报处理

```python
# mqtt_client/tests/test_mqtt_handler.py
import pytest
import json
from unittest.mock import patch, MagicMock
from mqtt_client.mqtt import MQTTClient
from iot_devices.models import Project, Device, Sensor, SensorData
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_handle_device_data():
    """测试处理设备上报的传感器数据"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    sensor = Sensor.objects.create(
        name='Temperature Sensor',
        sensor_type='temperature',
        unit='°C',
        device=device,
        value_key='temperature'
    )
    
    # 模拟MQTT客户端
    mqtt_client = MQTTClient()
    
    # 创建模拟的MQTT消息
    message = MagicMock()
    message.topic = 'novacloud/devices/DEV-TEST/data'
    message.payload = json.dumps({
        'temperature': 25.5,
        'humidity': 60,
        'timestamp': 1651234567,
        'device_id': 'DEV-TEST'
    }).encode('utf-8')
    
    # 调用处理函数
    with patch.object(mqtt_client, 'client') as mock_client:
        mqtt_client._handle_device_data(message)
    
    # 验证数据保存
    data = SensorData.objects.filter(sensor=sensor).first()
    assert data is not None
    assert data.value_float == 25.5
    
    # 验证设备状态更新
    device.refresh_from_db()
    assert device.status == 'online'
    assert device.last_seen is not None
```

#### 测试设备认证

```python
# mqtt_client/tests/test_authentication.py
import pytest
from mqtt_client.auth import authenticate_device
from iot_devices.models import Project, Device
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_device_authentication_success():
    """测试设备认证成功"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    # 设备密钥在创建时自动生成
    device_key = device.device_key
    
    # 调用认证函数
    result = authenticate_device('DEV-TEST', device_key)
    
    # 验证结果
    assert result is True

@pytest.mark.django_db
def test_device_authentication_wrong_key():
    """测试设备认证失败 - 错误的密钥"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    
    # 使用错误的密钥
    wrong_key = 'wrong_key'
    
    # 调用认证函数
    result = authenticate_device('DEV-TEST', wrong_key)
    
    # 验证结果
    assert result is False

@pytest.mark.django_db
def test_device_authentication_nonexistent_device():
    """测试设备认证失败 - 不存在的设备"""
    # 调用认证函数
    result = authenticate_device('NONEXISTENT', 'any_key')
    
    # 验证结果
    assert result is False
```

### 策略引擎测试

```python
# strategy_engine/tests/test_evaluator.py
import pytest
from strategy_engine.evaluator import evaluate_condition
from strategy_engine.models import Strategy, Condition
from iot_devices.models import Project, Device, Sensor, SensorData
from django.contrib.auth.models import User
from datetime import datetime

@pytest.mark.django_db
def test_evaluate_greater_than_condition():
    """测试大于条件的评估"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    sensor = Sensor.objects.create(
        name='Temperature Sensor',
        sensor_type='temperature',
        unit='°C',
        device=device,
        value_key='temperature'
    )
    
    # 创建传感器数据
    SensorData.objects.create(
        sensor=sensor,
        value_float=30.0,  # 高温值
        timestamp=datetime.now()
    )
    
    # 创建策略和条件
    strategy = Strategy.objects.create(
        name='High Temperature Alert',
        description='温度过高报警',
        owner=user,
        is_active=True
    )
    condition = Condition.objects.create(
        strategy=strategy,
        sensor=sensor,
        operator='gt',  # 大于
        value=25.0,
        value_type='float'
    )
    
    # 评估条件
    result = evaluate_condition(condition)
    
    # 验证结果
    assert result is True, "温度大于阈值，条件应该满足"
```

## 三、集成测试 (Integration Tests)

集成测试用于测试多个组件一起工作时的功能。

### 场景1: 用户-项目-设备流程

```python
# tests/integration/test_user_project_device_flow.py
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from iot_devices.models import Project, Device

@pytest.mark.django_db
def test_complete_user_project_device_flow(client):
    """测试完整流程：用户注册->登录->创建项目->添加设备->查看设备->删除设备->删除项目"""
    
    # 1. 用户注册
    register_url = reverse('accounts:register')
    register_data = {
        'username': 'flowuser',
        'email': 'flow@example.com',
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    response = client.post(register_url, register_data)
    assert response.status_code == 302  # 重定向到登录页面
    assert User.objects.filter(username='flowuser').exists()
    
    # 2. 用户登录
    login_url = reverse('accounts:login')
    login_data = {
        'username': 'flowuser',
        'password': 'securepassword123',
    }
    response = client.post(login_url, login_data)
    assert response.status_code == 302  # 重定向到首页
    
    # 3. 创建项目
    create_project_url = reverse('iot_devices:create_project')
    project_data = {
        'project_id': 'PRJ-FLOW',
        'name': 'Flow Test Project',
        'description': 'Project for integration testing',
    }
    response = client.post(create_project_url, project_data)
    assert response.status_code == 302  # 重定向到项目列表
    assert Project.objects.filter(project_id='PRJ-FLOW').exists()
    
    # 获取创建的项目
    project = Project.objects.get(project_id='PRJ-FLOW')
    
    # 4. 在项目中添加设备
    create_device_url = reverse('iot_devices:create_device', kwargs={'project_id': 'PRJ-FLOW'})
    device_data = {
        'device_id': 'DEV-FLOW',
        'device_identifier': 'AA:BB:CC:DD:EE:FF',
        'name': 'Flow Test Device',
        'status': 'offline',
    }
    response = client.post(create_device_url, device_data)
    assert response.status_code == 302  # 重定向到项目详情页面
    assert Device.objects.filter(device_id='DEV-FLOW').exists()
    
    # 获取创建的设备
    device = Device.objects.get(device_id='DEV-FLOW')
    
    # 5. 查看设备详情
    device_detail_url = reverse('iot_devices:device_detail', kwargs={'device_id': 'DEV-FLOW'})
    response = client.get(device_detail_url)
    assert response.status_code == 200
    assert 'device' in response.context
    assert response.context['device'].device_id == 'DEV-FLOW'
    
    # 6. 删除设备
    delete_device_url = reverse('iot_devices:delete_device', kwargs={'device_id': 'DEV-FLOW'})
    response = client.post(delete_device_url)
    assert response.status_code == 302  # 重定向到项目详情页面
    assert not Device.objects.filter(device_id='DEV-FLOW').exists()
    
    # 7. 删除项目
    delete_project_url = reverse('iot_devices:delete_project', kwargs={'project_id': 'PRJ-FLOW'})
    response = client.post(delete_project_url)
    assert response.status_code == 302  # 重定向到项目列表
    assert not Project.objects.filter(project_id='PRJ-FLOW').exists()
```

### 场景2: 设备数据上报与策略触发

```python
# tests/integration/test_device_data_strategy.py
import pytest
import json
from unittest.mock import patch, MagicMock
from iot_devices.models import Project, Device, Sensor, SensorData
from strategy_engine.models import Strategy, Condition, Action
from django.contrib.auth.models import User
from mqtt_client.mqtt import MQTTClient

@pytest.mark.django_db
def test_device_data_triggers_strategy():
    """测试设备数据上报触发策略执行"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    
    # 创建项目和设备
    project = Project.objects.create(project_id='PRJ-STRAT', name='Strategy Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-STRAT',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Strategy Test Device',
        project=project
    )
    
    # 创建传感器
    sensor = Sensor.objects.create(
        name='Temperature Sensor',
        sensor_type='temperature',
        unit='°C',
        device=device,
        value_key='temperature'
    )
    
    # 创建策略和条件
    strategy = Strategy.objects.create(
        name='High Temperature Alert',
        description='温度过高报警',
        owner=user,
        is_active=True
    )
    condition = Condition.objects.create(
        strategy=strategy,
        sensor=sensor,
        operator='gt',  # 大于
        value=30.0,
        value_type='float'
    )
    
    # 创建动作（模拟发送通知）
    notification_action = Action.objects.create(
        strategy=strategy,
        action_type='notification',
        config=json.dumps({
            'message': '温度过高警报！',
            'recipients': ['admin@example.com']
        })
    )
    
    # 模拟MQTT上报数据
    mqtt_client = MQTTClient()
    
    # 创建模拟的MQTT消息 - 温度35度，超过阈值
    message = MagicMock()
    message.topic = f'novacloud/devices/{device.device_id}/data'
    message.payload = json.dumps({
        'temperature': 35.0,
        'humidity': 60,
        'timestamp': 1651234567,
        'device_id': device.device_id
    }).encode('utf-8')
    
    # 模拟策略引擎执行动作的函数
    with patch('strategy_engine.executor.execute_action') as mock_execute:
        # 处理MQTT消息
        mqtt_client._handle_device_data(message)
        
        # 验证传感器数据已保存
        data = SensorData.objects.filter(sensor=sensor).first()
        assert data is not None
        assert data.value_float == 35.0
        
        # 验证策略动作是否被执行
        mock_execute.assert_called()

        # 验证执行的动作参数
        call_args = mock_execute.call_args[0]
        assert call_args[0] == notification_action  # 第一个参数应该是action对象
```

### 场景3: API接口测试

```python
# tests/integration/test_device_api.py
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from iot_devices.models import Project, Device, Sensor, SensorData
from django.contrib.auth.models import User
import json

@pytest.mark.django_db
def test_sensor_data_api():
    """测试传感器数据API"""
    # 创建测试数据
    user = User.objects.create_user(username='apiuser', password='password123')
    project = Project.objects.create(project_id='PRJ-API', name='API Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-API',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='API Test Device',
        project=project
    )
    sensor = Sensor.objects.create(
        name='Humidity Sensor',
        sensor_type='humidity',
        unit='%',
        device=device,
        value_key='humidity'
    )
    
    # 创建APIClient并认证
    client = APIClient()
    client.force_authenticate(user=user)
    
    # 上报传感器数据
    url = reverse('api:sensor_data', kwargs={'sensor_id': sensor.id})
    data = {
        'value': 75.5,  # 湿度值
        'timestamp': '2023-05-01T12:00:00Z'
    }
    response = client.post(url, data, format='json')
    
    # 验证API响应
    assert response.status_code == 201
    assert 'id' in response.data
    
    # 验证数据库中的数据
    assert SensorData.objects.filter(sensor=sensor).exists()
    sensor_data = SensorData.objects.get(id=response.data['id'])
    assert sensor_data.value_float == 75.5
    
    # 获取传感器数据列表
    response = client.get(url)
    
    # 验证API响应
    assert response.status_code == 200
    assert 'results' in response.data
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['value_float'] == 75.5
```

## 四、测试覆盖率

### 运行带覆盖率的测试

使用pytest-cov来生成测试覆盖率报告：

```bash
# 运行测试并生成HTML覆盖率报告
pytest --cov=accounts --cov=iot_devices --cov=mqtt_client --cov=strategy_engine --cov-report=html
```

这将为指定的应用生成HTML格式的覆盖率报告，保存在`htmlcov/`目录中。

### 设置覆盖率目标

对于NovaCloud平台，建议以下覆盖率目标：

1. **初始阶段**: 50-60% 覆盖率，确保基本功能和核心业务逻辑有测试。
2. **中期阶段**: 70-80% 覆盖率，包括大部分错误处理和边界情况。
3. **成熟阶段**: 85%+ 覆盖率，仅忽略一些不太可能执行的错误处理路径。

根据团队和项目特点，可以灵活调整这些目标。

### 重点测试区域

优先测试以下关键区域：

1. **核心业务逻辑**: 设备管理、数据处理、策略引擎。
2. **安全相关功能**: 认证、授权、访问控制。
3. **API接口**: 所有对外暴露的HTTP和MQTT接口。
4. **数据验证**: 表单和API数据验证逻辑。

### 持续集成中的测试

将测试和覆盖率检查集成到CI/CD流程中：

```yaml
# GitHub Actions 示例
name: Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
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
        pip install pytest pytest-django pytest-cov
    - name: Test with pytest
      run: |
        pytest --cov=accounts --cov=iot_devices --cov=mqtt_client --cov=strategy_engine --cov-report=xml --cov-report=term
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
```

## 五、测试最佳实践

### 测试命名约定

- 使用清晰的前缀 `test_` 命名测试函数或方法
- 测试名称应描述被测试的功能或场景，例如 `test_user_can_register` 或 `test_high_temperature_triggers_alert`
- 测试模块应与被测试的模块对应，例如 `test_models.py` 对应 `models.py`

### 使用 Fixture

使用pytest的fixture机制准备测试数据：

```python
# conftest.py
import pytest
from django.contrib.auth.models import User
from iot_devices.models import Project, Device

@pytest.fixture
def test_user():
    """创建测试用户"""
    return User.objects.create_user(username='testuser', password='password123')

@pytest.fixture
def test_project(test_user):
    """创建测试项目"""
    return Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=test_user
    )

@pytest.fixture
def test_device(test_project):
    """创建测试设备"""
    return Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=test_project
    )
```

### 测试隔离

- 使用 `pytest.mark.django_db` 装饰器确保测试之间数据库隔离
- 在每个测试中创建所需的数据，不要依赖于其他测试的数据
- 使用事务或装饰器自动回滚测试中的变更

### 模拟外部依赖

使用`unittest.mock`或`pytest-mock`模拟外部服务：

```python
# 模拟MQTT客户端发布消息
@patch('mqtt_client.mqtt.MQTTClient.publish_message')
def test_send_command_to_device(mock_publish, test_device):
    # 执行发送命令
    result = send_command_to_device(test_device.device_id, 'reboot')
    
    # 验证publish_message被调用
    mock_publish.assert_called_once()
    # 验证调用参数
    args, kwargs = mock_publish.call_args
    assert test_device.device_id in args[0]  # 主题包含设备ID
    assert 'reboot' in args[1]  # 消息内容包含命令
```

### 测试错误情况

不仅测试成功路径，也要测试预期的错误情况：

```python
@pytest.mark.django_db
def test_device_not_found(client):
    """测试访问不存在的设备"""
    # 创建并登录用户
    user = User.objects.create_user(username='testuser', password='password123')
    client.login(username='testuser', password='password123')
    
    # 尝试访问不存在的设备
    url = reverse('iot_devices:device_detail', kwargs={'device_id': 'NONEXISTENT'})
    response = client.get(url)
    
    # 应返回404错误
    assert response.status_code == 404
``` 

## 一、测试框架与工具

### 推荐的测试工具

NovaCloud平台的测试工作建议使用以下工具组合：

- **pytest**: 现代化的测试框架，比Django内置的unittest更加灵活和易用。
- **pytest-django**: 为pytest提供Django集成功能。
- **pytest-cov**: 用于生成测试覆盖率报告。

### 为何选择pytest

pytest相比Django默认的unittest框架有以下优势：

1. **更简洁的语法**：不需要创建测试类，可以直接使用函数编写测试。
2. **强大的fixture机制**：更灵活的依赖注入和测试资源管理。
3. **参数化测试**：可以用不同参数集运行相同的测试。
4. **丰富的插件生态**：如pytest-django, pytest-cov等，提供专业功能。
5. **更友好的错误报告**：展示详细的错误比较和上下文信息。

### 安装测试工具

```bash
pip install pytest pytest-django pytest-cov
```

然后创建一个`pytest.ini`文件配置pytest：

```ini
[pytest]
DJANGO_SETTINGS_MODULE = DjangoNovaCloud.settings
python_files = test_*.py
testpaths = accounts iot_devices mqtt_client strategy_engine
```

## 二、单元测试 (Unit Tests)

单元测试是测试系统最小可测试单元（函数、方法、类）的过程。下面是各模块的单元测试示例。

### 用户认证模块测试

#### 测试 UserRegisterForm

```python
# accounts/tests/test_forms.py
import pytest
from accounts.forms import UserRegisterForm
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_user_register_form_valid():
    """测试有效的用户注册表单"""
    form_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    form = UserRegisterForm(data=form_data)
    assert form.is_valid(), f"表单验证失败: {form.errors}"

@pytest.mark.django_db
def test_user_register_form_duplicate_email():
    """测试使用已存在的邮箱注册"""
    # 创建一个用户
    User.objects.create_user(username='existinguser', email='exists@example.com', password='password123')
    
    # 使用相同的邮箱尝试注册
    form_data = {
        'username': 'newuser',
        'email': 'exists@example.com',  # 这个邮箱已经被使用
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    form = UserRegisterForm(data=form_data)
    assert not form.is_valid()
    assert 'email' in form.errors
    assert '该邮箱已被注册' in str(form.errors['email'])
```

#### 测试 UserLoginForm

```python
# accounts/tests/test_forms.py
import pytest
from accounts.forms import UserLoginForm
from django.contrib.auth.models import User
from django.test import RequestFactory

@pytest.mark.django_db
def test_user_login_with_username():
    """测试使用用户名登录"""
    # 创建用户
    User.objects.create_user(username='testuser', email='test@example.com', password='password123')
    
    # 创建请求对象
    factory = RequestFactory()
    request = factory.get('/')
    
    # 使用用户名登录
    form_data = {
        'username': 'testuser',
        'password': 'password123',
    }
    form = UserLoginForm(request=request, data=form_data)
    assert form.is_valid(), f"用户名登录验证失败: {form.errors}"

@pytest.mark.django_db
def test_user_login_with_email():
    """测试使用邮箱登录"""
    # 创建用户
    User.objects.create_user(username='testuser', email='test@example.com', password='password123')
    
    # 创建请求对象
    factory = RequestFactory()
    request = factory.get('/')
    
    # 使用邮箱登录
    form_data = {
        'username': 'test@example.com',  # 使用邮箱而非用户名
        'password': 'password123',
    }
    form = UserLoginForm(request=request, data=form_data)
    assert form.is_valid(), f"邮箱登录验证失败: {form.errors}"

@pytest.mark.django_db
def test_user_login_invalid_credentials():
    """测试无效的登录凭据"""
    # 创建用户
    User.objects.create_user(username='testuser', email='test@example.com', password='password123')
    
    # 创建请求对象
    factory = RequestFactory()
    request = factory.get('/')
    
    # 使用错误的密码尝试登录
    form_data = {
        'username': 'testuser',
        'password': 'wrongpassword',
    }
    form = UserLoginForm(request=request, data=form_data)
    assert not form.is_valid()
    assert '用户名/邮箱或密码不正确' in str(form.errors)
```

#### 测试注册视图

```python
# accounts/tests/test_views.py
import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_register_view_get(client):
    """测试GET请求注册视图"""
    url = reverse('accounts:register')
    response = client.get(url)
    assert response.status_code == 200
    assert 'form' in response.context
    assert 'accounts/register.html' in [t.name for t in response.templates]

@pytest.mark.django_db
def test_register_view_post_success(client):
    """测试成功注册"""
    url = reverse('accounts:register')
    data = {
        'username': 'newuser',
        'email': 'new@example.com',
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    response = client.post(url, data)
    # 检查是否重定向到登录页面
    assert response.status_code == 302
    assert response.url == reverse('accounts:login')
    # 验证用户是否被创建
    assert User.objects.filter(username='newuser').exists()

@pytest.mark.django_db
def test_register_view_post_invalid(client):
    """测试无效注册数据"""
    url = reverse('accounts:register')
    data = {
        'username': 'newuser',
        'email': 'invalid-email',  # 无效的邮箱格式
        'password1': 'pass1',
        'password2': 'pass2',  # 密码不匹配
    }
    response = client.post(url, data)
    assert response.status_code == 200  # 表单有错误，返回同一页面
    assert 'form' in response.context
    assert response.context['form'].errors  # 表单包含错误
    # 验证用户未被创建
    assert not User.objects.filter(username='newuser').exists()
```

### IoT设备模块测试

#### 测试 Device 模型

```python
# iot_devices/tests/test_models.py
import pytest
from iot_devices.models import Project, Device
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_device_key_generation():
    """测试设备密钥自动生成"""
    # 创建用户和项目
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=user
    )
    
    # 创建设备，不提供device_key
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    
    # 验证密钥已生成
    assert device.device_key is not None
    assert len(device.device_key) == 32  # uuid4().hex 生成32个字符
```

#### 测试 ProjectForm 和 DeviceForm

```python
# iot_devices/tests/test_forms.py
import pytest
from django.contrib.auth.models import User
from iot_devices.models import Project
from iot_devices.forms import ProjectForm, DeviceForm

@pytest.mark.django_db
def test_project_form_valid():
    """测试有效的项目表单"""
    user = User.objects.create_user(username='testuser', password='password123')
    form_data = {
        'project_id': 'PRJ-TEST',
        'name': 'Test Project',
        'description': 'This is a test project'
    }
    form = ProjectForm(data=form_data, user=user)
    assert form.is_valid(), f"表单验证失败: {form.errors}"

@pytest.mark.django_db
def test_project_form_invalid_id():
    """测试无效的项目ID"""
    user = User.objects.create_user(username='testuser', password='password123')
    form_data = {
        'project_id': 'PRJ TEST',  # 包含空格，不合法
        'name': 'Test Project',
    }
    form = ProjectForm(data=form_data, user=user)
    assert not form.is_valid()
    assert 'project_id' in form.errors

@pytest.mark.django_db
def test_device_form_with_project():
    """测试有效的设备表单，指定项目"""
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=user
    )
    
    form_data = {
        'device_id': 'DEV-TEST',
        'device_identifier': 'AA:BB:CC:DD:EE:FF',
        'name': 'Test Device',
        'project': project.id,
        'status': 'offline'
    }
    form = DeviceForm(data=form_data, user=user)
    assert form.is_valid(), f"表单验证失败: {form.errors}"

@pytest.mark.django_db
def test_device_form_invalid_identifier():
    """测试无效的设备标识符"""
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=user
    )
    
    form_data = {
        'device_id': 'DEV-TEST',
        'device_identifier': 'INVALID MAC',  # 无效的MAC地址格式
        'name': 'Test Device',
        'project': project.id,
        'status': 'offline'
    }
    form = DeviceForm(data=form_data, user=user)
    assert not form.is_valid()
    assert 'device_identifier' in form.errors
```

#### 测试项目列表视图（权限）

```python
# iot_devices/tests/test_views.py
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from iot_devices.models import Project

@pytest.mark.django_db
def test_project_list_view_authenticated(client):
    """测试已登录用户可以访问项目列表"""
    # 创建用户
    user = User.objects.create_user(username='testuser', password='password123')
    # 创建一些项目
    Project.objects.create(project_id='PRJ-1', name='Project 1', owner=user)
    Project.objects.create(project_id='PRJ-2', name='Project 2', owner=user)
    
    # 登录
    client.login(username='testuser', password='password123')
    
    # 访问项目列表
    url = reverse('iot_devices:project_list')
    response = client.get(url)
    
    # 验证响应
    assert response.status_code == 200
    assert 'projects' in response.context
    assert len(response.context['projects']) == 2

@pytest.mark.django_db
def test_project_list_view_unauthenticated(client):
    """测试未登录用户被重定向到登录页面"""
    url = reverse('iot_devices:project_list')
    response = client.get(url)
    
    # 验证重定向
    assert response.status_code == 302
    assert reverse('accounts:login') in response.url

@pytest.mark.django_db
def test_project_list_view_only_shows_user_projects(client):
    """测试用户只能看到自己的项目"""
    # 创建两个用户
    user1 = User.objects.create_user(username='user1', password='password123')
    user2 = User.objects.create_user(username='user2', password='password123')
    
    # 为每个用户创建项目
    Project.objects.create(project_id='PRJ-U1', name='User1 Project', owner=user1)
    Project.objects.create(project_id='PRJ-U2', name='User2 Project', owner=user2)
    
    # 用户1登录
    client.login(username='user1', password='password123')
    
    # 访问项目列表
    url = reverse('iot_devices:project_list')
    response = client.get(url)
    
    # 验证用户1只能看到自己的项目
    assert response.status_code == 200
    assert 'projects' in response.context
    assert len(response.context['projects']) == 1
    assert response.context['projects'][0].project_id == 'PRJ-U1'
```

### MQTT消息处理测试

#### 测试数据上报处理

```python
# mqtt_client/tests/test_mqtt_handler.py
import pytest
import json
from unittest.mock import patch, MagicMock
from mqtt_client.mqtt import MQTTClient
from iot_devices.models import Project, Device, Sensor, SensorData
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_handle_device_data():
    """测试处理设备上报的传感器数据"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    sensor = Sensor.objects.create(
        name='Temperature Sensor',
        sensor_type='temperature',
        unit='°C',
        device=device,
        value_key='temperature'
    )
    
    # 模拟MQTT客户端
    mqtt_client = MQTTClient()
    
    # 创建模拟的MQTT消息
    message = MagicMock()
    message.topic = 'novacloud/devices/DEV-TEST/data'
    message.payload = json.dumps({
        'temperature': 25.5,
        'humidity': 60,
        'timestamp': 1651234567,
        'device_id': 'DEV-TEST'
    }).encode('utf-8')
    
    # 调用处理函数
    with patch.object(mqtt_client, 'client') as mock_client:
        mqtt_client._handle_device_data(message)
    
    # 验证数据保存
    data = SensorData.objects.filter(sensor=sensor).first()
    assert data is not None
    assert data.value_float == 25.5
    
    # 验证设备状态更新
    device.refresh_from_db()
    assert device.status == 'online'
    assert device.last_seen is not None
```

#### 测试设备认证

```python
# mqtt_client/tests/test_authentication.py
import pytest
from mqtt_client.auth import authenticate_device
from iot_devices.models import Project, Device
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_device_authentication_success():
    """测试设备认证成功"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    # 设备密钥在创建时自动生成
    device_key = device.device_key
    
    # 调用认证函数
    result = authenticate_device('DEV-TEST', device_key)
    
    # 验证结果
    assert result is True

@pytest.mark.django_db
def test_device_authentication_wrong_key():
    """测试设备认证失败 - 错误的密钥"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    
    # 使用错误的密钥
    wrong_key = 'wrong_key'
    
    # 调用认证函数
    result = authenticate_device('DEV-TEST', wrong_key)
    
    # 验证结果
    assert result is False

@pytest.mark.django_db
def test_device_authentication_nonexistent_device():
    """测试设备认证失败 - 不存在的设备"""
    # 调用认证函数
    result = authenticate_device('NONEXISTENT', 'any_key')
    
    # 验证结果
    assert result is False
```

### 策略引擎测试

```python
# strategy_engine/tests/test_evaluator.py
import pytest
from strategy_engine.evaluator import evaluate_condition
from strategy_engine.models import Strategy, Condition
from iot_devices.models import Project, Device, Sensor, SensorData
from django.contrib.auth.models import User
from datetime import datetime

@pytest.mark.django_db
def test_evaluate_greater_than_condition():
    """测试大于条件的评估"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    project = Project.objects.create(project_id='PRJ-TEST', name='Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=project
    )
    sensor = Sensor.objects.create(
        name='Temperature Sensor',
        sensor_type='temperature',
        unit='°C',
        device=device,
        value_key='temperature'
    )
    
    # 创建传感器数据
    SensorData.objects.create(
        sensor=sensor,
        value_float=30.0,  # 高温值
        timestamp=datetime.now()
    )
    
    # 创建策略和条件
    strategy = Strategy.objects.create(
        name='High Temperature Alert',
        description='温度过高报警',
        owner=user,
        is_active=True
    )
    condition = Condition.objects.create(
        strategy=strategy,
        sensor=sensor,
        operator='gt',  # 大于
        value=25.0,
        value_type='float'
    )
    
    # 评估条件
    result = evaluate_condition(condition)
    
    # 验证结果
    assert result is True, "温度大于阈值，条件应该满足"
```

## 三、集成测试 (Integration Tests)

集成测试用于测试多个组件一起工作时的功能。

### 场景1: 用户-项目-设备流程

```python
# tests/integration/test_user_project_device_flow.py
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from iot_devices.models import Project, Device

@pytest.mark.django_db
def test_complete_user_project_device_flow(client):
    """测试完整流程：用户注册->登录->创建项目->添加设备->查看设备->删除设备->删除项目"""
    
    # 1. 用户注册
    register_url = reverse('accounts:register')
    register_data = {
        'username': 'flowuser',
        'email': 'flow@example.com',
        'password1': 'securepassword123',
        'password2': 'securepassword123',
    }
    response = client.post(register_url, register_data)
    assert response.status_code == 302  # 重定向到登录页面
    assert User.objects.filter(username='flowuser').exists()
    
    # 2. 用户登录
    login_url = reverse('accounts:login')
    login_data = {
        'username': 'flowuser',
        'password': 'securepassword123',
    }
    response = client.post(login_url, login_data)
    assert response.status_code == 302  # 重定向到首页
    
    # 3. 创建项目
    create_project_url = reverse('iot_devices:create_project')
    project_data = {
        'project_id': 'PRJ-FLOW',
        'name': 'Flow Test Project',
        'description': 'Project for integration testing',
    }
    response = client.post(create_project_url, project_data)
    assert response.status_code == 302  # 重定向到项目列表
    assert Project.objects.filter(project_id='PRJ-FLOW').exists()
    
    # 获取创建的项目
    project = Project.objects.get(project_id='PRJ-FLOW')
    
    # 4. 在项目中添加设备
    create_device_url = reverse('iot_devices:create_device', kwargs={'project_id': 'PRJ-FLOW'})
    device_data = {
        'device_id': 'DEV-FLOW',
        'device_identifier': 'AA:BB:CC:DD:EE:FF',
        'name': 'Flow Test Device',
        'status': 'offline',
    }
    response = client.post(create_device_url, device_data)
    assert response.status_code == 302  # 重定向到项目详情页面
    assert Device.objects.filter(device_id='DEV-FLOW').exists()
    
    # 获取创建的设备
    device = Device.objects.get(device_id='DEV-FLOW')
    
    # 5. 查看设备详情
    device_detail_url = reverse('iot_devices:device_detail', kwargs={'device_id': 'DEV-FLOW'})
    response = client.get(device_detail_url)
    assert response.status_code == 200
    assert 'device' in response.context
    assert response.context['device'].device_id == 'DEV-FLOW'
    
    # 6. 删除设备
    delete_device_url = reverse('iot_devices:delete_device', kwargs={'device_id': 'DEV-FLOW'})
    response = client.post(delete_device_url)
    assert response.status_code == 302  # 重定向到项目详情页面
    assert not Device.objects.filter(device_id='DEV-FLOW').exists()
    
    # 7. 删除项目
    delete_project_url = reverse('iot_devices:delete_project', kwargs={'project_id': 'PRJ-FLOW'})
    response = client.post(delete_project_url)
    assert response.status_code == 302  # 重定向到项目列表
    assert not Project.objects.filter(project_id='PRJ-FLOW').exists()
```

### 场景2: 设备数据上报与策略触发

```python
# tests/integration/test_device_data_strategy.py
import pytest
import json
from unittest.mock import patch, MagicMock
from iot_devices.models import Project, Device, Sensor, SensorData
from strategy_engine.models import Strategy, Condition, Action
from django.contrib.auth.models import User
from mqtt_client.mqtt import MQTTClient

@pytest.mark.django_db
def test_device_data_triggers_strategy():
    """测试设备数据上报触发策略执行"""
    # 创建测试数据
    user = User.objects.create_user(username='testuser', password='password123')
    
    # 创建项目和设备
    project = Project.objects.create(project_id='PRJ-STRAT', name='Strategy Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-STRAT',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Strategy Test Device',
        project=project
    )
    
    # 创建传感器
    sensor = Sensor.objects.create(
        name='Temperature Sensor',
        sensor_type='temperature',
        unit='°C',
        device=device,
        value_key='temperature'
    )
    
    # 创建策略和条件
    strategy = Strategy.objects.create(
        name='High Temperature Alert',
        description='温度过高报警',
        owner=user,
        is_active=True
    )
    condition = Condition.objects.create(
        strategy=strategy,
        sensor=sensor,
        operator='gt',  # 大于
        value=30.0,
        value_type='float'
    )
    
    # 创建动作（模拟发送通知）
    notification_action = Action.objects.create(
        strategy=strategy,
        action_type='notification',
        config=json.dumps({
            'message': '温度过高警报！',
            'recipients': ['admin@example.com']
        })
    )
    
    # 模拟MQTT上报数据
    mqtt_client = MQTTClient()
    
    # 创建模拟的MQTT消息 - 温度35度，超过阈值
    message = MagicMock()
    message.topic = f'novacloud/devices/{device.device_id}/data'
    message.payload = json.dumps({
        'temperature': 35.0,
        'humidity': 60,
        'timestamp': 1651234567,
        'device_id': device.device_id
    }).encode('utf-8')
    
    # 模拟策略引擎执行动作的函数
    with patch('strategy_engine.executor.execute_action') as mock_execute:
        # 处理MQTT消息
        mqtt_client._handle_device_data(message)
        
        # 验证传感器数据已保存
        data = SensorData.objects.filter(sensor=sensor).first()
        assert data is not None
        assert data.value_float == 35.0
        
        # 验证策略动作是否被执行
        mock_execute.assert_called()

        # 验证执行的动作参数
        call_args = mock_execute.call_args[0]
        assert call_args[0] == notification_action  # 第一个参数应该是action对象
```

### 场景3: API接口测试

```python
# tests/integration/test_device_api.py
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from iot_devices.models import Project, Device, Sensor, SensorData
from django.contrib.auth.models import User
import json

@pytest.mark.django_db
def test_sensor_data_api():
    """测试传感器数据API"""
    # 创建测试数据
    user = User.objects.create_user(username='apiuser', password='password123')
    project = Project.objects.create(project_id='PRJ-API', name='API Test Project', owner=user)
    device = Device.objects.create(
        device_id='DEV-API',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='API Test Device',
        project=project
    )
    sensor = Sensor.objects.create(
        name='Humidity Sensor',
        sensor_type='humidity',
        unit='%',
        device=device,
        value_key='humidity'
    )
    
    # 创建APIClient并认证
    client = APIClient()
    client.force_authenticate(user=user)
    
    # 上报传感器数据
    url = reverse('api:sensor_data', kwargs={'sensor_id': sensor.id})
    data = {
        'value': 75.5,  # 湿度值
        'timestamp': '2023-05-01T12:00:00Z'
    }
    response = client.post(url, data, format='json')
    
    # 验证API响应
    assert response.status_code == 201
    assert 'id' in response.data
    
    # 验证数据库中的数据
    assert SensorData.objects.filter(sensor=sensor).exists()
    sensor_data = SensorData.objects.get(id=response.data['id'])
    assert sensor_data.value_float == 75.5
    
    # 获取传感器数据列表
    response = client.get(url)
    
    # 验证API响应
    assert response.status_code == 200
    assert 'results' in response.data
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['value_float'] == 75.5
```

## 四、测试覆盖率

### 运行带覆盖率的测试

使用pytest-cov来生成测试覆盖率报告：

```bash
# 运行测试并生成HTML覆盖率报告
pytest --cov=accounts --cov=iot_devices --cov=mqtt_client --cov=strategy_engine --cov-report=html
```

这将为指定的应用生成HTML格式的覆盖率报告，保存在`htmlcov/`目录中。

### 设置覆盖率目标

对于NovaCloud平台，建议以下覆盖率目标：

1. **初始阶段**: 50-60% 覆盖率，确保基本功能和核心业务逻辑有测试。
2. **中期阶段**: 70-80% 覆盖率，包括大部分错误处理和边界情况。
3. **成熟阶段**: 85%+ 覆盖率，仅忽略一些不太可能执行的错误处理路径。

根据团队和项目特点，可以灵活调整这些目标。

### 重点测试区域

优先测试以下关键区域：

1. **核心业务逻辑**: 设备管理、数据处理、策略引擎。
2. **安全相关功能**: 认证、授权、访问控制。
3. **API接口**: 所有对外暴露的HTTP和MQTT接口。
4. **数据验证**: 表单和API数据验证逻辑。

### 持续集成中的测试

将测试和覆盖率检查集成到CI/CD流程中：

```yaml
# GitHub Actions 示例
name: Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
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
        pip install pytest pytest-django pytest-cov
    - name: Test with pytest
      run: |
        pytest --cov=accounts --cov=iot_devices --cov=mqtt_client --cov=strategy_engine --cov-report=xml --cov-report=term
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
```

## 五、测试最佳实践

### 测试命名约定

- 使用清晰的前缀 `test_` 命名测试函数或方法
- 测试名称应描述被测试的功能或场景，例如 `test_user_can_register` 或 `test_high_temperature_triggers_alert`
- 测试模块应与被测试的模块对应，例如 `test_models.py` 对应 `models.py`

### 使用 Fixture

使用pytest的fixture机制准备测试数据：

```python
# conftest.py
import pytest
from django.contrib.auth.models import User
from iot_devices.models import Project, Device

@pytest.fixture
def test_user():
    """创建测试用户"""
    return User.objects.create_user(username='testuser', password='password123')

@pytest.fixture
def test_project(test_user):
    """创建测试项目"""
    return Project.objects.create(
        project_id='PRJ-TEST',
        name='Test Project',
        owner=test_user
    )

@pytest.fixture
def test_device(test_project):
    """创建测试设备"""
    return Device.objects.create(
        device_id='DEV-TEST',
        device_identifier='AA:BB:CC:DD:EE:FF',
        name='Test Device',
        project=test_project
    )
```

### 测试隔离

- 使用 `pytest.mark.django_db` 装饰器确保测试之间数据库隔离
- 在每个测试中创建所需的数据，不要依赖于其他测试的数据
- 使用事务或装饰器自动回滚测试中的变更

### 模拟外部依赖

使用`unittest.mock`或`pytest-mock`模拟外部服务：

```python
# 模拟MQTT客户端发布消息
@patch('mqtt_client.mqtt.MQTTClient.publish_message')
def test_send_command_to_device(mock_publish, test_device):
    # 执行发送命令
    result = send_command_to_device(test_device.device_id, 'reboot')
    
    # 验证publish_message被调用
    mock_publish.assert_called_once()
    # 验证调用参数
    args, kwargs = mock_publish.call_args
    assert test_device.device_id in args[0]  # 主题包含设备ID
    assert 'reboot' in args[1]  # 消息内容包含命令
```

### 测试错误情况

不仅测试成功路径，也要测试预期的错误情况：

```python
@pytest.mark.django_db
def test_device_not_found(client):
    """测试访问不存在的设备"""
    # 创建并登录用户
    user = User.objects.create_user(username='testuser', password='password123')
    client.login(username='testuser', password='password123')
    
    # 尝试访问不存在的设备
    url = reverse('iot_devices:device_detail', kwargs={'device_id': 'NONEXISTENT'})
    response = client.get(url)
    
    # 应返回404错误
    assert response.status_code == 404
``` 
 