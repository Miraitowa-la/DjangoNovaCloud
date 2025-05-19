from django import forms
from django.contrib.auth.models import User, Permission
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.contenttypes.models import ContentType

from admin_panel.models import Role

class UserCreateForm(UserCreationForm):
    """
    自定义用户创建表单，扩展了Django的UserCreationForm
    添加了角色选择和电子邮件字段
    """
    email = forms.EmailField(
        required=True, 
        label='电子邮件',
        help_text='请输入有效的电子邮件地址'
    )
    
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label='用户角色',
        help_text='选择用户角色，决定用户权限'
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password1', 'password2', 
            'first_name', 'last_name', 'is_active'
        ]
        labels = {
            'username': '用户名',
            'first_name': '名',
            'last_name': '姓',
            'is_active': '账户激活'
        }
        help_texts = {
            'username': '必填。150个字符或更少。只能包含字母、数字和@/./+/-/_',
            'is_active': '指定此账户是否可以登录'
        }
    
    def save(self, commit=True):
        # 获取父类的save方法的结果
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # 如果用户有关联的profile，设置角色
            if hasattr(user, 'profile') and self.cleaned_data.get('role'):
                user.profile.role = self.cleaned_data['role']
                user.profile.save()
        
        return user

class UserEditForm(forms.ModelForm):
    """
    用户编辑表单，不包含密码字段
    """
    email = forms.EmailField(
        required=True, 
        label='电子邮件',
        help_text='请输入有效的电子邮件地址'
    )
    
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label='用户角色',
        help_text='选择用户角色，决定用户权限'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        labels = {
            'username': '用户名',
            'first_name': '名',
            'last_name': '姓',
            'is_active': '账户激活'
        }
        help_texts = {
            'username': '必填。150个字符或更少。只能包含字母、数字和@/./+/-/_',
            'is_active': '指定此账户是否可以登录'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 如果用户有profile且有角色，设置初始值
        if self.instance and hasattr(self.instance, 'profile') and self.instance.profile.role:
            self.fields['role'].initial = self.instance.profile.role
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # 更新用户角色
            if hasattr(user, 'profile'):
                user.profile.role = self.cleaned_data.get('role')
                user.profile.save()
        
        return user 

class RoleForm(forms.ModelForm):
    """
    角色创建和编辑表单
    包含角色名称、描述和权限选择
    """
    name = forms.CharField(
        max_length=50, 
        required=True,
        label='角色名称',
        help_text='角色的唯一名称'
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='角色描述',
        help_text='关于此角色功能和用途的简短描述'
    )
    
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='权限',
        help_text='选择此角色拥有的权限'
    )
    
    class Meta:
        model = Role
        fields = ['name', 'description', 'permissions']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 获取所有权限并按应用和模型分组
        content_types = ContentType.objects.all().order_by('app_label', 'model')
        
        # 构建分组的权限字典
        self.grouped_permissions = {}
        
        for ct in content_types:
            app_label = ct.app_label
            model_name = ct.model
            
            if app_label not in self.grouped_permissions:
                self.grouped_permissions[app_label] = {}
            
            # 获取此内容类型的所有权限
            ct_permissions = Permission.objects.filter(content_type=ct).order_by('codename')
            
            if ct_permissions.exists():
                self.grouped_permissions[app_label][model_name] = ct_permissions 