from django.db import models
from django.conf import settings
from iot_devices.models import Project, Device, Sensor, Actuator
import json
import logging

logger = logging.getLogger(__name__)


class Strategy(models.Model):
    """策略模型"""
    name = models.CharField('策略名称', max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='strategies', verbose_name='所属项目')
    description = models.TextField('策略描述', blank=True, null=True)
    is_enabled = models.BooleanField('是否启用', default=True)
    trigger_source_device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='trigger_strategies', verbose_name='触发设备')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '策略'
        verbose_name_plural = '策略'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.project.name})"
    
    def evaluate_conditions(self, sensor_data):
        """
        评估策略条件
        :param sensor_data: SensorData实例
        :return: 条件是否满足
        """
        if not self.is_enabled:
            return False
        
        # 检查传感器是否属于触发设备
        if sensor_data.sensor.device != self.trigger_source_device:
            return False
        
        # 获取所有条件
        conditions = self.conditions.all().order_by('id')
        if not conditions:
            logger.warning(f"策略 {self.name} 没有条件")
            return False
        
        result = None
        
        # 逐个评估条件
        for i, condition in enumerate(conditions):
            # 如果当前传感器数据不是条件关注的传感器，跳过
            if condition.sensor != sensor_data.sensor:
                continue
                
            # 检查传感器值是否符合条件
            current_result = condition.evaluate(sensor_data)
            
            if i == 0:
                # 第一个条件的结果
                result = current_result
            else:
                # 根据逻辑运算符组合条件结果
                prev_condition = conditions[i-1]
                if prev_condition.logical_operator_to_next == 'AND':
                    result = result and current_result
                elif prev_condition.logical_operator_to_next == 'OR':
                    result = result or current_result
        
        # 如果没有评估任何条件（没有匹配的传感器），返回False
        if result is None:
            return False
            
        return result
    
    def execute_actions(self, sensor_data):
        """
        执行策略动作
        :param sensor_data: 触发的传感器数据
        """
        for action in self.actions.all():
            try:
                action.execute(sensor_data)
                # 记录执行日志
                StrategyLog.objects.create(
                    strategy=self,
                    sensor_data=sensor_data,
                    action=action,
                    result=True,
                    message=f"动作 {action.get_action_type_display()} 执行成功"
                )
            except Exception as e:
                # 记录错误日志
                logger.error(f"执行策略动作时出错: {str(e)}")
                StrategyLog.objects.create(
                    strategy=self,
                    sensor_data=sensor_data,
                    action=action,
                    result=False,
                    message=f"执行失败: {str(e)}"
                )


class Condition(models.Model):
    """条件模型"""
    OPERATOR_CHOICES = (
        ('>', '大于'),
        ('<', '小于'),
        ('>=', '大于等于'),
        ('<=', '小于等于'),
        ('==', '等于'),
        ('!=', '不等于'),
    )
    
    LOGICAL_OPERATOR_CHOICES = (
        ('AND', '与'),
        ('OR', '或'),
    )
    
    VALUE_TYPE_CHOICES = (
        ('float', '数值'),
        ('string', '文本'),
        ('boolean', '布尔值'),
    )
    
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='conditions', verbose_name='所属策略')
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='conditions', verbose_name='传感器')
    metric_key = models.CharField('指标键名', max_length=50, default='value', help_text='通常为"value"')
    operator = models.CharField('比较运算符', max_length=2, choices=OPERATOR_CHOICES)
    threshold_value_type = models.CharField('阈值类型', max_length=10, choices=VALUE_TYPE_CHOICES, default='float')
    threshold_value_float = models.FloatField('数值阈值', null=True, blank=True)
    threshold_value_string = models.CharField('文本阈值', max_length=100, null=True, blank=True)
    threshold_value_boolean = models.BooleanField('布尔阈值', null=True, blank=True)
    logical_operator_to_next = models.CharField('与下一条件的逻辑关系', max_length=3, choices=LOGICAL_OPERATOR_CHOICES, null=True, blank=True)
    
    class Meta:
        verbose_name = '条件'
        verbose_name_plural = '条件'
    
    def __str__(self):
        threshold = self.get_threshold_value()
        return f"{self.sensor.name} {self.get_operator_display()} {threshold}"
    
    def get_threshold_value(self):
        """获取阈值"""
        if self.threshold_value_type == 'float':
            return self.threshold_value_float
        elif self.threshold_value_type == 'string':
            return self.threshold_value_string
        elif self.threshold_value_type == 'boolean':
            return self.threshold_value_boolean
        return None
    
    def evaluate(self, sensor_data):
        """
        评估条件是否满足
        :param sensor_data: SensorData实例
        :return: 条件是否满足
        """
        # 获取传感器数据值
        if self.threshold_value_type == 'float':
            actual_value = sensor_data.value_float
        elif self.threshold_value_type == 'string':
            actual_value = sensor_data.value_string
        elif self.threshold_value_type == 'boolean':
            actual_value = sensor_data.value_boolean
        else:
            return False
        
        # 获取阈值
        threshold = self.get_threshold_value()
        
        # 如果没有值或阈值，返回False
        if actual_value is None or threshold is None:
            return False
        
        # 根据运算符比较值
        if self.operator == '>':
            return actual_value > threshold
        elif self.operator == '<':
            return actual_value < threshold
        elif self.operator == '>=':
            return actual_value >= threshold
        elif self.operator == '<=':
            return actual_value <= threshold
        elif self.operator == '==':
            return actual_value == threshold
        elif self.operator == '!=':
            return actual_value != threshold
        
        return False


