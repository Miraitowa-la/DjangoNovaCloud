from django.contrib import admin
from .models import Role

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
