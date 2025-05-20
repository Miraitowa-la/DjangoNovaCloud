from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, InvitationCode

# Register your models here.

# 用户资料内联管理
class UserProfileInline(admin.StackedInline):
    """
    用户个人信息作为内联显示在用户编辑页面
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = '用户信息'
    fk_name = 'user'

# 扩展用户管理
class CustomUserAdmin(UserAdmin):
    """
    扩展User Admin，添加个人信息内联
    """
    inlines = (UserProfileInline, )
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)
    
    def get_fieldsets(self, request, obj=None):
        # 沿用原有的fieldsets结构
        fieldsets = super().get_fieldsets(request, obj)
        return fieldsets

# 重新注册User模型
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# 注册邀请码管理
@admin.register(InvitationCode)
class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'issuer', 'is_active', 'times_used', 'max_uses', 'created_at', 'expires_at']
    list_filter = ['is_active', 'issuer']
    search_fields = ['code', 'issuer__username']
    readonly_fields = ['times_used']
    date_hierarchy = 'created_at'
    fieldsets = (
        (None, {
            'fields': ('code', 'issuer', 'is_active')
        }),
        ('使用情况', {
            'fields': ('times_used', 'max_uses')
        }),
        ('时间信息', {
            'fields': ('created_at', 'expires_at')
        })
    )
