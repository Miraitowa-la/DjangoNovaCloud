from django import forms
from .models import Project, Device, Sensor, Actuator


class ProjectForm(forms.ModelForm):
    """项目表单"""
    class Meta:
        model = Project
        fields = ['project_id', 'name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'project_id': '项目唯一标识，例如：PRJ-XXXXXX',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 对字段添加样式类
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class DeviceForm(forms.ModelForm):
    """设备表单"""
    class Meta:
        model = Device
        fields = ['device_id', 'device_identifier', 'name', 'project', 'status']
        widgets = {
            'device_key': forms.TextInput(attrs={'readonly': 'readonly'}),
        }
        help_texts = {
            'device_id': '设备唯一标识，例如：DEV-YYYYYY',
            'device_identifier': '设备物理标识，如MAC地址或序列号',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        
        # 对字段添加样式类
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # 限制项目选择为当前用户的项目
        if self.user:
            self.fields['project'].queryset = Project.objects.filter(owner=self.user)
        
        # 如果指定了项目ID，则预设并禁用项目选择
        if self.project_id:
            try:
                project = Project.objects.get(project_id=self.project_id, owner=self.user)
                self.fields['project'].initial = project
                self.fields['project'].widget.attrs['disabled'] = 'disabled'
                self.fields['project'].required = False
            except Project.DoesNotExist:
                pass
    
    def clean(self):
        """表单验证"""
        cleaned_data = super().clean()
        
        # 如果项目选择被禁用，则从初始值中获取
        if self.project_id and 'project' in self.fields and self.fields['project'].widget.attrs.get('disabled'):
            try:
                project = Project.objects.get(project_id=self.project_id, owner=self.user)
                cleaned_data['project'] = project
            except Project.DoesNotExist:
                self.add_error('project', '无效的项目')
        
        return cleaned_data


class SensorForm(forms.ModelForm):
    """传感器表单"""
    class Meta:
        model = Sensor
        fields = ['name', 'sensor_type', 'unit', 'value_key']
        help_texts = {
            'sensor_type': '传感器类型，例如：temperature, humidity',
            'unit': '单位，例如：°C, %',
            'value_key': '设备数据中的键名，用于识别此传感器的值'
        }
    
    def __init__(self, *args, **kwargs):
        self.device = kwargs.pop('device', None)
        super().__init__(*args, **kwargs)
        
        # 对字段添加样式类
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def save(self, commit=True):
        sensor = super().save(commit=False)
        if self.device:
            sensor.device = self.device
        if commit:
            sensor.save()
        return sensor


class ActuatorForm(forms.ModelForm):
    """执行器表单"""
    class Meta:
        model = Actuator
        fields = ['name', 'actuator_type', 'command_key', 'current_state']
        help_texts = {
            'actuator_type': '执行器类型，例如：switch, dimmer',
            'command_key': '控制命令的键名，用于发送控制命令',
            'current_state': '当前状态，例如：ON, OFF, 50%'
        }
    
    def __init__(self, *args, **kwargs):
        self.device = kwargs.pop('device', None)
        super().__init__(*args, **kwargs)
        
        # 对字段添加样式类
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def save(self, commit=True):
        actuator = super().save(commit=False)
        if self.device:
            actuator.device = self.device
        if commit:
            actuator.save()
        return actuator 