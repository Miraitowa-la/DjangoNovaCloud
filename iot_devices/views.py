from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q
from django.utils import timezone

from .models import Project, Device, Sensor, Actuator, SensorData, ActuatorData, ActuatorCommand
from .forms import ProjectForm, DeviceForm, SensorForm, ActuatorForm

import uuid
import json
import logging

logger = logging.getLogger(__name__)


# 项目视图
class ProjectListView(LoginRequiredMixin, ListView):
    """项目列表视图"""
    model = Project
    template_name = 'iot_devices/project_list.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        """只返回当前用户的项目"""
        return Project.objects.filter(owner=self.request.user)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """项目详情视图"""
    model = Project
    template_name = 'iot_devices/project_detail.html'
    context_object_name = 'project'
    
    def get_object(self):
        """获取项目，确保用户有权限"""
        project = get_object_or_404(Project, project_id=self.kwargs['project_id'])
        if project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限访问此项目")
        return project
    
    def get_context_data(self, **kwargs):
        """添加项目设备列表到上下文"""
        context = super().get_context_data(**kwargs)
        context['devices'] = Device.objects.filter(project=self.object)
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """项目创建视图"""
    model = Project
    form_class = ProjectForm
    template_name = 'iot_devices/project_form.html'
    
    def get_form_kwargs(self):
        """传递当前用户到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """保存前设置项目所有者为当前用户"""
        form.instance.owner = self.request.user
        messages.success(self.request, "项目创建成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到项目详情页"""
        return reverse('iot_devices:project_detail', kwargs={'project_id': self.object.project_id})


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """项目更新视图"""
    model = Project
    form_class = ProjectForm
    template_name = 'iot_devices/project_form.html'
    
    def get_object(self):
        """获取项目，确保用户有权限"""
        project = get_object_or_404(Project, project_id=self.kwargs['project_id'])
        if project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限编辑此项目")
        return project
    
    def get_form_kwargs(self):
        """传递当前用户到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "项目更新成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到项目详情页"""
        return reverse('iot_devices:project_detail', kwargs={'project_id': self.object.project_id})


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """项目删除视图"""
    model = Project
    template_name = 'iot_devices/project_confirm_delete.html'
    success_url = reverse_lazy('iot_devices:project_list')
    
    def get_object(self):
        """获取项目，确保用户有权限"""
        project = get_object_or_404(Project, project_id=self.kwargs['project_id'])
        if project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限删除此项目")
        return project
    
    def delete(self, request, *args, **kwargs):
        """删除成功后显示提示"""
        messages.success(self.request, "项目已删除")
        return super().delete(request, *args, **kwargs)


# 设备视图
class DeviceDetailView(LoginRequiredMixin, DetailView):
    """设备详情视图"""
    model = Device
    template_name = 'iot_devices/device_detail.html'
    context_object_name = 'device'
    
    def get_object(self):
        """获取设备，确保用户有权限"""
        device = get_object_or_404(Device, device_id=self.kwargs['device_id'])
        if device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限访问此设备")
        return device
    
    def get_context_data(self, **kwargs):
        """添加设备的传感器和执行器到上下文"""
        context = super().get_context_data(**kwargs)
        context['sensors'] = Sensor.objects.filter(device=self.object)
        context['actuators'] = Actuator.objects.filter(device=self.object)
        return context


class DeviceCreateView(LoginRequiredMixin, CreateView):
    """设备创建视图"""
    model = Device
    form_class = DeviceForm
    template_name = 'iot_devices/device_form.html'
    
    def get_form_kwargs(self):
        """传递当前用户和项目ID到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project_id'] = self.kwargs.get('project_id')
        return kwargs
    
    def form_valid(self, form):
        """保存前确保设备关联到正确的项目"""
        if self.kwargs.get('project_id'):
            project = get_object_or_404(Project, project_id=self.kwargs['project_id'])
            if project.owner != self.request.user:
                return HttpResponseForbidden("您没有权限在此项目下创建设备")
            form.instance.project = project
        
        # 设备密钥会在模型的save方法中自动生成
        messages.success(self.request, "设备创建成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.object.device_id})


class DeviceUpdateView(LoginRequiredMixin, UpdateView):
    """设备更新视图"""
    model = Device
    form_class = DeviceForm
    template_name = 'iot_devices/device_form.html'
    
    def get_object(self):
        """获取设备，确保用户有权限"""
        device = get_object_or_404(Device, device_id=self.kwargs['device_id'])
        if device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限编辑此设备")
        return device
    
    def get_form_kwargs(self):
        """传递当前用户到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "设备更新成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.object.device_id})


