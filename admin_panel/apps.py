from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_panel'
    verbose_name = '管理面板'
    
    def ready(self):
        """应用启动时加载信号处理器"""
        import admin_panel.signals  # 导入信号模块以注册信号处理器