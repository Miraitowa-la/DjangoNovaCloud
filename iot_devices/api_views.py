from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication

import datetime

from .models import Sensor, SensorData, Actuator
from .serializers import SensorDataSerializer, SensorSerializer, ActuatorSerializer


class SensorDataAPIView(APIView):
    """传感器数据API视图"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    
    def get_sensor(self, sensor_id):
        """获取传感器并验证权限"""
        sensor = get_object_or_404(Sensor, id=sensor_id)
        if sensor.device.project.owner != self.request.user:
            raise Http404("传感器不存在或您没有权限访问")
        return sensor
    
    def get(self, request, sensor_id, format=None):
        """获取传感器数据"""
        sensor = self.get_sensor(sensor_id)
        
        # 获取时间范围参数
        period = request.query_params.get('period', '24h')  # 默认24小时
        
        # 解析时间范围
        now = timezone.now()
        if period == '1h':
            start_time = now - datetime.timedelta(hours=1)
        elif period == '12h':
            start_time = now - datetime.timedelta(hours=12)
        elif period == '24h':
            start_time = now - datetime.timedelta(hours=24)
        elif period == '7d':
            start_time = now - datetime.timedelta(days=7)
        elif period == '30d':
            start_time = now - datetime.timedelta(days=30)
        else:
            start_time = now - datetime.timedelta(hours=24)  # 默认24小时
        
        # 查询数据
        sensor_data = SensorData.objects.filter(
            sensor=sensor,
            timestamp__gte=start_time
        ).order_by('timestamp')
        
        # 序列化
        serializer = SensorDataSerializer(sensor_data, many=True)
        
        # 返回数据
        return Response({
            'sensor': SensorSerializer(sensor).data,
            'data': serializer.data,
            'period': period,
            'start_time': start_time.isoformat(),
            'end_time': now.isoformat()
        })


class ActuatorDetailAPIView(APIView):
    """执行器详情API视图"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    
    def get_actuator(self, actuator_id):
        """获取执行器并验证权限"""
        actuator = get_object_or_404(Actuator, id=actuator_id)
        if actuator.device.project.owner != self.request.user:
            raise Http404("执行器不存在或您没有权限访问")
        return actuator
    
    def get(self, request, actuator_id, format=None):
        """获取执行器详情"""
        actuator = self.get_actuator(actuator_id)
        serializer = ActuatorSerializer(actuator)
        return Response(serializer.data) 