from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User, Permission
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q, Count
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta

from accounts.models import UserProfile
from admin_panel.models import Role, AuditLog
from admin_panel.forms import UserCreateForm, UserEditForm, RoleForm
from .utils import get_subordinate_user_ids, get_user_and_subordinates_queryset, create_audit_log
from iot_devices.models import Project

User = get_user_model()

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
        
        # 记录审计日志
        role_name = "无角色"
        if hasattr(user, 'profile') and user.profile.role:
            role_name = user.profile.role.name
            
        create_audit_log(
            user=self.request.user,
            action=AuditLog.ACTION_USER_CREATE,
            target_object=user,
            details=f"创建用户 {user.username}，设置角色为 {role_name}",
            request=self.request
        )
        
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
        
        # 构建审计日志详情
        details = f"更新用户 {user.username} 的信息"
        
        # 如果有角色变更，特别记录
        if 'role' in form.changed_data:
            old_role = "无角色"
            if hasattr(self.object, 'profile') and self.object.profile.role_id:
                try:
                    old_role = Role.objects.get(id=self.object.profile.role_id).name
                except Role.DoesNotExist:
                    pass
                
            new_role = "无角色"
            if form.cleaned_data.get('role'):
                new_role = form.cleaned_data['role'].name
                
            if old_role != new_role:
                # 添加角色变更的审计日志
                create_audit_log(
                    user=self.request.user,
                    action=AuditLog.ACTION_ROLE_CHANGE,
                    target_object=user,
                    details=f"修改用户 {user.username} 的角色，从 {old_role} 变更为 {new_role}",
                    request=self.request
                )
        
        # 记录常规更新审计日志
        create_audit_log(
            user=self.request.user,
            action=AuditLog.ACTION_USER_UPDATE,
            target_object=user,
            details=details,
            request=self.request
        )
        
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
        username = user.username  # 保存用户名供日志使用
        
        # 记录审计日志
        create_audit_log(
            user=self.request.user,
            action=AuditLog.ACTION_USER_DELETE,
            details=f"删除用户 {username}",
            request=self.request
        )
        
        messages.success(request, f'用户 {username} 已删除！')
        return super().delete(request, *args, **kwargs)

# 切换用户激活状态
class UserToggleActiveView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        if request.user.is_superuser:
            user = get_object_or_404(User, pk=pk)
        else:
            user = get_object_or_404(User, pk=pk, profile__parent_user=request.user)
        
        # 切换状态前记录原状态
        was_active = user.is_active
        user.is_active = not was_active
        user.save()
        
        # 记录审计日志
        action = AuditLog.ACTION_USER_ACTIVATE if user.is_active else AuditLog.ACTION_USER_DEACTIVATE
        status = "启用" if user.is_active else "禁用"
        
        create_audit_log(
            user=request.user,
            action=action,
            target_object=user,
            details=f"{status}用户 {user.username}",
            request=request
        )
        
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
            
            # 记录审计日志
            create_audit_log(
                user=request.user,
                action=AuditLog.ACTION_PASSWORD_RESET,
                target_object=user,
                details=f"重置用户 {user.username} 的密码",
                request=request
            )
            
            messages.success(request, f'用户 {user.username} 的密码已重置！')
            return redirect('admin_panel:user_detail', pk=pk)
        
        return render(request, 'admin_panel/reset_password.html', {
            'form': form,
            'user_obj': user
        })

# 全局项目视图
class GlobalProjectListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """全局项目视图，仅限管理员访问"""
    model = Project
    template_name = 'admin_panel/projects/global_project_list.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        """根据管理员权限返回可管理的项目"""
        user = self.request.user
        
        # 超级管理员可查看所有项目
        if user.is_superuser:
            return Project.objects.all()
        
        # 其他管理员可查看其下级用户的项目
        user_ids = get_subordinate_user_ids(user)
        return Project.objects.filter(owner__id__in=user_ids)
    
    def get_context_data(self, **kwargs):
        """添加额外上下文"""
        context = super().get_context_data(**kwargs)
        context['title'] = '全局项目'
        context['is_admin_view'] = True
        return context

