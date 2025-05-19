from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    """
    用户个人信息作为内联显示在用户编辑页面
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = '用户信息'
    fk_name = 'user'

class UserAdmin(BaseUserAdmin):
    """
    扩展User Admin，添加个人信息内联
    """
    inlines = (UserProfileInline, )
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)
    
    def get_fieldsets(self, request, obj=None):
        # 沿用原有的fieldsets结构
        fieldsets = super().get_fieldsets(request, obj)
        return fieldsets

# 重新注册User模型
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
