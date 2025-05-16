from django import forms
from .models import Project, Device


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