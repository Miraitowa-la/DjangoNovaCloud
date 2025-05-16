from django.urls import path
from . import views

app_name = 'iot_devices'

urlpatterns = [
    # 项目相关URLs
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<str:project_id>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<str:project_id>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<str:project_id>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    
    # 设备相关URLs
    path('projects/<str:project_id>/devices/create/', views.DeviceCreateView.as_view(), name='device_create'),
    path('devices/<str:device_id>/', views.DeviceDetailView.as_view(), name='device_detail'),
    path('devices/<str:device_id>/update/', views.DeviceUpdateView.as_view(), name='device_update'),
    path('devices/<str:device_id>/delete/', views.DeviceDeleteView.as_view(), name='device_delete'),
    path('devices/<str:device_id>/regenerate_key/', views.regenerate_device_key, name='regenerate_device_key'),
] 