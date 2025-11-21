from django.urls import path
from . import views

urlpatterns = [
    path("", views.chatbot_view, name="chatbot"),
    path("conversations/", views.get_conversations, name="chat_conversations"),
    path("messages/", views.get_messages, name="chat_messages"),
    path("create/", views.create_conversation, name="chat_create"),
    path("send/", views.send_message, name="chat_send"),
    path('api/clear_chats/', views.clear_chats, name='clear_chats')


]
