import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from iot_devices.models import SensorData
from .models import Strategy

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SensorData)
def evaluate_strategies(sender, instance, created, **kwargs):
    """
    当新的传感器数据保存时，评估所有相关策略
    :param sender: 发送信号的模型类（SensorData）
    :param instance: 保存的SensorData实例
    :param created: 是否是新创建的记录
    :param kwargs: 其他参数
    """
    if not created:
        # 只对新创建的传感器数据进行处理
        return
    
    # 获取传感器对应的设备
    device = instance.sensor.device
    
    # 查找所有以该设备为触发源的已启用策略
    strategies = Strategy.objects.filter(
        trigger_source_device=device,
        is_enabled=True
    )
    
    if not strategies:
        # 没有相关策略，直接返回
        return
    
    logger.info(f"找到 {strategies.count()} 个关联设备 {device.name} 的策略")
    
    # 评估每个策略的条件
    for strategy in strategies:
        try:
            # 评估策略条件
            if strategy.evaluate_conditions(instance):
                logger.info(f"策略 {strategy.name} 条件满足，准备执行动作")
                # 执行策略动作
                strategy.execute_actions(instance)
            else:
                logger.debug(f"策略 {strategy.name} 条件不满足，不执行动作")
        
        except Exception as e:
            logger.error(f"评估策略 {strategy.name} 时出错: {str(e)}") 