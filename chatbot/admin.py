# chatbot/admin.py
from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'created_at', 'updated_at']
    search_fields = ['session_id']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'user_message', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['user_message', 'bot_response']