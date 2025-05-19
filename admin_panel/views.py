from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.forms import SetPasswordForm

from accounts.models import UserProfile
from admin_panel.models import Role
from admin_panel.forms import UserCreateForm, UserEditForm

# Create your views here.

# 混入类，检查当前用户是否有管理权限
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # 检查用户是否是管理员
        # 可以通过角色判断或直接检查特定权限
        return self.request.user.is_staff or (
            hasattr(self.request.user, 'profile') and 
            self.request.user.profile.role and 
            self.request.user.profile.role.permissions.filter(codename='can_manage_users').exists()
        )

# 用户列表视图
class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = User
    template_name = 'admin_panel/user_list.html'
    context_object_name = 'users'
    
    def get_queryset(self):
        # 只显示当前管理员的下级用户
        if self.request.user.is_superuser:
            # 超级管理员可以看到所有用户
            return User.objects.all().order_by('-date_joined')
        else:
            # 普通管理员只能看到自己创建的用户
            return User.objects.filter(
                profile__parent_user=self.request.user
            ).order_by('-date_joined')

# 用户创建视图
class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = User
    template_name = 'admin_panel/user_form.html'
    form_class = UserCreateForm
    success_url = reverse_lazy('admin_panel:user_list')
    
    def form_valid(self, form):
        # 创建用户
        user = form.save(commit=False)
        
        # 设置上级用户关系
        if hasattr(user, 'profile'):
            profile = user.profile
            profile.parent_user = self.request.user
            profile.save()
        
        # 完成保存
        user.save()
        form.save_m2m()  # 保存多对多关系
        
        messages.success(self.request, f'用户 {user.username} 创建成功！')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '创建用户'
        return context

# 用户详情视图
class UserDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = User
    template_name = 'admin_panel/user_detail.html'
    context_object_name = 'user_obj'  # 避免与request.user冲突
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(profile__parent_user=self.request.user)

# 用户更新视图
class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = User
    template_name = 'admin_panel/user_form.html'
    form_class = UserEditForm
    context_object_name = 'user_obj'
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(profile__parent_user=self.request.user)
    
    def get_success_url(self):
        return reverse('admin_panel:user_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, f'用户 {user.username} 更新成功！')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '编辑用户'
        return context

# 用户删除视图
class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = User
    template_name = 'admin_panel/user_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:user_list')
    context_object_name = 'user_obj'
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(profile__parent_user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        messages.success(request, f'用户 {user.username} 已删除！')
        return super().delete(request, *args, **kwargs)

# 切换用户激活状态
class UserToggleActiveView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        if request.user.is_superuser:
            user = get_object_or_404(User, pk=pk)
        else:
            user = get_object_or_404(User, pk=pk, profile__parent_user=request.user)
        
        user.is_active = not user.is_active
        user.save()
        
        status = "启用" if user.is_active else "禁用"
        messages.success(request, f'用户 {user.username} 已{status}！')
        
        return redirect('admin_panel:user_detail', pk=pk)

# 重置用户密码
class UserResetPasswordView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request, pk):
        if request.user.is_superuser:
            user = get_object_or_404(User, pk=pk)
        else:
            user = get_object_or_404(User, pk=pk, profile__parent_user=request.user)
        
        form = SetPasswordForm(user)
        return render(request, 'admin_panel/reset_password.html', {
            'form': form,
            'user_obj': user
        })
    
    def post(self, request, pk):
        if request.user.is_superuser:
            user = get_object_or_404(User, pk=pk)
        else:
            user = get_object_or_404(User, pk=pk, profile__parent_user=request.user)
        
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'用户 {user.username} 的密码已重置！')
            return redirect('admin_panel:user_detail', pk=pk)
        
        return render(request, 'admin_panel/reset_password.html', {
            'form': form,
            'user_obj': user
        })