# 审计日志列表视图
class AuditLogListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """审计日志列表视图，仅限管理员访问"""
    model = AuditLog
    template_name = 'admin_panel/audit_logs/audit_log_list.html'
    context_object_name = 'logs'
    paginate_by = 50  # 每页显示50条日志
    
    def get_queryset(self):
        """根据筛选条件返回审计日志"""
        queryset = AuditLog.objects.all().order_by('-timestamp')
        
        # 用户筛选
        user_id = self.request.GET.get('user')
        if user_id:
            try:
                queryset = queryset.filter(user_id=int(user_id))
            except (ValueError, TypeError):
                pass
                
        # 操作类型筛选
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # 时间范围筛选
        time_range = self.request.GET.get('time_range', '7d')  # 默认查看过去7天
        
        now = timezone.now()
        if time_range == '24h':
            start_time = now - timedelta(hours=24)
        elif time_range == '7d':
            start_time = now - timedelta(days=7)
        elif time_range == '30d':
            start_time = now - timedelta(days=30)
        elif time_range == 'all':
            start_time = None
        else:
            start_time = now - timedelta(days=7)
            
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
        
        # 搜索功能 - 增强版
        search = self.request.GET.get('search')
        if search:
            username_search = None
            content_search = None
            ip_search = None
            
            # 处理特殊搜索语法
            search_terms = search.split()
            
            # 提取特殊搜索条件
            for term in search_terms:
                if term.startswith('@'):
                    username_search = term[1:]  # 去掉@符号
                elif term.startswith('#'):
                    content_search = term[1:]  # 去掉#符号
                elif term.startswith('%'):
                    ip_search = term[1:]  # 去掉%符号
            
            # 使用 AND 逻辑组合多个条件（而非 OR 逻辑）
            # 首先检查是否有特殊搜索条件
            has_special_search = username_search is not None or content_search is not None or ip_search is not None
            
            if has_special_search:
                # 应用特殊搜索条件，同时满足所有指定的条件
                if username_search:
                    queryset = queryset.filter(user__username__icontains=username_search)
                
                if content_search:
                    queryset = queryset.filter(details__icontains=content_search)
                
                if ip_search:
                    queryset = queryset.filter(ip_address__icontains=ip_search)
            else:
                # 如果没有特殊搜索语法，则进行普通搜索
                queryset = queryset.filter(
                    Q(user__username__icontains=search) |
                    Q(details__icontains=search) |
                    Q(ip_address__icontains=search)
                )
            
        return queryset
    
    def get_context_data(self, **kwargs):
        """添加额外上下文"""
        context = super().get_context_data(**kwargs)
        context['title'] = '操作审计日志'
        context['action_choices'] = AuditLog.ACTION_CHOICES
        
        # 获取筛选参数供模板使用
        context['selected_user'] = self.request.GET.get('user', '')
        context['selected_action'] = self.request.GET.get('action', '')
        context['selected_time_range'] = self.request.GET.get('time_range', '7d')
        context['search_query'] = self.request.GET.get('search', '')
        
        # 获取用户列表供筛选使用
        context['users'] = User.objects.all()
        
        # 保存当前查询字符串，便于分页使用
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_string'] = query_params.urlencode()
        
        return context

# 用户层级树状图视图
class UserHierarchyView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """用户层级树状图视图，仅限管理员访问"""
    template_name = 'admin_panel/users/user_hierarchy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 构建用户树状结构
        if user.is_superuser:
            # 超级管理员从根用户开始构建完整树
            root_users = User.objects.filter(profile__parent_user__isnull=True)
            user_tree = self._build_user_tree(root_users)
        else:
            # 其他管理员从自己开始构建树
            user_tree = [self._build_user_subtree(user)]
            
        context['user_tree'] = user_tree
        context['title'] = '用户层级结构'
        return context
    
    def _build_user_tree(self, users):
        """构建多个用户的树状结构"""
        return [self._build_user_subtree(user) for user in users]
    
    def _build_user_subtree(self, user):
        """递归构建单个用户及其下级的树状结构"""
        # 获取用户的角色名称（如果有）
        role_name = user.profile.role.name if hasattr(user, 'profile') and user.profile.role else '无角色'
        
        # 查询用户的直接下级
        subordinates = User.objects.filter(profile__parent_user=user)
        
        # 构建用户节点，包括ID、用户名、角色和子节点
        node = {
            'id': user.id,
            'username': user.username,
            'role': role_name,
            'is_active': user.is_active,
            'children': [self._build_user_subtree(sub) for sub in subordinates] if subordinates else []
        }
        
        return node