class Action(models.Model):
    """动作模型"""
    ACTION_TYPE_CHOICES = (
        ('send_email_notification', '发送邮件通知'),
        ('control_actuator', '控制执行器'),
        ('webhook', 'WebHook调用'),
    )
    
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='actions', verbose_name='所属策略')
    action_type = models.CharField('动作类型', max_length=50, choices=ACTION_TYPE_CHOICES)
    
    # 邮件通知相关字段
    recipient_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, verbose_name='接收用户')
    recipient_email = models.EmailField('接收邮箱', null=True, blank=True)
    notification_subject_template = models.CharField('通知主题模板', max_length=200, null=True, blank=True)
    notification_body_template = models.TextField('通知内容模板', null=True, blank=True, 
                                               help_text='可使用占位符如 {{device.name}}, {{sensor.name}}, {{value}}')
    
    # 执行器控制相关字段
    target_actuator = models.ForeignKey(Actuator, on_delete=models.CASCADE, null=True, blank=True, verbose_name='目标执行器')
    actuator_command = models.CharField('执行器命令', max_length=50, null=True, blank=True, 
                                      help_text='简单命令如"ON"/"OFF"，或复杂命令的JSON字符串')
    
    # WebHook相关字段
    webhook_url = models.URLField('WebHook URL', null=True, blank=True)
    webhook_method = models.CharField('HTTP方法', max_length=10, default='POST', null=True, blank=True)
    webhook_payload_template = models.TextField('WebHook负载模板', null=True, blank=True, 
                                             help_text='JSON模板，可包含占位符')
    
    class Meta:
        verbose_name = '动作'
        verbose_name_plural = '动作'
    
    def __str__(self):
        if self.action_type == 'send_email_notification':
            recipient = self.recipient_user or self.recipient_email or '项目所有者'
            return f"发送邮件通知给 {recipient}"
        elif self.action_type == 'control_actuator':
            if self.target_actuator:
                return f"控制执行器 {self.target_actuator.name} => {self.actuator_command}"
            return "控制执行器"
        elif self.action_type == 'webhook':
            return f"WebHook调用 {self.webhook_url}"
        return f"动作: {self.get_action_type_display()}"
    
    def execute(self, sensor_data):
        """
        执行动作
        :param sensor_data: 触发的传感器数据
        """
        if self.action_type == 'send_email_notification':
            self._send_email_notification(sensor_data)
        elif self.action_type == 'control_actuator':
            self._control_actuator(sensor_data)
        elif self.action_type == 'webhook':
            self._call_webhook(sensor_data)
    
    def _send_email_notification(self, sensor_data):
        """发送邮件通知"""
        from django.core.mail import send_mail
        from django.template import Template, Context
        
        # 确定接收者
        recipients = []
        if self.recipient_email:
            recipients.append(self.recipient_email)
        if self.recipient_user and self.recipient_user.email:
            recipients.append(self.recipient_user.email)
        if not recipients:
            # 如果没有指定接收者，发送给项目所有者
            if self.strategy.project.owner.email:
                recipients.append(self.strategy.project.owner.email)
        
        if not recipients:
            raise Exception("没有可用的邮件接收者")
        
        # 准备模板上下文
        sensor = sensor_data.sensor
        device = sensor.device
        value = sensor_data.value_float or sensor_data.value_string or sensor_data.value_boolean
        
        context = Context({
            'device': device,
            'sensor': sensor,
            'value': value,
            'strategy': self.strategy,
            'timestamp': sensor_data.timestamp,
        })
        
        # 渲染主题和内容
        subject_template = Template(self.notification_subject_template or f"NovaCloud策略触发: {self.strategy.name}")
        body_template = Template(self.notification_body_template or 
                                f"设备 {{{{ device.name }}}} 的传感器 {{{{ sensor.name }}}} 当前值为 {{{{ value }}}}，触发了策略 {{{{ strategy.name }}}}。")
        
        subject = subject_template.render(context)
        body = body_template.render(context)
        
        # 发送邮件
        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # 使用默认发件人
            recipient_list=recipients,
            fail_silently=False,
        )
        
        logger.info(f"已发送策略触发通知邮件到 {', '.join(recipients)}")
    
    def _control_actuator(self, sensor_data):
        """控制执行器"""
        if not self.target_actuator:
            raise Exception("未指定目标执行器")
        
        # 获取执行器命令
        command = self.actuator_command
        if not command:
            raise Exception("未指定执行器命令")
        
        # 准备发送的命令数据
        try:
            # 尝试解析为JSON，如果不是有效的JSON，则作为普通字符串使用
            command_data = json.loads(command)
        except json.JSONDecodeError:
            # 简单命令字符串，用执行器的command_key作为键
            command_data = {
                self.target_actuator.command_key: command
            }
        
        # 添加命令标识
        command_data['command'] = 'control_actuator'
        
        # 引入MQTT客户端
        from mqtt_client.mqtt import mqtt_client
        
        # 发送命令到设备
        result = mqtt_client.publish_command(
            self.target_actuator.device.device_id,
            command_data
        )
        
        if not result:
            raise Exception(f"向设备 {self.target_actuator.device.name} 发送命令失败")
        
        logger.info(f"已向设备 {self.target_actuator.device.name} 的执行器 {self.target_actuator.name} 发送命令: {command}")
    
    def _call_webhook(self, sensor_data):
        """调用WebHook"""
        import requests
        from django.template import Template, Context
        
        if not self.webhook_url:
            raise Exception("未指定WebHook URL")
        
        # 准备模板上下文
        sensor = sensor_data.sensor
        device = sensor.device
        value = sensor_data.value_float or sensor_data.value_string or sensor_data.value_boolean
        
        context = Context({
            'device': {
                'id': device.device_id,
                'name': device.name,
                'status': device.status,
            },
            'sensor': {
                'id': sensor.id,
                'name': sensor.name,
                'type': sensor.sensor_type,
            },
            'value': value,
            'strategy': {
                'id': self.strategy.id,
                'name': self.strategy.name,
            },
            'timestamp': sensor_data.timestamp.isoformat(),
        })
        
        # 渲染WebHook负载
        if self.webhook_payload_template:
            template = Template(self.webhook_payload_template)
            payload_str = template.render(context)
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                raise Exception(f"WebHook负载模板不是有效的JSON: {payload_str}")
        else:
            # 默认负载
            payload = {
                'event': 'strategy_triggered',
                'strategy': {
                    'id': self.strategy.id,
                    'name': self.strategy.name,
                },
                'device': {
                    'id': device.device_id,
                    'name': device.name,
                },
                'sensor': {
                    'id': sensor.id,
                    'name': sensor.name,
                    'value': value,
                },
                'timestamp': sensor_data.timestamp.isoformat(),
            }
        
        # 发送HTTP请求
        method = self.webhook_method or 'POST'
        if method == 'GET':
            response = requests.get(self.webhook_url, params=payload)
        else:
            response = requests.post(self.webhook_url, json=payload)
        
        # 检查响应
        if not response.ok:
            raise Exception(f"WebHook请求失败，状态码: {response.status_code}, 响应: {response.text}")
        
        logger.info(f"WebHook调用成功: {self.webhook_url}, 状态码: {response.status_code}")


class StrategyLog(models.Model):
    """策略执行日志模型"""
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='logs', verbose_name='策略')
    sensor_data = models.ForeignKey('iot_devices.SensorData', on_delete=models.CASCADE, related_name='strategy_logs', verbose_name='触发数据')
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='logs', verbose_name='执行动作')
    timestamp = models.DateTimeField('记录时间', auto_now_add=True)
    result = models.BooleanField('执行结果', default=True)
    message = models.TextField('日志信息', blank=True, null=True)
    
    class Meta:
        verbose_name = '策略日志'
        verbose_name_plural = '策略日志'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.strategy.name} {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {'成功' if self.result else '失败'}"