class DeviceDeleteView(LoginRequiredMixin, DeleteView):
    """设备删除视图"""
    model = Device
    template_name = 'iot_devices/device_confirm_delete.html'
    
    def get_object(self):
        """获取设备，确保用户有权限"""
        device = get_object_or_404(Device, device_id=self.kwargs['device_id'])
        if device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限删除此设备")
        return device
    
    def delete(self, request, *args, **kwargs):
        """删除成功后显示提示"""
        device = self.get_object()
        project_id = device.project.project_id
        messages.success(self.request, "设备已删除")
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        """成功后重定向到设备所属项目详情页"""
        return reverse('iot_devices:project_detail', kwargs={'project_id': self.object.project.project_id})


@login_required
def regenerate_device_key(request, device_id):
    """重新生成设备密钥"""
    if request.method == 'POST':
        device = get_object_or_404(Device, device_id=device_id)
        
        # 确保用户有权限
        if device.project.owner != request.user:
            return HttpResponseForbidden("您没有权限管理此设备")
        
        # 生成新密钥
        device.device_key = uuid.uuid4().hex
        device.save()
        
        messages.success(request, "设备密钥已重新生成")
        return redirect('iot_devices:device_detail', device_id=device_id)
    
    return redirect('iot_devices:device_detail', device_id=device_id)


# 传感器视图
class SensorCreateView(LoginRequiredMixin, CreateView):
    """传感器创建视图"""
    model = Sensor
    form_class = SensorForm
    template_name = 'iot_devices/sensor_form.html'
    
    def get_form_kwargs(self):
        """传递设备到表单"""
        kwargs = super().get_form_kwargs()
        device = get_object_or_404(Device, device_id=self.kwargs['device_id'])
        
        # 验证权限
        if device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限管理此设备的传感器")
        
        kwargs['device'] = device
        return kwargs
    
    def get_context_data(self, **kwargs):
        """添加设备到上下文"""
        context = super().get_context_data(**kwargs)
        device = get_object_or_404(Device, device_id=self.kwargs['device_id'])
        context['device'] = device
        return context
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "传感器创建成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.kwargs['device_id']})


class SensorUpdateView(LoginRequiredMixin, UpdateView):
    """传感器更新视图"""
    model = Sensor
    form_class = SensorForm
    template_name = 'iot_devices/sensor_form.html'
    
    def get_object(self):
        """获取传感器，确保用户有权限"""
        sensor = get_object_or_404(Sensor, id=self.kwargs['pk'])
        if sensor.device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限编辑此传感器")
        return sensor
    
    def get_context_data(self, **kwargs):
        """添加设备到上下文"""
        context = super().get_context_data(**kwargs)
        context['device'] = self.object.device
        return context
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "传感器更新成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.object.device.device_id})


class SensorDeleteView(LoginRequiredMixin, DeleteView):
    """传感器删除视图"""
    model = Sensor
    template_name = 'iot_devices/sensor_confirm_delete.html'
    
    def get_object(self):
        """获取传感器，确保用户有权限"""
        sensor = get_object_or_404(Sensor, id=self.kwargs['pk'])
        if sensor.device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限删除此传感器")
        return sensor
    
    def get_context_data(self, **kwargs):
        """添加设备到上下文"""
        context = super().get_context_data(**kwargs)
        context['device'] = self.object.device
        return context
    
    def delete(self, request, *args, **kwargs):
        """删除成功后显示提示"""
        sensor = self.get_object()
        device_id = sensor.device.device_id
        messages.success(self.request, "传感器已删除")
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.object.device.device_id})