# 超级管理员检查混入类
class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

# 角色列表视图
class RoleListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    """角色列表视图，仅限超级管理员访问"""
    model = Role
    template_name = 'admin_panel/roles/role_list.html'
    context_object_name = 'roles'
    
    def get_queryset(self):
        # 获取每个角色关联的用户数量
        return Role.objects.annotate(user_count=Count('users')).order_by('name')

# 角色创建视图
class RoleCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    """角色创建视图，仅限超级管理员访问"""
    model = Role
    form_class = RoleForm
    template_name = 'admin_panel/roles/role_form.html'
    success_url = reverse_lazy('admin_panel:role_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # 记录审计日志
        create_audit_log(
            user=self.request.user,
            action=AuditLog.ACTION_ROLE_CREATE,
            target_object=self.object,
            details=f"创建角色 {self.object.name}",
            request=self.request
        )
        
        messages.success(self.request, f'角色 {self.object.name} 创建成功！')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '创建角色'
        # 将分组的权限传递给模板
        context['permissions_by_app'] = self.form_class().grouped_permissions
        return context

# 角色更新视图
class RoleUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    """角色编辑视图，仅限超级管理员访问"""
    model = Role
    form_class = RoleForm
    template_name = 'admin_panel/roles/role_form.html'
    context_object_name = 'role'
    success_url = reverse_lazy('admin_panel:role_list')
    
    def form_valid(self, form):
        # 获取修改前的权限列表
        old_permissions = list(self.get_object().permissions.values_list('id', flat=True))
        
        response = super().form_valid(form)
        
        # 获取修改后的权限列表
        new_permissions = list(self.object.permissions.values_list('id', flat=True))
        
        # 如果权限有变化，记录在审计日志中
        if set(old_permissions) != set(new_permissions):
            added = len(set(new_permissions) - set(old_permissions))
            removed = len(set(old_permissions) - set(new_permissions))
            
            permission_changes = []
            if added > 0:
                permission_changes.append(f"添加了 {added} 个权限")
            if removed > 0:
                permission_changes.append(f"移除了 {removed} 个权限")
                
            permission_change_text = "，".join(permission_changes)
            details = f"更新角色 {self.object.name}：{permission_change_text}"
        else:
            details = f"更新角色 {self.object.name}"
        
        # 记录审计日志
        create_audit_log(
            user=self.request.user,
            action=AuditLog.ACTION_ROLE_UPDATE,
            target_object=self.object,
            details=details,
            request=self.request
        )
        
        messages.success(self.request, f'角色 {self.object.name} 更新成功！')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '编辑角色'
        # 将分组的权限传递给模板
        context['permissions_by_app'] = self.get_form().grouped_permissions
        return context

# 角色删除视图
class RoleDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    """角色删除视图，仅限超级管理员访问"""
    model = Role
    template_name = 'admin_panel/roles/role_confirm_delete.html'
    context_object_name = 'role'
    success_url = reverse_lazy('admin_panel:role_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 获取使用此角色的用户数量
        context['user_count'] = UserProfile.objects.filter(role=self.object).count()
        return context
    
    def post(self, request, *args, **kwargs):
        role = self.get_object()
        # 检查是否有用户使用此角色
        if UserProfile.objects.filter(role=role).exists():
            messages.error(request, f'无法删除角色 {role.name}，仍有用户使用此角色。')
            return redirect('admin_panel:role_list')
        
        # 记录角色名称供日志使用
        role_name = role.name
        
        # 调用父类的delete方法删除角色
        response = super().post(request, *args, **kwargs)
        
        # 记录审计日志
        create_audit_log(
            user=request.user,
            action=AuditLog.ACTION_ROLE_DELETE,
            details=f"删除角色 {role_name}",
            request=request
        )
        
        messages.success(request, f'角色 {role_name} 已删除！')
        return response
