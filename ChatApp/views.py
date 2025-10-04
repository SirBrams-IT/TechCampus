import json
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from TechApp.models import User, Conversation, Message


# ✅ Send message
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request, conversation_id):
    try:
        data = json.loads(request.body)
        content = data.get("content")
        sender_type = data.get("sender_type")  # "student" or "mentor"
        sender_id = data.get("sender_id")

        if not content or not sender_type or not sender_id:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        conversation = get_object_or_404(Conversation, id=conversation_id)
        sender = get_object_or_404(User, id=sender_id, role=sender_type)

        # Membership check
        if sender_type == "student" and sender not in conversation.participants.all():
            return JsonResponse({"error": "Not authorized"}, status=403)
        if sender_type == "mentor" and sender not in conversation.admin_participants.all():
            return JsonResponse({"error": "Not authorized"}, status=403)

        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
        )

        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])

        return JsonResponse(
            {
                "success": True,
                "message_id": message.id,
                "timestamp": message.timestamp.isoformat(),
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ✅ Get conversation messages
@csrf_exempt
@require_http_methods(["GET"])
def get_conversation_messages(request, conversation_id):
    try:
        user_type = request.GET.get("user_type")
        user_id = request.GET.get("user_id")

        if not user_type or not user_id:
            return JsonResponse({"error": "Missing user identification"}, status=400)

        conversation = get_object_or_404(Conversation, id=conversation_id)
        user = get_object_or_404(User, id=user_id, role=user_type)

        # Membership check
        if user_type == "student" and user not in conversation.participants.all():
            return JsonResponse({"error": "Not authorized"}, status=403)
        if user_type == "mentor" and user not in conversation.admin_participants.all():
            return JsonResponse({"error": "Not authorized"}, status=403)

        messages = conversation.messages.all().order_by("timestamp")

        # Mark opposite messages as read
        conversation.messages.exclude(sender=user).update(read=True)

        messages_data = [
            {
                "id": msg.id,
                "content": msg.content,
                "sender_name": msg.get_sender_name(),
                "sender_type": msg.get_sender_type(),
                "timestamp": msg.timestamp.isoformat(),
                "is_own": msg.sender.id == int(user_id),
            }
            for msg in messages
        ]

        return JsonResponse({"messages": messages_data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ✅ Start DM
@csrf_exempt
@require_http_methods(["POST"])
def start_dm(request):
    try:
        data = json.loads(request.body)
        student_id = data.get("student_id")
        mentor_id = data.get("mentor_id")

        if not student_id or not mentor_id:
            return JsonResponse({"error": "Missing student or mentor ID"}, status=400)

        student = get_object_or_404(User, id=student_id, role="student")
        mentor = get_object_or_404(User, id=mentor_id, role="mentor")

        # Check if DM already exists
        existing_dm = (
            Conversation.objects.filter(conversation_type="dm", participants=student)
            .filter(admin_participants=mentor)
            .first()
        )
        if existing_dm:
            return JsonResponse({"conversation_id": existing_dm.id})

        # Create DM
        dm = Conversation.objects.create(conversation_type="dm")
        dm.participants.add(student)
        dm.admin_participants.add(mentor)

        return JsonResponse({"conversation_id": dm.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ✅ Get user conversations
@csrf_exempt
@require_http_methods(["GET"])
def get_user_conversations(request):
    try:
        user_type = request.GET.get("user_type")
        user_id = request.GET.get("user_id")

        if not user_type or not user_id:
            return JsonResponse({"error": "Missing user identification"}, status=400)

        user = get_object_or_404(User, id=user_id, role=user_type)

        conversations = (
            user.conversations.all()
            if user_type == "student"
            else user.admin_conversations.all()
        )

        conversations_data = []
        for conv in conversations.order_by("-updated_at"):
            last_message = conv.messages.last()

            # Unread = messages not sent by this user and not read yet
            unread_count = conv.messages.filter(read=False).exclude(sender=user).count()

            if conv.conversation_type == "dm":
                if user_type == "student":
                    other = conv.admin_participants.first()
                    name = other.name if other else "Unknown mentor"
                else:
                    other = conv.participants.first()
                    name = other.name if other else "Unknown student"
            else:
                name = conv.name or "Unnamed forum"

            conversations_data.append(
                {
                    "id": conv.id,
                    "name": name,
                    "type": conv.conversation_type,
                    "last_message": last_message.content if last_message else "",
                    "last_message_time": (
                        last_message.timestamp.isoformat() if last_message else conv.updated_at.isoformat()
                    ),
                    "unread_count": unread_count,
                }
            )

        return JsonResponse({"conversations": conversations_data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ✅ Create forum
@csrf_exempt
@require_http_methods(["POST"])
def create_forum(request):
    try:
        data = json.loads(request.body)
        name = data.get("name")
        mentor_id = data.get("mentor_id")

        if not name or not mentor_id:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        mentor = get_object_or_404(User, id=mentor_id, role="mentor")

        forum = Conversation.objects.create(conversation_type="forum", name=name)
        forum.admin_participants.add(mentor)

        # Add all students
        all_students = User.objects.filter(role="student")
        forum.participants.add(*all_students)

        return JsonResponse({"forum_id": forum.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ✅ Get available mentors
@csrf_exempt
@require_http_methods(["GET"])
def get_available_mentors(request):
    try:
        mentors = User.objects.filter(role="mentor")
        mentors_data = [
            {"id": m.id, "name": m.name, "username": m.username, "email": m.email}
            for m in mentors
        ]
        return JsonResponse({"mentors": mentors_data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
