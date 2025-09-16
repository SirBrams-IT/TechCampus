# consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from TechApp.models import Conversation, Member, AdminLogin, Message

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Extract URL kwargs
            self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
            self.user_type = self.scope['url_route']['kwargs']['user_type']
            self.user_id = str(self.scope['url_route']['kwargs']['user_id'])
            
            self.room_group_name = f'chat_{self.conversation_id}'
            logger.info(f"WebSocket connect attempt: conv={self.conversation_id}, "
                        f"user_type={self.user_type}, user_id={self.user_id}")

            # TEMPORARY: bypass access check for testing, uncomment next line to enforce
            # has_access = await self.verify_access()
            has_access = True

            if has_access:
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.accept()
                logger.info("WebSocket accepted ✅")
            else:
                logger.warning("WebSocket denied ❌ (no access)")
                await self.close()
        except Exception as e:
            logger.exception(f"Error during connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"WebSocket disconnected: conv={self.conversation_id}")
        except Exception as e:
            logger.exception(f"Error during disconnect: {e}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '')
            sender_type = data.get('sender_type', '')
            sender_id = str(data.get('sender_id', ''))

            saved_message = await self.save_message(message, sender_type, sender_id)
            sender_name = await self.get_sender_name(sender_type, sender_id)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_type': sender_type,
                    'sender_id': sender_id,
                    'sender_name': sender_name,
                    'timestamp': saved_message.timestamp.isoformat()
                }
            )
        except Exception as e:
            logger.exception(f"Error during receive: {e}")

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps({
                'message': event['message'],
                'sender_type': event['sender_type'],
                'sender_id': event['sender_id'],
                'sender_name': event['sender_name'],
                'timestamp': event['timestamp'],
                'is_own': event['sender_type'] == self.user_type and event['sender_id'] == self.user_id
            }))
        except Exception as e:
            logger.exception(f"Error sending message: {e}")

    @database_sync_to_async
    def verify_access(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            if self.user_type == 'student':
                student = Member.objects.get(id=self.user_id)
                return student in conversation.participants.all()
            else:
                mentor = AdminLogin.objects.get(id=self.user_id)
                return mentor in conversation.admin_participants.all()
        except Exception as e:
            logger.warning(f"verify_access failed: {e}")
            return False

    @database_sync_to_async
    def save_message(self, content, sender_type, sender_id):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message(conversation=conversation, content=content)

            if sender_type == 'student':
                message.sender_member = Member.objects.get(id=sender_id)
            else:
                message.sender_admin = AdminLogin.objects.get(id=sender_id)

            message.save()
            conversation.updated_at = timezone.now()
            conversation.save()
            return message
        except Exception as e:
            logger.exception(f"save_message failed: {e}")
            return None

    @database_sync_to_async
    def get_sender_name(self, sender_type, sender_id):
        try:
            if sender_type == 'student':
                return Member.objects.get(id=sender_id).name
            else:
                return AdminLogin.objects.get(id=sender_id).name
        except Exception as e:
            logger.warning(f"get_sender_name failed: {e}")
            return "Unknown"
