from tkinter.font import names
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path
from TechApp import views

urlpatterns = [
    
    #messaging urls
    path('api/send_message/<int:conversation_id>/', views.send_message, name='send_message'),
    path('api/messages/<int:conversation_id>/', views.get_conversation_messages, name='get_messages'),
    path('api/start_dm/', views.start_dm, name='start_dm'),
    path('api/conversations/', views.get_user_conversations, name='get_conversations'),
    path('api/create_forum/', views.create_forum, name='create_forum'),
    path('api/mentors/', views.get_available_mentors, name='get_mentors'),

]


