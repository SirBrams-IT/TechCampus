from django.db import models
from django.conf import settings
import uuid

class Conversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chatbot_conversations"
    )
    title = models.CharField(max_length=200, blank=True)
    session_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title or f"Chat with {self.user.username} ({self.created_at.strftime('%b %d, %Y')})"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"Chat with {self.user.username}"
        super().save(*args, **kwargs)


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.CharField(
        max_length=10,
        choices=(
            ("user", "User"),
            ("bot", "Bot"),
        )
    )
    text = models.TextField(blank=True)
    file = models.FileField(upload_to="chat_uploads/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("timestamp",)

    def __str__(self):
        preview = (self.text[:40] + '...') if len(self.text) > 40 else self.text
        return f"[{self.sender}] {preview} ({self.timestamp.strftime('%H:%M')})"
