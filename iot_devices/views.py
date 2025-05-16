from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q

from .models import Project, Device, Sensor, Actuator
from .forms import ProjectForm, DeviceForm

import uuid


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
