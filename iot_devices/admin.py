from django.contrib import admin
from .models import Project, Device, Sensor, Actuator


class SensorInline(admin.TabularInline):
    """用于在设备管理页面内联显示传感器"""
    model = Sensor
    extra = 1


class ActuatorInline(admin.TabularInline):
    """用于在设备管理页面内联显示执行器"""
    model = Actuator
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """项目管理界面"""
    list_display = ('project_id', 'name', 'owner', 'created_at')
    list_filter = ('owner',)
    search_fields = ('name', 'project_id')
    date_hierarchy = 'created_at'


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """设备管理界面"""
    list_display = ('device_id', 'name', 'project', 'status', 'last_seen')
    list_filter = ('project', 'status')
    search_fields = ('name', 'device_id', 'device_identifier')
    readonly_fields = ('device_key',)
    inlines = [SensorInline, ActuatorInline]
    
    def save_model(self, request, obj, form, change):
        """保存设备前自动生成设备密钥"""
        # 使用模型的save方法会自动生成device_key
        super().save_model(request, obj, form, change)


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    """传感器管理界面"""
    list_display = ('name', 'sensor_type', 'unit', 'device')
    list_filter = ('device', 'sensor_type')
    search_fields = ('name',)


@admin.register(Actuator)
class ActuatorAdmin(admin.ModelAdmin):
    """执行器管理界面"""
    list_display = ('name', 'actuator_type', 'device', 'current_state')
    list_filter = ('device', 'actuator_type')
    search_fields = ('name',)
