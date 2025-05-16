from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.models import User
from .forms import UserRegisterForm, UserLoginForm


class UserRegisterView(CreateView):
    """用户注册视图"""
    template_name = 'accounts/register.html'
    form_class = UserRegisterForm
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        """表单验证成功处理"""
        response = super().form_valid(form)
        messages.success(self.request, f'账号创建成功，您现在可以登录了！')
        return response


class UserLoginView(LoginView):
    """用户登录视图"""
    template_name = 'accounts/login.html'
    form_class = UserLoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    """用户登出视图"""
    next_page = 'accounts:login'  # 显式指定登出后重定向的URL
    # Django的LogoutView会处理csrf验证和会话清除
