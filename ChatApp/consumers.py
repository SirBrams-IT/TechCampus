# ChatApp/consumers.py
import json
import logging
from typing import Any, Dict, Optional

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from ChatApp.schemas import IncomingMessage, OutgoingMessage, ErrorMessage
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    conversation_id: Optional[int]
    user_type: Optional[str]
    user_id: Optional[str]
    room_group_name: Optional[str]

    async def connect(self) -> None:
        try:
            kwargs: Dict[str, Any] = self.scope.get("url_route", {}).get("kwargs", {})
            self.conversation_id = int(kwargs.get("conversation_id", 0))
            self.user_type = kwargs.get("user_type")
            self.user_id = str(kwargs.get("user_id", ""))
            self.room_group_name = f"chat_{self.conversation_id}"

            logger.info(
                f"WS connect attempt: conv={self.conversation_id}, "
                f"user_type={self.user_type}, user_id={self.user_id}"
            )

            has_access: bool = await self.verify_access()

            await self.accept()

            if not has_access:
                logger.warning("WS denied — user not in conversation participants/admins")
                await self.send_error("Unauthorized", "You do not have access to this conversation")
                await self.close()
                return

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            logger.info(f"✅ WebSocket accepted and added to group: {self.room_group_name}")

        except Exception as e:
            logger.exception(f"Error during connect: {e}")
            try:
                await self.close()
            except Exception:
                pass

    async def disconnect(self, close_code: int) -> None:
        try:
            if getattr(self, "room_group_name", None):
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"WebSocket disconnected: conv={self.conversation_id}, code={close_code}")
        except Exception as e:
            logger.exception(f"Error during disconnect: {e}")

    async def receive(self, text_data: str) -> None:
        try:
            # Parse into Pydantic Incoming model
            try:
                incoming = IncomingMessage.parse_raw(text_data)
            except ValidationError as ve:
                logger.warning(f"Validation error for incoming payload: {ve}")
                await self.send_error("ValidationError", str(ve))
                return

            # Save message in DB
            saved_message = await self.save_message(
                incoming.message, incoming.sender_type, incoming.sender_id
            )
            if saved_message is None:
                await self.send_error("SaveError", "Message could not be saved.")
                return

            sender_name: str = await self.get_sender_name(
                incoming.sender_type, incoming.sender_id
            )

            # Convert timestamp to ISO string to avoid Redis datetime serialization error
            timestamp_str: Optional[str] = (
                saved_message.timestamp.isoformat() if saved_message.timestamp else None
            )

            outgoing = OutgoingMessage(
                message=incoming.message,
                sender_type=incoming.sender_type,
                sender_id=incoming.sender_id,
                sender_name=sender_name,
                timestamp=timestamp_str,
                is_own=(
                    incoming.sender_type == self.user_type
                    and str(incoming.sender_id) == str(self.user_id)
                ),
            )

            # Send dictionary (fully JSON-safe)
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat_message", "payload": outgoing.dict()}
            )

        except Exception as e:
            logger.exception(f"Error during receive: {e}")
            await self.send_error("ReceiveError", str(e))

    async def chat_message(self, event: Dict[str, Any]) -> None:
        try:
            payload = event.get("payload", {})

            try:
                outgoing = OutgoingMessage(**payload)
            except ValidationError as ve:
                logger.warning(f"Outgoing payload validation failed: {ve}")
                await self.send_error("PayloadValidationError", str(ve))
                return

            # Send JSON to WebSocket
            await self.send(text_data=outgoing.json())

        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            await self.send_error("SendError", str(e))

    async def send_error(self, error: str, detail: Optional[str] = None) -> None:
        try:
            err = ErrorMessage(error=error, detail=detail)
            await self.send(text_data=err.json())
        except Exception as e:
            logger.exception(f"Failed to send structured error: {e}")

    # -----------------------------------------------------
    # DATABASE HELPERS
    # -----------------------------------------------------
    @database_sync_to_async
    def verify_access(self) -> bool:
        try:
            from TechApp.models import Conversation, User

            conversation = Conversation.objects.get(id=self.conversation_id)
            user = User.objects.get(id=self.user_id)
            return (
                user in conversation.participants.all()
                or user in conversation.admin_participants.all()
            )
        except Exception as e:
            logger.warning(f"verify_access failed: {e}")
            return False

    @database_sync_to_async
    def save_message(self, content: str, sender_type: str, sender_id: str):
        try:
            from TechApp.models import Conversation, User, Message

            conversation = Conversation.objects.get(id=self.conversation_id)
            sender = User.objects.get(id=sender_id)

            # Validate sender role
            if sender.role != sender_type:
                logger.warning(
                    f"Role mismatch: user.role={sender.role} but sender_type={sender_type}"
                )
                return None

            # Ensure sender is part of conversation
            if not (
                sender in conversation.participants.all()
                or sender in conversation.admin_participants.all()
            ):
                logger.warning(
                    f"Sender {sender_id} not allowed in conversation {self.conversation_id}"
                )
                return None

            message = Message(conversation=conversation, content=content, sender=sender)
            message.save()

            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save()

            return message

        except Exception as e:
            logger.exception(f"save_message failed: {e}")
            return None

    @database_sync_to_async
    def get_sender_name(self, sender_type: str, sender_id: str) -> str:
        try:
            from TechApp.models import User
            user = User.objects.get(id=sender_id)
            return getattr(user, "name", user.username)
        except Exception as e:
            logger.warning(f"get_sender_name failed: {e}")
            return "Unknown"
