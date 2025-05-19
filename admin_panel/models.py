from django.db import models
from django.contrib.auth.models import Permission
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class Role(models.Model):
    """
    用户角色模型，用于定义系统中的不同角色及其权限
    """
    name = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="角色名称"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="角色描述"
    )
    permissions = models.ManyToManyField(
        Permission, 
        blank=True, 
        verbose_name="权限"
    )
    
    class Meta:
        verbose_name = "角色"
        verbose_name_plural = "角色"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class AuditLog(models.Model):
    """
    操作审计日志模型，记录用户在系统中的关键操作
    """
    # 审计日志类型常量
    ACTION_USER_CREATE = 'user_created'
    ACTION_USER_UPDATE = 'user_updated'
    ACTION_USER_DELETE = 'user_deleted'
    ACTION_USER_ACTIVATE = 'user_activated'
    ACTION_USER_DEACTIVATE = 'user_deactivated'
    ACTION_ROLE_CHANGE = 'role_changed'
    ACTION_PASSWORD_RESET = 'password_reset'
    ACTION_USER_LOGIN = 'user_login'
    ACTION_USER_LOGOUT = 'user_logout'
    ACTION_USER_LOGIN_FAILED = 'user_login_failed'
    ACTION_PROJECT_CREATE = 'project_created'
    ACTION_PROJECT_UPDATE = 'project_updated'
    ACTION_PROJECT_DELETE = 'project_deleted'
    
    ACTION_CHOICES = [
        (ACTION_USER_CREATE, '创建用户'),
        (ACTION_USER_UPDATE, '更新用户'),
        (ACTION_USER_DELETE, '删除用户'),
        (ACTION_USER_ACTIVATE, '启用用户'),
        (ACTION_USER_DEACTIVATE, '禁用用户'),
        (ACTION_ROLE_CHANGE, '角色变更'),
        (ACTION_PASSWORD_RESET, '密码重置'),
        (ACTION_USER_LOGIN, '用户登录'),
        (ACTION_USER_LOGOUT, '用户登出'),
        (ACTION_USER_LOGIN_FAILED, '登录失败'),
        (ACTION_PROJECT_CREATE, '创建项目'),
        (ACTION_PROJECT_UPDATE, '更新项目'),
        (ACTION_PROJECT_DELETE, '删除项目'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="操作用户"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name="操作类型"
    )
    # 使用ContentType实现通用外键
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="目标类型"
    )
    target_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="目标ID"
    )
    target = GenericForeignKey(
        'target_content_type',
        'target_object_id'
    )
    details = models.TextField(
        verbose_name="操作详情"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP地址"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="操作时间"
    )
    
    class Meta:
        verbose_name = "审计日志"
        verbose_name_plural = "审计日志"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['target_content_type', 'target_object_id']),
        ]
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.get_action_display()} - {self.timestamp}"
        return f"匿名用户 - {self.get_action_display()} - {self.timestamp}"
