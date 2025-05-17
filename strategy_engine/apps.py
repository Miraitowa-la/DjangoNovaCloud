from django.apps import AppConfig


class StrategyEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'strategy_engine'
    verbose_name = '策略引擎'
    
    def ready(self):
        """应用就绪时导入信号模块"""
        import strategy_engine.signals
