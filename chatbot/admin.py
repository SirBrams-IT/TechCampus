from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "session_uuid", "updated_at")
    search_fields = ("title", "user__username", "session_uuid")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "timestamp")
    search_fields = ("text",)
    list_filter = ("sender",)
