from django.urls import path
from . import views
from . import api_views

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
    
    # 传感器相关URLs
    path('devices/<str:device_id>/sensors/create/', views.SensorCreateView.as_view(), name='sensor_create'),
    path('sensors/<int:pk>/', views.SensorDetailView.as_view(), name='sensor_detail'),
    path('sensors/<int:pk>/update/', views.SensorUpdateView.as_view(), name='sensor_update'),
    path('sensors/<int:pk>/delete/', views.SensorDeleteView.as_view(), name='sensor_delete'),
    
    # 执行器相关URLs
    path('devices/<str:device_id>/actuators/create/', views.ActuatorCreateView.as_view(), name='actuator_create'),
    path('actuators/<int:pk>/update/', views.ActuatorUpdateView.as_view(), name='actuator_update'),
    path('actuators/<int:pk>/delete/', views.ActuatorDeleteView.as_view(), name='actuator_delete'),
    path('api/actuators/<int:pk>/control/', views.control_actuator, name='control_actuator'),
    
    # API URLs
    path('api/sensors/<int:sensor_id>/data/', api_views.SensorDataAPIView.as_view(), name='sensor_data_api'),
    path('api/actuators/<int:actuator_id>/', api_views.ActuatorDetailAPIView.as_view(), name='actuator_detail_api'),
] 