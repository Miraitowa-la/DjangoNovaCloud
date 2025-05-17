from django.contrib import admin
from .models import Strategy, Condition, Action, StrategyLog


class ConditionInline(admin.TabularInline):
    """条件内联显示"""
    model = Condition
    extra = 1
    
    
class ActionInline(admin.TabularInline):
    """动作内联显示"""
    model = Action
    extra = 1
    fieldsets = (
        (None, {
            'fields': ('action_type',)
        }),
        ('邮件通知设置', {
            'fields': ('recipient_user', 'recipient_email', 'notification_subject_template', 'notification_body_template'),
            'classes': ('collapse',),
        }),
        ('执行器控制设置', {
            'fields': ('target_actuator', 'actuator_command'),
            'classes': ('collapse',),
        }),
        ('WebHook设置', {
            'fields': ('webhook_url', 'webhook_method', 'webhook_payload_template'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    """策略管理"""
    list_display = ('name', 'project', 'trigger_source_device', 'is_enabled', 'created_at')
    list_filter = ('project', 'is_enabled', 'trigger_source_device')
    search_fields = ('name', 'description')
    inlines = [ConditionInline, ActionInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'project', 'description', 'is_enabled', 'trigger_source_device')
        }),
    )


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    """条件管理"""
    list_display = ('__str__', 'strategy', 'sensor', 'operator', 'get_threshold_value', 'logical_operator_to_next')
    list_filter = ('strategy', 'operator', 'logical_operator_to_next')
    search_fields = ('strategy__name', 'sensor__name')


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    """动作管理"""
    list_display = ('__str__', 'strategy', 'action_type')
    list_filter = ('strategy', 'action_type')
    search_fields = ('strategy__name',)
    
    fieldsets = (
        (None, {
            'fields': ('strategy', 'action_type')
        }),
        ('邮件通知设置', {
            'fields': ('recipient_user', 'recipient_email', 'notification_subject_template', 'notification_body_template'),
            'classes': ('collapse',),
        }),
        ('执行器控制设置', {
            'fields': ('target_actuator', 'actuator_command'),
            'classes': ('collapse',),
        }),
        ('WebHook设置', {
            'fields': ('webhook_url', 'webhook_method', 'webhook_payload_template'),
            'classes': ('collapse',),
        }),
    )


@admin.register(StrategyLog)
class StrategyLogAdmin(admin.ModelAdmin):
    """策略日志管理"""
    list_display = ('__str__', 'strategy', 'action', 'result', 'timestamp')
    list_filter = ('strategy', 'result', 'action__action_type')
    search_fields = ('strategy__name', 'message')
    readonly_fields = ('strategy', 'sensor_data', 'action', 'timestamp', 'result', 'message')
    
    def has_add_permission(self, request):
        """禁止添加日志"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False
