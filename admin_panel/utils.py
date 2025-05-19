from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog

User = get_user_model()

def get_subordinate_user_ids(user):
    """
    获取用户的所有下级用户ID（包括直接和间接下级）
    
    参数:
        user: 用户对象
    
    返回:
        包含用户ID的列表
    """
    # 用于存储所有下级用户ID的集合
    subordinate_ids = set()
    
    # 内部递归函数，用于获取用户及其下级用户的ID
    def get_subordinates(user_id):
        # 获取直接下级用户
        direct_subordinates = User.objects.filter(
            profile__parent_user_id=user_id
        ).values_list('id', flat=True)
        
        # 将直接下级添加到集合
        for sub_id in direct_subordinates:
            subordinate_ids.add(sub_id)
            # 递归获取每个下级的下级
            get_subordinates(sub_id)
    
    # 从当前用户开始递归
    get_subordinates(user.id)
    
    # 将结果转换为列表
    return list(subordinate_ids)

def get_user_and_subordinates_queryset(user):
    """
    获取包含用户自身和所有下级用户的查询集
    
    参数:
        user: 用户对象
    
    返回:
        User查询集
    """
    # 获取所有下级用户ID
    subordinate_ids = get_subordinate_user_ids(user)
    
    # 将用户自身的ID添加到列表
    user_ids = [user.id] + subordinate_ids
    
    # 返回匹配这些ID的查询集
    return User.objects.filter(id__in=user_ids)

def create_audit_log(user, action, target_object=None, details="", ip_address=None, request=None):
    """
    创建审计日志条目

    参数:
        user: 操作用户
        action: 操作类型（来自AuditLog.ACTION_*常量）
        target_object: 被操作的对象（可选）
        details: 操作详情（可选）
        ip_address: IP地址（可选）
        request: 请求对象（可选，如果提供将从中提取IP地址）
    
    返回:
        创建的AuditLog对象
    """
    # 如果提供了request但没有提供ip_address，尝试从request中获取
    if ip_address is None and request is not None:
        ip_address = get_client_ip(request)
    
    # 构建审计日志条目
    audit_log = AuditLog(
        user=user,
        action=action,
        details=details,
        ip_address=ip_address
    )
    
    # 如果有目标对象，设置GenericForeignKey
    if target_object is not None:
        content_type = ContentType.objects.get_for_model(target_object)
        audit_log.target_content_type = content_type
        audit_log.target_object_id = target_object.pk
    
    # 保存并返回
    audit_log.save()
    return audit_log

def get_client_ip(request):
    """
    从请求中获取客户端IP地址
    尝试获取X-Forwarded-For头，如果没有则回退到REMOTE_ADDR
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For格式为：client, proxy1, proxy2, ...
        # 取第一个地址，即客户端真实IP
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip 