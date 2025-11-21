import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Conversation, Message
from .utils import SirBramsTechBot


@login_required
def chatbot_view(request):
    user = request.user

    # Get or create session UUID
    session_id = request.session.get("chat_session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session["chat_session_id"] = session_id
        Conversation.objects.create(user=user, session_uuid=session_id, title=f"Chat Session - {user.username}")
    else:
        Conversation.objects.get_or_create(session_uuid=session_id, defaults={"user": user, "title": f"Chat Session - {user.username}"})

    if user.role == "student":
        base_template = "student-main.html"
        context = {"base_template": base_template, "studentinfo": user}
    elif user.role == "mentor":
        base_template = "admin_main.html"
        context = {"base_template": base_template, "admininfo": user}
    else:
        return redirect("login")

    context["username"] = user.username
    context["session_uuid"] = session_id

    # Load recent conversations
    qs = Conversation.objects.filter(user=user).order_by("-updated_at")
    conversations = []
    for c in qs:
        last = c.messages.last()
        snippet = (last.text[:120] if last and last.text else c.title or "New chat")
        conversations.append({
            "id": c.id,
            "uuid": c.session_uuid,
            "title": c.title or snippet,
            "snippet": snippet,
        })
    context["conversations"] = conversations
    return render(request, "chatbot/chat.html", context)


@login_required
@require_GET
def get_conversations(request):
    user = request.user
    qs = Conversation.objects.filter(user=user).order_by("-updated_at")
    data = []
    for c in qs:
        last = c.messages.last()
        snippet = (last.text[:120] if last and last.text else c.title or "New chat")
        data.append({
            "id": c.id,
            "uuid": c.session_uuid,
            "title": c.title or snippet,
            "snippet": snippet,
            "updated_at": c.updated_at.isoformat(),
            "created_at": c.created_at.isoformat(),
        })
    return JsonResponse({"conversations": data})


@login_required
@require_GET
def get_messages(request):
    uuid_q = request.GET.get("uuid")
    if not uuid_q:
        return JsonResponse({"error": "missing uuid"}, status=400)
    conv = get_object_or_404(Conversation, session_uuid=uuid_q, user=request.user)
    messages = [{
        "sender": m.sender,
        "text": m.text,
        "file": m.file.url if m.file else None,
        "timestamp": m.timestamp.isoformat()
    } for m in conv.messages.all()]
    return JsonResponse({"messages": messages, "conversation": {"id": conv.id, "uuid": conv.session_uuid, "title": conv.title}})


@login_required
@require_POST
def create_conversation(request):
    user = request.user
    session_uuid = str(uuid.uuid4())
    conv = Conversation.objects.create(user=user, session_uuid=session_uuid, title="New chat")
    return JsonResponse({"conversation_id": conv.id, "session_uuid": conv.session_uuid})


@login_required
@csrf_exempt
def send_message(request):
    user = request.user

    if request.content_type.startswith("multipart/form-data"):
        message_text = request.POST.get("message", "").strip()
        session_uuid = request.POST.get("session_uuid", "").strip()
        uploaded_file = request.FILES.get("file")
    else:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "invalid json"}, status=400)
        message_text = data.get("message", "").strip()
        session_uuid = data.get("session_uuid", "").strip()
        uploaded_file = None

    if not message_text and not uploaded_file:
        return JsonResponse({"error": "empty message/file"}, status=400)

    conv = Conversation.objects.filter(session_uuid=session_uuid, user=user).first()
    if not conv:
        conv = Conversation.objects.create(user=user, session_uuid=str(uuid.uuid4()), title=(message_text[:60] or "Chat"))

    msg = Message.objects.create(conversation=conv, sender="user", text=message_text)
    if uploaded_file:
        msg.file = uploaded_file
        msg.save()

    # Generate bot response
    try:
        bot = SirBramsTechBot()
        prev_msgs = list(conv.messages.order_by("-timestamp")[:10])
        bot_resp = bot.generate_response(message_text, list(reversed(prev_msgs)))
    except Exception:
        bot_resp = "Sorry, I couldn't process that right now."

    bot_msg = Message.objects.create(conversation=conv, sender="bot", text=bot_resp)

    if not conv.title or conv.title == "New chat":
        conv.title = message_text[:60] or "Chat"
    conv.updated_at = timezone.now()
    conv.save()

    return JsonResponse({"response": bot_resp, "conversation_id": conv.id, "session_uuid": conv.session_uuid})

@csrf_exempt
@login_required
def clear_chats(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    try:
        data = json.loads(request.body)
        uuids = data.get("uuids", [])
        if not uuids:
            return JsonResponse({"error": "No chats selected"}, status=400)

        # FIX: use session_uuid instead of uuid
        Conversation.objects.filter(
            user=request.user,
            session_uuid__in=uuids
        ).delete()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



