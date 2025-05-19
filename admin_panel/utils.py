from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

def get_subordinate_user_ids(user):
    """
    递归获取某用户的所有下级用户ID列表
    
    Args:
        user: User对象
        
    Returns:
        list: 所有下级用户ID列表，包括直接和间接下级
    """
    # 初始化结果列表，包含当前用户ID
    user_ids = [user.id]
    
    # 查找直接下级用户
    direct_subordinates = User.objects.filter(
        profile__parent_user=user
    )
    
    # 如果有直接下级，递归获取他们的下级
    for subordinate in direct_subordinates:
        user_ids.extend(get_subordinate_user_ids(subordinate))
    
    return user_ids

def get_user_and_subordinates_queryset(user):
    """
    获取包含用户自身和所有下级用户的查询集
    
    Args:
        user: User对象
        
    Returns:
        QuerySet: User查询集
    """
    if user.is_superuser:
        return User.objects.all()
    
    user_ids = get_subordinate_user_ids(user)
    return User.objects.filter(id__in=user_ids) 