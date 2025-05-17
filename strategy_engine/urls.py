from django.urls import path
from . import views

app_name = 'strategy_engine'

urlpatterns = [
    # 策略列表
    path('projects/<str:project_id>/strategies/', views.StrategyListView.as_view(), name='strategy_list'),
    # 创建策略
    path('projects/<str:project_id>/strategies/create/', views.StrategyCreateView.as_view(), name='strategy_create'),
    # 查看策略详情
    path('strategies/<int:pk>/', views.StrategyDetailView.as_view(), name='strategy_detail'),
    # 编辑策略
    path('strategies/<int:pk>/update/', views.StrategyUpdateView.as_view(), name='strategy_update'),
    # 删除策略
    path('strategies/<int:pk>/delete/', views.StrategyDeleteView.as_view(), name='strategy_delete'),
    # 启用/禁用策略
    path('strategies/<int:pk>/toggle/', views.toggle_strategy, name='toggle_strategy'),
    # 添加条件
    path('strategies/<int:strategy_id>/conditions/create/', views.ConditionCreateView.as_view(), name='condition_create'),
    # 编辑条件
    path('conditions/<int:pk>/update/', views.ConditionUpdateView.as_view(), name='condition_update'),
    # 删除条件
    path('conditions/<int:pk>/delete/', views.ConditionDeleteView.as_view(), name='condition_delete'),
    # 添加动作
    path('strategies/<int:strategy_id>/actions/create/', views.ActionCreateView.as_view(), name='action_create'),
    # 编辑动作
    path('actions/<int:pk>/update/', views.ActionUpdateView.as_view(), name='action_update'),
    # 删除动作
    path('actions/<int:pk>/delete/', views.ActionDeleteView.as_view(), name='action_delete'),
    # 查看策略日志
    path('strategies/<int:strategy_id>/logs/', views.StrategyLogListView.as_view(), name='strategy_log_list'),
] 