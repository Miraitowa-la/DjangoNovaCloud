from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

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
        verbose_name = "用户信息"
        verbose_name_plural = "用户信息"
    
    def __str__(self):
        return f"{self.user.username}的个人信息"

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
