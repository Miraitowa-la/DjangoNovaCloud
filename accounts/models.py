from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
import string
import random
from django.utils import timezone

# Create your models here.

class UserProfile(models.Model):
    """
    用户扩展信息模型，关联到Django的User模型
    添加角色和上下级用户的功能
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="用户"
    )
    role = models.ForeignKey(
        'admin_panel.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="角色"
    )
    parent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_profiles',
        verbose_name="上级用户"
    )
    
    class Meta:
        verbose_name = "用户资料"
        verbose_name_plural = "用户资料"
    
    def __str__(self):
        return f"{self.user.username}的资料"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    当创建新用户时，自动创建关联的用户信息
    """
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    当保存用户时，确保用户信息也被保存
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # 如果用户没有关联的profile（例如在数据迁移时可能发生），则创建一个
        UserProfile.objects.create(user=instance)

class InvitationCode(models.Model):
    """
    邀请码模型，用于新用户注册时自动关联上级
    """
    code = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        verbose_name="邀请码"
    )
    issuer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='issued_invitations',
        verbose_name="发行者"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="过期时间"
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="最大使用次数",
        help_text="0或留空表示无限次"
    )
    times_used = models.PositiveIntegerField(
        default=0,
        verbose_name="已使用次数"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否激活"
    )
    
    class Meta:
        verbose_name = "邀请码"
        verbose_name_plural = "邀请码"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"邀请码 {self.code} (发行人: {self.issuer.username})"
    
    def save(self, *args, **kwargs):
        # 如果没有设置邀请码，则自动生成
        if not self.code:
            self.code = self._generate_unique_code()
        super().save(*args, **kwargs)
    
    def _generate_unique_code(self):
        """生成唯一的8位随机邀请码"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(8))
            if not InvitationCode.objects.filter(code=code).exists():
                return code
    
    def is_valid(self):
        """检查邀请码是否有效"""
        # 检查是否激活
        if not self.is_active:
            return False
            
        # 检查是否过期
        if self.expires_at and timezone.now() > self.expires_at:
            return False
            
        # 检查使用次数
        if self.max_uses and self.times_used >= self.max_uses:
            return False
            
        return True
