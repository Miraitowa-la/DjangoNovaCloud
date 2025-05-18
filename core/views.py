from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import logging  # 添加logging

# 获取不同的logger
django_logger = logging.getLogger('django')
security_logger = logging.getLogger('app.security')
debug_logger = logging.getLogger('debug')
accounts_logger = logging.getLogger('accounts')
iot_devices_logger = logging.getLogger('iot_devices')

class IndexView(LoginRequiredMixin, TemplateView):
    """平台主页视图"""
    template_name = 'core/index.html'
    
    def get(self, request, *args, **kwargs):
        # 添加测试日志
        django_logger.info('用户访问了首页 - django logger测试')
        security_logger.info('安全日志测试 - security logger测试')
        debug_logger.debug('调试日志测试 - debug logger测试')
        accounts_logger.info('账户日志测试 - accounts logger测试')
        iot_devices_logger.info('设备日志测试 - iot_devices logger测试')
        
        return super().get(request, *args, **kwargs)
