# chatbot/utils.py
import google.generativeai as genai
from decouple import config
import logging

logger = logging.getLogger(__name__)


class SirBramsTechBot:
    def __init__(self):
        API_KEY = config('GEMINI_API_KEY')
        if not API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=API_KEY)

        # Select the best model available
        self.model_name = self._choose_model()
        logger.info(f"✅ Using Gemini model: {self.model_name}")
        self.model = genai.GenerativeModel(self.model_name)

        # System instruction for tone and role
        self.system_prompt = (
            "You are SirBrams, an AI assistant for SirBrams Tech Virtual Campus. "
            "Your role is to guide students and mentors on technology, coding, design, and campus-related issues. "
            "Be friendly, professional, and precise in every response."
        )

    def _choose_model(self):
        """Selects the best available Gemini model."""
        try:
            models = [m.name for m in genai.list_models()]
        except Exception as e:
            logger.exception("Failed to list models: %s", e)
            return "models/gemini-2.5-flash"  # default fallback

        preferred = [
            "models/gemini-2.5-flash",
            "models/gemini-2.5-pro",
            "models/gemini-flash-latest",
            "models/gemini-pro-latest",
        ]

        for name in preferred:
            if name in models:
                return name

        for name in models:
            if "gemini" in name:
                return name

        raise RuntimeError(f"No supported Gemini model found. Available: {models}")

    def generate_response(self, user_message, conversation_history=None):
        """
        Generates a contextual response based on previous conversation messages.
        This version safely handles flexible field names in Message model.
        """
        try:
            context = self.system_prompt + "\n\n"

            # Safely build conversation context
            if conversation_history:
                for msg in conversation_history:
                    # Try to infer message roles dynamically
                    sender = getattr(msg, "sender", None)
                    text = getattr(msg, "content", None) or getattr(msg, "text", None) or getattr(msg, "message", None)

                    # Backward compatibility with old model fields
                    if hasattr(msg, "user_message") and hasattr(msg, "bot_response"):
                        context += f"Student: {msg.user_message}\nAssistant: {msg.bot_response}\n"
                    elif sender and sender.lower() in ["student", "user"]:
                        context += f"Student: {text}\n"
                    elif sender and sender.lower() in ["mentor", "assistant", "bot"]:
                        context += f"Assistant: {text}\n"
                    elif text:
                        # fallback
                        context += f"{text}\n"

            # Append new user query
            context += f"Student: {user_message}\nAssistant:"

            # Generate using Gemini
            response = self.model.generate_content(context)

            # Extract final text safely
            if hasattr(response, "text"):
                bot_reply = response.text.strip()
            elif hasattr(response, "candidates") and response.candidates:
                bot_reply = str(response.candidates[0].content)
            else:
                bot_reply = str(response)

            # Remove accidental echo duplication
            if bot_reply.lower().startswith(user_message.lower()):
                bot_reply = bot_reply[len(user_message):].strip()

            return bot_reply or "I'm here! How can I assist you today?"

        except Exception as e:
            logger.exception("Error generating response: %s", e)
            return "⚠️ I encountered an error while generating a response. Please try again later."
