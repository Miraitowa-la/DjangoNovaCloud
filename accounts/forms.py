from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class UserRegisterForm(UserCreationForm):
    """用户注册表单，扩展Django内置的UserCreationForm，添加邮箱字段"""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        """验证邮箱是否已被使用"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱已被注册')
        return email


class UserLoginForm(AuthenticationForm):
    """自定义登录表单，支持用户名或邮箱登录"""
    username = forms.CharField(label='用户名或邮箱')
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username is not None and password:
            # 尝试以用户名登录
            self.user_cache = authenticate(self.request, username=username, password=password)
            
            # 如果用户名登录失败，尝试邮箱登录
            if self.user_cache is None:
                try:
                    user = User.objects.get(email=username)
                    self.user_cache = authenticate(self.request, username=user.username, password=password)
                except User.DoesNotExist:
                    pass
                
            if self.user_cache is None:
                raise forms.ValidationError('用户名/邮箱或密码不正确，请重试。')
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data 