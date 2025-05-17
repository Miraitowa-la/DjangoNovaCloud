from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q

from iot_devices.models import Project, Device
from .models import Strategy, Condition, Action, StrategyLog
from .forms import StrategyForm, ConditionForm, ActionForm

import logging

logger = logging.getLogger(__name__)


# 策略视图
class StrategyListView(LoginRequiredMixin, ListView):
    """策略列表视图"""
    model = Strategy
    template_name = 'strategy_engine/strategy_list.html'
    context_object_name = 'strategies'
    
    def get_queryset(self):
        """获取当前项目的策略列表"""
        self.project = get_object_or_404(Project, project_id=self.kwargs['project_id'])
        
        # 检查用户是否有权限查看该项目
        if self.project.owner != self.request.user:
            return Strategy.objects.none()
            
        return Strategy.objects.filter(project=self.project)
    
    def get_context_data(self, **kwargs):
        """添加项目到上下文"""
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context


class StrategyDetailView(LoginRequiredMixin, DetailView):
    """策略详情视图"""
    model = Strategy
    template_name = 'strategy_engine/strategy_detail.html'
    context_object_name = 'strategy'
    
    def get_object(self):
        """确保用户有权限查看策略"""
        strategy = super().get_object()
        if strategy.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限查看此策略")
        return strategy
    
    def get_context_data(self, **kwargs):
        """添加条件和动作到上下文"""
        context = super().get_context_data(**kwargs)
        context['conditions'] = Condition.objects.filter(strategy=self.object).order_by('id')
        context['actions'] = Action.objects.filter(strategy=self.object)
        context['recent_logs'] = StrategyLog.objects.filter(strategy=self.object).order_by('-timestamp')[:10]
        return context


class StrategyCreateView(LoginRequiredMixin, CreateView):
    """策略创建视图"""
    model = Strategy
    form_class = StrategyForm
    template_name = 'strategy_engine/strategy_form.html'
    
    def get_form_kwargs(self):
        """传递用户和项目ID到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project_id'] = self.kwargs.get('project_id')
        return kwargs
    
    def get_context_data(self, **kwargs):
        """添加项目到上下文"""
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, project_id=self.kwargs['project_id'])
        context['action'] = '创建'
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """确保用户有权限创建策略"""
        project = get_object_or_404(Project, project_id=self.kwargs['project_id'])
        if project.owner != request.user:
            return HttpResponseForbidden("您没有权限在此项目中创建策略")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "策略创建成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.object.pk})


class StrategyUpdateView(LoginRequiredMixin, UpdateView):
    """策略更新视图"""
    model = Strategy
    form_class = StrategyForm
    template_name = 'strategy_engine/strategy_form.html'
    
    def get_form_kwargs(self):
        """传递用户和项目ID到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_object(self):
        """确保用户有权限编辑策略"""
        strategy = super().get_object()
        if strategy.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限编辑此策略")
        return strategy
    
    def get_context_data(self, **kwargs):
        """添加项目到上下文"""
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['action'] = '编辑'
        return context
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "策略更新成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.object.pk})


class StrategyDeleteView(LoginRequiredMixin, DeleteView):
    """策略删除视图"""
    model = Strategy
    template_name = 'strategy_engine/strategy_confirm_delete.html'
    
    def get_object(self):
        """确保用户有权限删除策略"""
        strategy = super().get_object()
        if strategy.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限删除此策略")
        return strategy
    
    def get_context_data(self, **kwargs):
        """添加项目到上下文"""
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context
    
    def delete(self, request, *args, **kwargs):
        """删除成功后显示提示"""
        strategy = self.get_object()
        project = strategy.project
        messages.success(self.request, "策略已删除")
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        """成功后重定向到策略列表页"""
        return reverse('strategy_engine:strategy_list', kwargs={'project_id': self.object.project.project_id})


@login_required
def toggle_strategy(request, pk):
    """启用/禁用策略"""
    strategy = get_object_or_404(Strategy, pk=pk)
    
    # 检查权限
    if strategy.project.owner != request.user:
        return JsonResponse({'status': 'error', 'message': '没有权限操作此策略'}, status=403)
    
    # 切换状态
    strategy.is_enabled = not strategy.is_enabled
    strategy.save()
    
    status = '启用' if strategy.is_enabled else '禁用'
    messages.success(request, f"策略已{status}")
    
    return JsonResponse({
        'status': 'success',
        'is_enabled': strategy.is_enabled,
        'message': f'策略已{status}'
    })


