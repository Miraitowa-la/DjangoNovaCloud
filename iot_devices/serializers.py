from rest_framework import serializers
from .models import Sensor, SensorData, Actuator


class SensorDataSerializer(serializers.ModelSerializer):
    """传感器数据序列化器"""
    value = serializers.SerializerMethodField()
    
    class Meta:
        model = SensorData
        fields = ['id', 'timestamp', 'value']
    
    def get_value(self, obj):
        """返回正确类型的值"""
        if obj.value_float is not None:
            return obj.value_float
        elif obj.value_string is not None:
            return obj.value_string
        elif obj.value_boolean is not None:
            return obj.value_boolean
        return None


class SensorSerializer(serializers.ModelSerializer):
    """传感器序列化器"""
    class Meta:
        model = Sensor
        fields = ['id', 'name', 'sensor_type', 'unit', 'value_key']


class ActuatorSerializer(serializers.ModelSerializer):
    """执行器序列化器"""
    class Meta:
        model = Actuator
        fields = ['id', 'name', 'actuator_type', 'command_key', 'current_state'] 