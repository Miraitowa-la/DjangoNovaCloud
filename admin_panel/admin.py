from django.contrib import admin
from .models import Role, AuditLog

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    角色模型的Admin配置
    """
    list_display = ('name', 'description')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    fieldsets = (
        (None, {'fields': ('name', 'description')}),
        ('权限设置', {'fields': ('permissions',), 'classes': ('collapse',)}),
    )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    审计日志模型的Admin配置
    """
    list_display = ('user', 'action', 'target_content_type', 'target_object_id', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp', 'target_content_type')
    search_fields = ('user__username', 'details', 'ip_address')
    readonly_fields = ('user', 'action', 'target_content_type', 'target_object_id', 'details', 'ip_address', 'timestamp')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """禁止手动添加审计日志"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改审计日志"""
        return False
