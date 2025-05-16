from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
import json
import logging

from iot_devices.models import Device
from mqtt_client.mqtt import mqtt_client

logger = logging.getLogger(__name__)


@login_required
@csrf_protect
@require_POST
def send_device_command(request, device_id):
    """发送命令到设备"""
    # 获取设备并验证所有权
    device = get_object_or_404(Device, device_id=device_id)
    if device.project.owner != request.user:
        return JsonResponse({
            'success': False,
            'message': '您没有权限控制此设备'
        }, status=403)
    
    try:
        # 解析命令数据
        command_data = json.loads(request.body)
        
        # 检查命令字段
        if 'command' not in command_data:
            return JsonResponse({
                'success': False,
                'message': '缺少command字段'
            }, status=400)
        
        # 发送命令
        command_sent = mqtt_client.publish_command(device_id, command_data)
        
        if command_sent:
            return JsonResponse({
                'success': True,
                'message': '命令已发送',
                'device_id': device_id,
                'command': command_data
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '命令发送失败，请稍后重试'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"发送设备命令时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'发送命令时出错: {str(e)}'
        }, status=500)


@login_required
@csrf_protect
@require_POST
def send_device_ping(request, device_id):
    """发送ping命令到设备"""
    # 获取设备并验证所有权
    device = get_object_or_404(Device, device_id=device_id)
    if device.project.owner != request.user:
        return JsonResponse({
            'success': False,
            'message': '您没有权限控制此设备'
        }, status=403)
    
    try:
        # 构建ping命令
        ping_command = {
            'command': 'ping',
            'timestamp': int(__import__('time').time())
        }
        
        # 发送命令
        command_sent = mqtt_client.publish_command(device_id, ping_command)
        
        if command_sent:
            return JsonResponse({
                'success': True,
                'message': 'Ping命令已发送',
                'device_id': device_id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Ping命令发送失败，请稍后重试'
            }, status=500)
    
    except Exception as e:
        logger.error(f"发送设备ping命令时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'发送ping命令时出错: {str(e)}'
        }, status=500)


@login_required
@csrf_protect
@require_POST
def send_device_reboot(request, device_id):
    """发送重启命令到设备"""
    # 获取设备并验证所有权
    device = get_object_or_404(Device, device_id=device_id)
    if device.project.owner != request.user:
        return JsonResponse({
            'success': False,
            'message': '您没有权限控制此设备'
        }, status=403)
    
    try:
        # 构建重启命令
        reboot_command = {
            'command': 'reboot',
            'timestamp': int(__import__('time').time())
        }
        
        # 发送命令
        command_sent = mqtt_client.publish_command(device_id, reboot_command)
        
        if command_sent:
            return JsonResponse({
                'success': True,
                'message': '重启命令已发送',
                'device_id': device_id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '重启命令发送失败，请稍后重试'
            }, status=500)
    
    except Exception as e:
        logger.error(f"发送设备重启命令时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'发送重启命令时出错: {str(e)}'
        }, status=500)
