# chatbot/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import uuid

from .models import Conversation, Message  # Fixed: use relative imports
from .utils import SirBramsTechBot

def chatbot_view(request):
    """Handle the main chatbot page view"""
    # Generate or get session ID
    session_id = request.session.get('chat_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session['chat_session_id'] = session_id
        
        # Create new conversation
        Conversation.objects.get_or_create(
            session_id=session_id,
            defaults={'session_id': session_id}
        )
    
    return render(request, 'chatbot/chat.html')

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(View):
    """Handle AJAX chat requests"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            session_id = request.session.get('chat_session_id')
            
            if not user_message:
                return JsonResponse({'error': 'Empty message'}, status=400)
            
            if not session_id:
                return JsonResponse({'error': 'No active session'}, status=400)
            
            # Get or create conversation
            conversation, created = Conversation.objects.get_or_create(
                session_id=session_id
            )
            
            # Initialize bot
            bot = SirBramsTechBot()
            
            # Get conversation history for context
            previous_messages = Message.objects.filter(
                conversation=conversation
            ).order_by('-timestamp')[:5]  # Last 5 messages for context
            
            # Generate response
            bot_response = bot.generate_response(
                user_message, 
                reversed(previous_messages)  # Reverse to maintain chronological order
            )
            
            # Save message
            Message.objects.create(
                conversation=conversation,
                user_message=user_message,
                bot_response=bot_response
            )
            
            return JsonResponse({
                'response': bot_response,
                'session_id': session_id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)