# 条件视图
class ConditionCreateView(LoginRequiredMixin, CreateView):
    """条件创建视图"""
    model = Condition
    form_class = ConditionForm
    template_name = 'strategy_engine/condition_form.html'
    
    def get_form_kwargs(self):
        """传递策略ID和用户到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['strategy_id'] = self.kwargs.get('strategy_id')
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """添加策略到上下文"""
        context = super().get_context_data(**kwargs)
        context['strategy'] = get_object_or_404(Strategy, pk=self.kwargs['strategy_id'])
        context['action'] = '添加'
        context['value_type_fields'] = {
            'float': 'threshold_value_float',
            'string': 'threshold_value_string',
            'boolean': 'threshold_value_boolean',
        }
        context['next_condition'] = Condition.objects.filter(strategy_id=self.kwargs['strategy_id']).exists()
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """确保用户有权限创建条件"""
        strategy = get_object_or_404(Strategy, pk=self.kwargs['strategy_id'])
        if strategy.project.owner != request.user:
            return HttpResponseForbidden("您没有权限为此策略添加条件")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "条件添加成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.kwargs['strategy_id']})


class ConditionUpdateView(LoginRequiredMixin, UpdateView):
    """条件更新视图"""
    model = Condition
    form_class = ConditionForm
    template_name = 'strategy_engine/condition_form.html'
    
    def get_form_kwargs(self):
        """传递用户到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_object(self):
        """确保用户有权限编辑条件"""
        condition = super().get_object()
        if condition.strategy.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限编辑此条件")
        return condition
    
    def get_context_data(self, **kwargs):
        """添加策略到上下文"""
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.object.strategy
        context['action'] = '编辑'
        context['value_type_fields'] = {
            'float': 'threshold_value_float',
            'string': 'threshold_value_string',
            'boolean': 'threshold_value_boolean',
        }
        context['next_condition'] = Condition.objects.filter(strategy=self.object.strategy).exclude(pk=self.object.pk).exists()
        return context
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "条件更新成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.object.strategy.pk})


class ConditionDeleteView(LoginRequiredMixin, DeleteView):
    """条件删除视图"""
    model = Condition
    template_name = 'strategy_engine/condition_confirm_delete.html'
    
    def get_object(self):
        """确保用户有权限删除条件"""
        condition = super().get_object()
        if condition.strategy.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限删除此条件")
        return condition
    
    def get_context_data(self, **kwargs):
        """添加策略到上下文"""
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.object.strategy
        return context
    
    def delete(self, request, *args, **kwargs):
        """删除成功后显示提示"""
        messages.success(self.request, "条件已删除")
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.object.strategy.pk})


# 动作视图
class ActionCreateView(LoginRequiredMixin, CreateView):
    """动作创建视图"""
    model = Action
    form_class = ActionForm
    template_name = 'strategy_engine/action_form.html'
    
    def get_form_kwargs(self):
        """传递策略ID和用户到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['strategy_id'] = self.kwargs.get('strategy_id')
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """添加策略到上下文"""
        context = super().get_context_data(**kwargs)
        context['strategy'] = get_object_or_404(Strategy, pk=self.kwargs['strategy_id'])
        context['action'] = '添加'
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """确保用户有权限创建动作"""
        strategy = get_object_or_404(Strategy, pk=self.kwargs['strategy_id'])
        if strategy.project.owner != request.user:
            return HttpResponseForbidden("您没有权限为此策略添加动作")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "动作添加成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.kwargs['strategy_id']})


class ActionUpdateView(LoginRequiredMixin, UpdateView):
    """动作更新视图"""
    model = Action
    form_class = ActionForm
    template_name = 'strategy_engine/action_form.html'
    
    def get_form_kwargs(self):
        """传递用户到表单"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_object(self):
        """确保用户有权限编辑动作"""
        action = super().get_object()
        if action.strategy.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限编辑此动作")
        return action
    
    def get_context_data(self, **kwargs):
        """添加策略到上下文"""
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.object.strategy
        context['action'] = '编辑'
        return context
    
    def form_valid(self, form):
        """保存成功后显示提示"""
        messages.success(self.request, "动作更新成功")
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.object.strategy.pk})


class ActionDeleteView(LoginRequiredMixin, DeleteView):
    """动作删除视图"""
    model = Action
    template_name = 'strategy_engine/action_confirm_delete.html'
    
    def get_object(self):
        """确保用户有权限删除动作"""
        action = super().get_object()
        if action.strategy.project.owner != self.request.user:
            raise HttpResponseForbidden("您没有权限删除此动作")
        return action
    
    def get_context_data(self, **kwargs):
        """添加策略到上下文"""
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.object.strategy
        return context
    
    def delete(self, request, *args, **kwargs):
        """删除成功后显示提示"""
        messages.success(self.request, "动作已删除")
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        """成功后重定向到策略详情页"""
        return reverse('strategy_engine:strategy_detail', kwargs={'pk': self.object.strategy.pk})


# 策略日志视图
class StrategyLogListView(LoginRequiredMixin, ListView):
    """策略日志列表视图"""
    model = StrategyLog
    template_name = 'strategy_engine/strategy_log_list.html'
    context_object_name = 'logs'
    paginate_by = 20
    
    def get_queryset(self):
        """获取策略的日志列表"""
        self.strategy = get_object_or_404(Strategy, pk=self.kwargs['strategy_id'])
        
        # 检查用户是否有权限查看该策略的日志
        if self.strategy.project.owner != self.request.user:
            return StrategyLog.objects.none()
            
        return StrategyLog.objects.filter(strategy=self.strategy).order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        """添加策略到上下文"""
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.strategy
        context['project'] = self.strategy.project
        return context
