from django import forms
from django.core.exceptions import ValidationError
from .models import Strategy, Condition, Action
from iot_devices.models import Project, Device, Sensor, Actuator


class StrategyForm(forms.ModelForm):
    """策略表单"""
    class Meta:
        model = Strategy
        fields = ['name', 'description', 'is_enabled', 'trigger_source_device']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # 如果提供了用户，则限制触发设备的选择范围
            if self.project_id:
                # 如果提供了项目ID，则只显示该项目的设备
                try:
                    project = Project.objects.get(project_id=self.project_id, owner=self.user)
                    self.fields['trigger_source_device'].queryset = Device.objects.filter(project=project)
                except Project.DoesNotExist:
                    self.fields['trigger_source_device'].queryset = Device.objects.none()
            else:
                # 否则显示用户所有项目的设备
                self.fields['trigger_source_device'].queryset = Device.objects.filter(project__owner=self.user)
        
        # 如果是编辑已有策略，则设置project字段的值
        if self.instance and self.instance.pk:
            self.project = self.instance.project
        elif self.project_id:
            try:
                self.project = Project.objects.get(project_id=self.project_id)
            except Project.DoesNotExist:
                self.project = None
    
    def clean_name(self):
        """验证策略名称的唯一性"""
        name = self.cleaned_data.get('name')
        if name:
            # 检查同一项目下是否存在同名策略
            if self.project:
                existing = Strategy.objects.filter(project=self.project, name=name)
                if self.instance and self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)
                if existing.exists():
                    raise ValidationError('同一项目下已存在同名策略')
        return name
    
    def save(self, commit=True):
        """保存策略，设置project字段"""
        instance = super().save(commit=False)
        
        # 设置策略所属项目
        if self.project:
            instance.project = self.project
        
        if commit:
            instance.save()
        
        return instance


class ConditionForm(forms.ModelForm):
    """条件表单"""
    class Meta:
        model = Condition
        fields = ['sensor', 'metric_key', 'operator', 'threshold_value_type', 
                 'threshold_value_float', 'threshold_value_string', 'threshold_value_boolean',
                 'logical_operator_to_next']
        widgets = {
            'threshold_value_float': forms.NumberInput(attrs={'step': 'any'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.strategy_id = kwargs.pop('strategy_id', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.strategy_id:
            try:
                strategy = Strategy.objects.get(pk=self.strategy_id)
                self.fields['sensor'].queryset = Sensor.objects.filter(device=strategy.trigger_source_device)
                self.strategy = strategy
            except Strategy.DoesNotExist:
                self.fields['sensor'].queryset = Sensor.objects.none()
                self.strategy = None
        elif self.instance and self.instance.pk:
            # 编辑已有条件时设置sensor选项
            self.strategy = self.instance.strategy
            self.fields['sensor'].queryset = Sensor.objects.filter(device=self.strategy.trigger_source_device)
        else:
            self.fields['sensor'].queryset = Sensor.objects.none()
            self.strategy = None
        
        # 添加占位符
        self.fields['metric_key'].widget.attrs['placeholder'] = '通常为"value"'
    
    def clean(self):
        """验证表单数据"""
        cleaned_data = super().clean()
        threshold_type = cleaned_data.get('threshold_value_type')
        
        # 根据阈值类型，确保对应的阈值字段已填写
        if threshold_type == 'float':
            if cleaned_data.get('threshold_value_float') is None:
                self.add_error('threshold_value_float', '使用数值类型时必须提供数值阈值')
        elif threshold_type == 'string':
            if not cleaned_data.get('threshold_value_string'):
                self.add_error('threshold_value_string', '使用文本类型时必须提供文本阈值')
        elif threshold_type == 'boolean':
            if cleaned_data.get('threshold_value_boolean') is None:
                self.add_error('threshold_value_boolean', '使用布尔类型时必须提供布尔阈值')
        
        return cleaned_data
    
    def save(self, commit=True):
        """保存条件，设置strategy字段"""
        instance = super().save(commit=False)
        
        # 设置条件所属策略
        if self.strategy:
            instance.strategy = self.strategy
        
        if commit:
            instance.save()
        
        return instance


class ActionForm(forms.ModelForm):
    """动作表单"""
    class Meta:
        model = Action
        fields = ['action_type', 
                 'recipient_user', 'recipient_email', 'notification_subject_template', 'notification_body_template',
                 'target_actuator', 'actuator_command',
                 'webhook_url', 'webhook_method', 'webhook_payload_template']
        widgets = {
            'notification_body_template': forms.Textarea(attrs={'rows': 5}),
            'webhook_payload_template': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        self.strategy_id = kwargs.pop('strategy_id', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # 限制接收用户选择范围
            self.fields['recipient_user'].queryset = self.fields['recipient_user'].queryset.filter(
                id=self.user.id
            )
        
        if self.strategy_id:
            try:
                strategy = Strategy.objects.get(pk=self.strategy_id)
                # 限制目标执行器选择范围
                self.fields['target_actuator'].queryset = Actuator.objects.filter(
                    device__project=strategy.project
                )
                self.strategy = strategy
            except Strategy.DoesNotExist:
                self.fields['target_actuator'].queryset = Actuator.objects.none()
                self.strategy = None
        elif self.instance and self.instance.pk:
            # 编辑已有动作时
            self.strategy = self.instance.strategy
            self.fields['target_actuator'].queryset = Actuator.objects.filter(
                device__project=self.strategy.project
            )
        else:
            self.fields['target_actuator'].queryset = Actuator.objects.none()
            self.strategy = None
    
    def clean(self):
        """验证表单数据"""
        cleaned_data = super().clean()
        action_type = cleaned_data.get('action_type')
        
        # 根据动作类型，验证必填字段
        if action_type == 'send_email_notification':
            # 邮件通知：主题和内容是必填的
            if not cleaned_data.get('notification_subject_template'):
                self.add_error('notification_subject_template', '邮件主题是必填的')
            if not cleaned_data.get('notification_body_template'):
                self.add_error('notification_body_template', '邮件内容是必填的')
        
        elif action_type == 'control_actuator':
            # 执行器控制：目标执行器和命令是必填的
            if not cleaned_data.get('target_actuator'):
                self.add_error('target_actuator', '目标执行器是必填的')
            if not cleaned_data.get('actuator_command'):
                self.add_error('actuator_command', '执行器命令是必填的')
        
        elif action_type == 'webhook':
            # WebHook：URL是必填的
            if not cleaned_data.get('webhook_url'):
                self.add_error('webhook_url', 'WebHook URL是必填的')
        
        return cleaned_data
    
    def save(self, commit=True):
        """保存动作，设置strategy字段"""
        instance = super().save(commit=False)
        
        # 设置动作所属策略
        if self.strategy:
            instance.strategy = self.strategy
        
        if commit:
            instance.save()
        
        return instance 