from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import InvitationCode, UserProfile


class UserRegisterForm(UserCreationForm):
    """用户注册表单，扩展Django内置的UserCreationForm，添加邮箱字段和邀请码字段"""
    email = forms.EmailField(required=True)
    invitation_code = forms.CharField(
        label='邀请码',
        required=False,
        help_text='选填。如果您有邀请码，请在此输入。'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'invitation_code']

    def clean_email(self):
        """验证邮箱是否已被使用"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱已被注册')
        return email
    
    def clean_invitation_code(self):
        """验证邀请码是否有效"""
        code = self.cleaned_data.get('invitation_code')
        if not code:
            # 邀请码是可选的，返回空值
            return code
            
        try:
            invitation = InvitationCode.objects.get(code=code)
            if not invitation.is_valid():
                raise forms.ValidationError('此邀请码已失效或已达到使用上限')
        except InvitationCode.DoesNotExist:
            raise forms.ValidationError('无效的邀请码')
            
        return code
        
    def save(self, commit=True):
        """保存用户，如果提供了有效邀请码，则设置上级用户关系"""
        user = super().save(commit=False)
        
        # 设置邮箱
        user.email = self.cleaned_data.get('email')
        
        if commit:
            user.save()
            
            # 处理邀请码和上级用户关系
            invitation_code = self.cleaned_data.get('invitation_code')
            if invitation_code:
                try:
                    invitation = InvitationCode.objects.get(code=invitation_code)
                    if invitation.is_valid():
                        # 设置上级用户关系
                        profile = UserProfile.objects.get(user=user)
                        profile.parent_user = invitation.issuer
                        profile.save()
                        
                        # 更新邀请码使用次数
                        invitation.times_used += 1
                        
                        # 如果达到使用上限，则禁用邀请码
                        if invitation.max_uses and invitation.times_used >= invitation.max_uses:
                            invitation.is_active = False
                            
                        invitation.save()
                except InvitationCode.DoesNotExist:
                    pass
        
        return user


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