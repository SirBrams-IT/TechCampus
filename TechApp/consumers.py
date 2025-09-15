# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from .models import Conversation, Member, AdminLogin, Message
from datetime import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user_type = self.scope['url_route']['kwargs']['user_type']
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Verify user has access to this conversation
        if await self.verify_access():
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_type = text_data_json['sender_type']
        sender_id = text_data_json['sender_id']
        
        # Save message to database
        saved_message = await self.save_message(message, sender_type, sender_id)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_type': sender_type,
                'sender_id': sender_id,
                'sender_name': await self.get_sender_name(sender_type, sender_id),
                'timestamp': saved_message.timestamp.isoformat()
            }
        )

    async def chat_message(self, event):
        message = event['message']
        sender_type = event['sender_type']
        sender_id = event['sender_id']
        sender_name = event['sender_name']
        timestamp = event['timestamp']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender_type': sender_type,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'timestamp': timestamp,
            'is_own': sender_type == self.user_type and str(sender_id) == self.user_id
        }))

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
        except (Conversation.DoesNotExist, Member.DoesNotExist, AdminLogin.DoesNotExist):
            return False

    @database_sync_to_async
    def save_message(self, content, sender_type, sender_id):
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message(conversation=conversation, content=content)
        
        if sender_type == 'student':
            student = Member.objects.get(id=sender_id)
            message.sender_member = student
        else:
            mentor = AdminLogin.objects.get(id=sender_id)
            message.sender_admin = mentor
        
        message.save()
        conversation.updated_at = timezone.now()
        conversation.save()
        return message

    @database_sync_to_async
    def get_sender_name(self, sender_type, sender_id):
        if sender_type == 'student':
            student = Member.objects.get(id=sender_id)
            return student.name
        else:
            mentor = AdminLogin.objects.get(id=sender_id)
            return mentor.name