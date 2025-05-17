from django.db import models
from django.conf import settings
import uuid


class Project(models.Model):
    """项目模型"""
    project_id = models.CharField('项目号', max_length=20, unique=True, help_text="例如：PRJ-XXXXXX")
    name = models.CharField('项目名称', max_length=100)
    description = models.TextField('项目描述', blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='所有者')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.project_id})"


class Device(models.Model):
    """设备模型"""
    STATUS_CHOICES = (
        ('online', '在线'),
        ('offline', '离线'),
        ('unregistered', '未注册'),
    )
    
    PROTOCOL_CHOICES = (
        ('mqtt', 'MQTT'),
        ('tcp', 'TCP原生'),
    )
    
    device_id = models.CharField('设备号', max_length=20, unique=True, help_text="例如：DEV-YYYYYY")
    device_identifier = models.CharField('设备标识', max_length=100, unique=True, help_text="可以是MAC地址、序列号等")
    device_key = models.CharField('设备密钥', max_length=64, blank=True, help_text="用于设备认证")
    name = models.CharField('设备名称', max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='devices', verbose_name='所属项目')
    status = models.CharField('设备状态', max_length=20, choices=STATUS_CHOICES, default='unregistered')
    protocol_type = models.CharField('通信协议', max_length=20, choices=PROTOCOL_CHOICES, default='mqtt')
    last_seen = models.DateTimeField('最后在线时间', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.device_id})"
    
    def save(self, *args, **kwargs):
        """保存前自动生成设备密钥（如果为空）"""
        if not self.device_key:
            self.device_key = uuid.uuid4().hex
        super().save(*args, **kwargs)


class Sensor(models.Model):
    """传感器模型"""
    name = models.CharField('传感器名称', max_length=100)
    sensor_type = models.CharField('传感器类型', max_length=50, help_text="例如：temperature, humidity")
    unit = models.CharField('单位', max_length=20, blank=True, null=True, help_text="例如：°C, %")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sensors', verbose_name='所属设备')
    value_key = models.CharField('值键名', max_length=50, help_text="用于从设备消息中提取该传感器值的键名")
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '传感器'
        verbose_name_plural = '传感器'
        ordering = ['device', 'name']

    def __str__(self):
        return f"{self.name} ({self.device.name})"


class Actuator(models.Model):
    """执行器模型"""
    name = models.CharField('执行器名称', max_length=100)
    actuator_type = models.CharField('执行器类型', max_length=50, help_text="例如：switch, dimmer")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='actuators', verbose_name='所属设备')
    command_key = models.CharField('命令键名', max_length=50, help_text="用于向设备发送命令的标识")
    current_state = models.CharField('当前状态', max_length=20, blank=True, null=True, help_text="例如：ON, OFF, 50%")
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '执行器'
        verbose_name_plural = '执行器'
        ordering = ['device', 'name']

    def __str__(self):
        return f"{self.name} ({self.device.name})"


class SensorData(models.Model):
    """传感器数据模型"""
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='data_points', verbose_name='传感器')
    timestamp = models.DateTimeField('记录时间', auto_now_add=True)
    value_float = models.FloatField('浮点数值', null=True, blank=True)
    value_string = models.CharField('字符串值', max_length=100, null=True, blank=True)
    value_boolean = models.BooleanField('布尔值', null=True, blank=True)

    class Meta:
        verbose_name = '传感器数据'
        verbose_name_plural = '传感器数据'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sensor', '-timestamp'])
        ]

    def __str__(self):
        if self.value_float is not None:
            value = self.value_float
        elif self.value_string is not None:
            value = self.value_string
        elif self.value_boolean is not None:
            value = "是" if self.value_boolean else "否"
        else:
            value = "无数据"
        return f"{self.sensor.name}: {value} ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
