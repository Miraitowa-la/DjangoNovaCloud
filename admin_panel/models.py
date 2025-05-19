from django.db import models
from django.contrib.auth.models import Permission

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
