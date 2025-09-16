import json
import requests
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
# Import all necessary models from TechApp
from TechApp.models import ( Member,Contact,Conversation,Message, AdminLogin)

# send messages view
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request, conversation_id):
    try:
        data = json.loads(request.body)
        content = data.get('content')
        sender_type = data.get('sender_type')  # 'student' or 'mentor'
        sender_id = data.get('sender_id')
        
        if not content or not sender_type or not sender_id:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Create the message
        message = Message(conversation=conversation, content=content)
        
        if sender_type == 'student':
            student = get_object_or_404(Member, id=sender_id)
            # Verify student is in conversation
            if student not in conversation.participants.all():
                return JsonResponse({'error': 'Not authorized'}, status=403)
            message.sender_member = student
        else:
            mentor = get_object_or_404(AdminLogin, id=sender_id)
            # Verify mentor is in conversation
            if mentor not in conversation.admin_participants.all():
                return JsonResponse({'error': 'Not authorized'}, status=403)
            message.sender_admin = mentor
        
        message.save()
        conversation.updated_at = timezone.now()
        conversation.save()
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'timestamp': message.timestamp.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_conversation_messages(request, conversation_id):
    try:
        user_type = request.GET.get('user_type')
        user_id = request.GET.get('user_id')
        
        if not user_type or not user_id:
            return JsonResponse({'error': 'Missing user identification'}, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Verify user has access to this conversation
        if user_type == 'student':
            student = get_object_or_404(Member, id=user_id)
            if student not in conversation.participants.all():
                return JsonResponse({'error': 'Not authorized'}, status=403)
        else:
            mentor = get_object_or_404(AdminLogin, id=user_id)
            if mentor not in conversation.admin_participants.all():
                return JsonResponse({'error': 'Not authorized'}, status=403)
        
        # Get messages
        messages = conversation.messages.all().order_by('timestamp')
        
        # Mark messages as read for the requesting user
        if user_type == 'student':
            conversation.messages.exclude(sender_member__isnull=True).update(read=True)
        else:
            conversation.messages.exclude(sender_admin__isnull=True).update(read=True)
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'content': msg.content,
                'sender_name': msg.get_sender_name(),
                'sender_type': msg.get_sender_type(),
                'timestamp': msg.timestamp.isoformat(),
                'is_own': (user_type == 'student' and msg.sender_member and msg.sender_member.id == int(user_id)) or 
                          (user_type == 'mentor' and msg.sender_admin and msg.sender_admin.id == int(user_id))
            })
        
        return JsonResponse({'messages': messages_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def start_dm(request):
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        mentor_id = data.get('mentor_id')
        
        if not student_id or not mentor_id:
            return JsonResponse({'error': 'Missing student or mentor ID'}, status=400)
        
        student = get_object_or_404(Member, id=student_id)
        mentor = get_object_or_404(AdminLogin, id=mentor_id)
        
        # Check if DM already exists
        existing_dm = Conversation.objects.filter(
            conversation_type='dm',
            participants=student,
            admin_participants=mentor
        ).first()
        
        if existing_dm:
            return JsonResponse({'conversation_id': existing_dm.id})
        
        # Create new DM
        dm = Conversation(conversation_type='dm')
        dm.save()
        dm.participants.add(student)
        dm.admin_participants.add(mentor)
        
        return JsonResponse({'conversation_id': dm.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_user_conversations(request):
    try:
        user_type = request.GET.get('user_type')
        user_id = request.GET.get('user_id')
        
        if not user_type or not user_id:
            return JsonResponse({'error': 'Missing user identification'}, status=400)
        
        if user_type == 'student':
            user = get_object_or_404(Member, id=user_id)
            conversations = user.conversations.all()
        else:
            user = get_object_or_404(AdminLogin, id=user_id)
            conversations = user.conversations.all()
        
        conversations_data = []
        for conv in conversations:
            last_message = conv.messages.last()
            unread_count = conv.messages.filter(read=False).count()
            
            # Get conversation name and other participant info
            if conv.conversation_type == 'dm':
                # For DMs, get the other participant's name
                if user_type == 'student':
                    other_participants = list(conv.admin_participants.all())
                    name = other_participants[0].name if other_participants else "Unknown"
                else:
                    other_participants = list(conv.participants.all())
                    name = other_participants[0].name if other_participants else "Unknown"
            else:
                # For forums, use the forum name
                name = conv.name
            
            conversations_data.append({
                'id': conv.id,
                'name': name,
                'type': conv.conversation_type,
                'last_message': last_message.content if last_message else '',
                'last_message_time': last_message.timestamp if last_message else conv.updated_at,
                'unread_count': unread_count
            })
        
        return JsonResponse({'conversations': conversations_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_forum(request):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        mentor_id = data.get('mentor_id')
        
        if not name or not mentor_id:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        mentor = get_object_or_404(AdminLogin, id=mentor_id)
        
        # Create forum
        forum = Conversation(conversation_type='forum', name=name)
        forum.save()
        forum.admin_participants.add(mentor)
        
        # Add all students to the forum
        all_students = Member.objects.all()
        for student in all_students:
            forum.participants.add(student)
        
        return JsonResponse({'forum_id': forum.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_available_mentors(request):
    try:
        mentors = AdminLogin.objects.all()
        mentors_data = [{
            'id': mentor.id,
            'name': mentor.name,
            'username': mentor.username,
            'email': mentor.email
        } for mentor in mentors]
        
        return JsonResponse({'mentors': mentors_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
#notifications
def latest_messages(request):
    messages_count = Contact.objects.count()  # or filter for unread if you track it
    latest_messages = Contact.objects.order_by('-created_at')[:5]
    return {
        'messages_count': messages_count,
        'latest_messages': latest_messages,
    }    
