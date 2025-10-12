# chatbot/urls.py
from django.urls import path
from chatbot.views import ChatView, chatbot_view

urlpatterns = [
    path('chatbot/', chatbot_view, name='chatbot'), 
    path('chatbot/chat/', ChatView.as_view(), name='chat'), 
]