class SensorDetailView(LoginRequiredMixin, DetailView):
    """传感器详情视图（含数据可视化）"""
    model = Sensor
    template_name = 'iot_devices/sensor_detail.html'
    context_object_name = 'sensor'
    
    def get_object(self):
        """获取传感器，确保用户有权限"""
        sensor = get_object_or_404(Sensor, id=self.kwargs['pk'])
        if sensor.device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限查看此传感器")
        return sensor
    
    def get_context_data(self, **kwargs):
        """添加额外数据到上下文"""
        context = super().get_context_data(**kwargs)
        context['device'] = self.object.device
        
        # 添加最近的传感器数据（最多10条）
        context['recent_data'] = SensorData.objects.filter(sensor=self.object).order_by('-timestamp')[:10]
        
        return context


# 执行器视图
class ActuatorCreateView(LoginRequiredMixin, CreateView):
    """执行器创建视图"""
    model = Actuator
    form_class = ActuatorForm
    template_name = 'iot_devices/actuator_form.html'
    
    def get_form_kwargs(self):
        """传递设备到表单"""
        kwargs = super().get_form_kwargs()
        device = get_object_or_404(Device, device_id=self.kwargs['device_id'])
        
        # 验证权限
        if device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限管理此设备的执行器")
        
        kwargs['device'] = device
        return kwargs
    
    def get_context_data(self, **kwargs):
        """添加设备到上下文"""
        context = super().get_context_data(**kwargs)
        device = get_object_or_404(Device, device_id=self.kwargs['device_id'])
        context['device'] = device
        return context
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "执行器创建成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.kwargs['device_id']})


class ActuatorUpdateView(LoginRequiredMixin, UpdateView):
    """执行器更新视图"""
    model = Actuator
    form_class = ActuatorForm
    template_name = 'iot_devices/actuator_form.html'
    
    def get_object(self):
        """获取执行器，确保用户有权限"""
        actuator = get_object_or_404(Actuator, id=self.kwargs['pk'])
        if actuator.device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限编辑此执行器")
        return actuator
    
    def get_context_data(self, **kwargs):
        """添加设备到上下文"""
        context = super().get_context_data(**kwargs)
        context['device'] = self.object.device
        return context
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "执行器更新成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.object.device.device_id})


class ActuatorDeleteView(LoginRequiredMixin, DeleteView):
    """执行器删除视图"""
    model = Actuator
    template_name = 'iot_devices/actuator_confirm_delete.html'
    
    def get_object(self):
        """获取执行器，确保用户有权限"""
        actuator = get_object_or_404(Actuator, id=self.kwargs['pk'])
        if actuator.device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限删除此执行器")
        return actuator
    
    def get_context_data(self, **kwargs):
        """添加设备到上下文"""
        context = super().get_context_data(**kwargs)
        context['device'] = self.object.device
        return context
    
    def delete(self, request, *args, **kwargs):
        """删除成功后显示提示"""
        actuator = self.get_object()
        device_id = actuator.device.device_id
        messages.success(self.request, "执行器已删除")
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        """成功后重定向到设备详情页"""
        return reverse('iot_devices:device_detail', kwargs={'device_id': self.object.device.device_id})


@login_required
def control_actuator(request, pk):
    """控制执行器"""
    if request.method == 'POST':
        actuator = get_object_or_404(Actuator, id=pk)
        
        # 验证用户权限
        if actuator.device.project.owner != request.user:
            return JsonResponse({
                'success': False,
                'message': '您没有权限控制此执行器'
            }, status=403)
        
        try:
            # 解析命令数据
            command_data = json.loads(request.body)
            
            # 检查命令值字段
            if 'value' not in command_data:
                return JsonResponse({
                    'success': False,
                    'message': '缺少value字段'
                }, status=400)
            
            value = command_data['value']
            
            # 记录命令
            command_record = ActuatorCommand.objects.create(
                actuator=actuator,
                command_value=str(value),
                source='user',
                source_detail=request.user.username,
                status='pending'
            )
            
            # 构建控制命令
            command = {
                'target': actuator.command_key,
                'action': value
            }
            
            # 导入MQTT客户端
            from mqtt_client.mqtt import MQTTClient
            mqtt_client = MQTTClient.get_instance()
            
            # 发送命令
            command_sent = mqtt_client.publish_command(actuator.device.device_id, command)
            
            if command_sent:
                # 更新执行器状态
                actuator.current_state = str(value)
                actuator.save()
                
                # 更新命令状态
                command_record.status = 'success'
                command_record.response_time = timezone.now()
                command_record.save()
                
                # 记录数据点
                ActuatorData.objects.create(
                    actuator=actuator,
                    value=str(value),
                    source='system'
                )
                
                return JsonResponse({
                    'success': True,
                    'message': '命令已发送',
                    'actuator_id': actuator.id,
                    'new_state': actuator.current_state
                })
            else:
                # 更新命令状态为失败
                command_record.status = 'failed'
                command_record.response_time = timezone.now()
                command_record.response_message = "MQTT发布失败"
                command_record.save()
                
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
            logger.error(f"控制执行器时出错: {str(e)}")
            
            # 如果已创建命令记录，更新为失败状态
            if 'command_record' in locals():
                command_record.status = 'failed'
                command_record.response_time = timezone.now()
                command_record.response_message = str(e)
                command_record.save()
                
            return JsonResponse({
                'success': False,
                'message': f'控制执行器时出错: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': '不支持的请求方法'
    }, status=405)


