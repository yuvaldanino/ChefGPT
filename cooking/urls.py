from django.urls import path
from . import views

urlpatterns = [
    path('', views.root_view, name='root'),
    path('home/', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('chat/new/', views.new_chat, name='new_chat'),
    path('chat/<int:chat_id>/', views.chat_view, name='chat'),
    path('chat/<int:chat_id>/send/', views.send_message, name='send_message'),
    path('chat/<int:chat_id>/save-recipe/', views.save_recipe, name='save_recipe'),
    path('recipe/<int:recipe_id>/delete/', views.delete_recipe, name='delete_recipe'),
    path('recipe/<int:recipe_id>/', views.view_recipe, name='view_recipe'),
    path('my-recipes/', views.my_recipes, name='my_recipes'),
    path('chat-list/', views.chat_list, name='chat_list'),
    path('update-sidebar-state/', views.update_sidebar_state, name='update_sidebar_state'),
    path('health/', views.health_check, name='health_check'),
] 