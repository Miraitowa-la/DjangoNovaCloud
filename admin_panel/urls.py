from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # 用户管理
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/view/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<int:pk>/toggle_active/', views.UserToggleActiveView.as_view(), name='user_toggle_active'),
    path('users/<int:pk>/reset_password/', views.UserResetPasswordView.as_view(), name='user_reset_password'),
] 