from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .utils import create_audit_log
from .models import AuditLog

User = get_user_model()

# 登录信号处理
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """记录用户登录事件"""
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_USER_LOGIN,
        details=f"用户 {user.username} 登录成功",
        request=request
    )

# 登出信号处理
@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """记录用户登出事件"""
    if user:  # 确保用户不是匿名用户
        create_audit_log(
            user=user,
            action=AuditLog.ACTION_USER_LOGOUT,
            details=f"用户 {user.username} 登出系统",
            request=request
        )

# 登录失败信号处理
@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """记录用户登录失败事件"""
    # 这里无法获取用户对象，因为登录失败
    # 获取用户名或邮箱
    username = credentials.get('username', '')
    create_audit_log(
        user=None,  # 无法获取用户对象
        action=AuditLog.ACTION_USER_LOGIN_FAILED,
        details=f"用户名 '{username}' 登录失败",
        request=request
    ) 