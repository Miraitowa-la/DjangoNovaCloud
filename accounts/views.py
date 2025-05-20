from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import CreateView, ListView, DeleteView
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegisterForm, UserLoginForm
from .models import InvitationCode


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


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 注册后自动登录
            messages.success(request, '注册成功！欢迎加入NovaCloud。')
            return redirect('core:index')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'欢迎回来，{user.username}！')
            
            # 如果有next参数，则重定向到该地址
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('core:index')
    else:
        form = UserLoginForm(request)
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, '您已成功登出。')
        return redirect('accounts:login')
    
    # 如果是GET请求，显示确认页面
    return render(request, 'accounts/logout.html')

# 邀请码管理视图
class InvitationCodeListView(LoginRequiredMixin, ListView):
    """邀请码列表视图"""
    model = InvitationCode
    template_name = 'accounts/invitations/invitation_list.html'
    context_object_name = 'invitations'
    
    def get_queryset(self):
        """只显示当前用户创建的邀请码"""
        return InvitationCode.objects.filter(issuer=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '邀请码管理'
        context['active_invitations'] = self.get_queryset().filter(is_active=True)
        context['inactive_invitations'] = self.get_queryset().filter(is_active=False)
        return context

class InvitationCodeCreateView(LoginRequiredMixin, CreateView):
    """创建邀请码视图"""
    model = InvitationCode
    template_name = 'accounts/invitations/invitation_form.html'
    fields = ['max_uses', 'expires_at']
    success_url = reverse_lazy('accounts:invitation_list')
    
    def form_valid(self, form):
        """设置邀请码发行者为当前用户"""
        form.instance.issuer = self.request.user
        messages.success(self.request, '邀请码创建成功！')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '创建邀请码'
        # 提供常用的过期时间选项
        context['expires_options'] = {
            '1d': timezone.now() + timedelta(days=1),
            '7d': timezone.now() + timedelta(days=7),
            '30d': timezone.now() + timedelta(days=30),
        }
        return context

class QuickInvitationCreateView(LoginRequiredMixin, View):
    """快速创建邀请码"""
    def post(self, request):
        # 创建7天有效期的邀请码
        expires_at = timezone.now() + timedelta(days=7)
        invitation = InvitationCode.objects.create(
            issuer=request.user,
            expires_at=expires_at,
            max_uses=1  # 只能使用一次
        )
        messages.success(request, f'邀请码 {invitation.code} 创建成功！')
        return redirect('accounts:invitation_list')

class InvitationCodeDeleteView(LoginRequiredMixin, DeleteView):
    """删除邀请码视图"""
    model = InvitationCode
    template_name = 'accounts/invitations/invitation_confirm_delete.html'
    success_url = reverse_lazy('accounts:invitation_list')
    context_object_name = 'invitation'
    
    def get_queryset(self):
        """只能删除自己创建的邀请码"""
        return InvitationCode.objects.filter(issuer=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '邀请码已删除。')
        return super().delete(request, *args, **kwargs)
