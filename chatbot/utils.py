import google.generativeai as genai
from decouple import config
import logging

logger = logging.getLogger(__name__)

class SirBramsTechBot:
    def __init__(self):
        API_KEY = config('GEMINI_API_KEY')
        if not API_KEY:
            raise ValueError("GEMINI_API_KEY not found")

        genai.configure(api_key=API_KEY)
        self.model_name = self._choose_model()
        logger.info(f"✅ Using Gemini model: {self.model_name}")
        self.model = genai.GenerativeModel(self.model_name)
        self.system_prompt = (
            "You are SirBrams, an AI assistant for SirBrams Tech Virtual Campus. "
            "Guide students and mentors on technology, coding, design, and campus issues. "
            "Be friendly, professional, and precise."
        )

    def _choose_model(self):
        try:
            models = [m.name for m in genai.list_models()]
        except Exception:
            return "models/gemini-2.5-flash"
        preferred = ["models/gemini-2.5-flash", "models/gemini-2.5-pro"]
        for name in preferred:
            if name in models: return name
        for name in models:
            if "gemini" in name: return name
        return "models/gemini-2.5-flash"

    def generate_response(self, user_message, conversation_history=None):
        try:
            context = self.system_prompt + "\n\n"
            if conversation_history:
                for msg in conversation_history:
                    sender = getattr(msg, "sender", "").lower()
                    text = getattr(msg, "text", "")
                    if sender in ["user", "student"]:
                        context += f"Student: {text}\n"
                    elif sender in ["bot", "assistant"]:
                        context += f"Assistant: {text}\n"
                    elif text:
                        context += f"{text}\n"
            context += f"Student: {user_message}\nAssistant:"
            response = self.model.generate_content(context)
            if hasattr(response, "text"):
                bot_reply = response.text.strip()
            elif hasattr(response, "candidates") and response.candidates:
                bot_reply = str(response.candidates[0].content)
            else:
                bot_reply = str(response)
            if bot_reply.lower().startswith(user_message.lower()):
                bot_reply = bot_reply[len(user_message):].strip()
            return bot_reply or "I'm here! How can I assist you today?"
        except Exception as e:
            logger.exception("Error generating response: %s", e)
            return "⚠️ I encountered an error while generating a response. Please try again later."
