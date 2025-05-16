from django.urls import path
from . import views

app_name = 'mqtt_client'

urlpatterns = [
    path('api/devices/<str:device_id>/command/', views.send_device_command, name='send_device_command'),
    path('api/devices/<str:device_id>/ping/', views.send_device_ping, name='send_device_ping'),
    path('api/devices/<str:device_id>/reboot/', views.send_device_reboot, name='send_device_reboot'),
] 