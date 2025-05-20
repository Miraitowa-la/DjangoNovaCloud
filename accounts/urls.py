from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'
 
urlpatterns = [
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # 邀请码管理
    path('invitations/', views.InvitationCodeListView.as_view(), name='invitation_list'),
    path('invitations/create/', views.InvitationCodeCreateView.as_view(), name='invitation_create'),
    path('invitations/quick-create/', views.QuickInvitationCreateView.as_view(), name='invitation_quick_create'),
    path('invitations/<int:pk>/delete/', views.InvitationCodeDeleteView.as_view(), name='invitation_delete'),
] 