# 传感器数据视图
class SensorDataListView(LoginRequiredMixin, ListView):
    """传感器数据列表视图"""
    model = SensorData
    template_name = 'iot_devices/sensor_data_list.html'
    context_object_name = 'data_records'
    paginate_by = 20
    
    def get_queryset(self):
        """获取传感器的所有数据记录"""
        self.sensor = get_object_or_404(Sensor, id=self.kwargs['sensor_id'])
        
        # 检查用户是否有权限查看该传感器的数据
        if self.sensor.device.project.owner != self.request.user:
            return SensorData.objects.none()
            
        return SensorData.objects.filter(sensor=self.sensor).order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        """添加传感器和设备到上下文"""
        context = super().get_context_data(**kwargs)
        context['sensor'] = self.sensor
        context['device'] = self.sensor.device
        return context


# 执行器详情视图
class ActuatorDetailView(LoginRequiredMixin, DetailView):
    """执行器详情视图（含数据可视化）"""
    model = Actuator
    template_name = 'iot_devices/actuator_detail.html'
    context_object_name = 'actuator'
    
    def get_object(self):
        """获取执行器，确保用户有权限"""
        actuator = get_object_or_404(Actuator, id=self.kwargs['pk'])
        if actuator.device.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限查看此执行器")
        return actuator
    
    def get_context_data(self, **kwargs):
        """添加额外数据到上下文"""
        context = super().get_context_data(**kwargs)
        context['device'] = self.object.device
        
        # 添加最近的执行器数据（最多10条）
        context['recent_data'] = ActuatorData.objects.filter(actuator=self.object).order_by('-timestamp')[:10]
        
        # 添加最近的命令记录（最多10条）
        context['recent_commands'] = ActuatorCommand.objects.filter(actuator=self.object).order_by('-timestamp')[:10]
        
        return context


# 执行器数据视图
class ActuatorDataListView(LoginRequiredMixin, ListView):
    """执行器数据列表视图"""
    model = ActuatorData
    template_name = 'iot_devices/actuator_data_list.html'
    context_object_name = 'data_records'
    paginate_by = 20
    
    def get_queryset(self):
        """获取执行器的所有数据记录"""
        self.actuator = get_object_or_404(Actuator, id=self.kwargs['actuator_id'])
        
        # 检查用户是否有权限查看该执行器的数据
        if self.actuator.device.project.owner != self.request.user:
            return ActuatorData.objects.none()
        
        # 获取数据类型（数据或命令）
        data_type = self.request.GET.get('type', 'data')
        
        if data_type == 'command':
            # 如果是命令记录，则返回命令列表
            return ActuatorCommand.objects.filter(actuator=self.actuator).order_by('-timestamp')
        else:
            # 默认返回数据记录
            return ActuatorData.objects.filter(actuator=self.actuator).order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        """添加执行器和设备到上下文"""
        context = super().get_context_data(**kwargs)
        context['actuator'] = self.actuator
        context['device'] = self.actuator.device
        
        # 添加数据类型
        context['data_type'] = self.request.GET.get('type', 'data')
        
        return context
