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

        # Try to use the best available Gemini model explicitly
        self.model_name = self._choose_model()
        logger.info(f"✅ Using Gemini model: {self.model_name}")
        self.model = genai.GenerativeModel(self.model_name)

        self.system_prompt = (
            "You are an AI assistant for Sirbrams Tech Virtual Campus. "
            "You help students understand technology topics, give academic guidance, "
            "and reply in a friendly and professional tone."
        )

    def _choose_model(self):
        """
        Selects the best available text generation model.
        This version no longer filters by supported_methods (since new SDK changed API).
        """
        try:
            models = [m.name for m in genai.list_models()]
        except Exception as e:
            logger.exception("Failed to list models: %s", e)
            return "models/gemini-2.5-flash"  # fallback default

        # Strong preference order
        preferred = [
            "models/gemini-2.5-flash",
            "models/gemini-2.5-pro",
            "models/gemini-flash-latest",
            "models/gemini-pro-latest",
        ]

        for name in preferred:
            if name in models:
                return name

        # fallback to any gemini model
        for name in models:
            if "gemini" in name:
                return name

        raise RuntimeError(
            f"No supported Gemini model found for this API key.\nAvailable: {models}"
        )

    def generate_response(self, user_message, conversation_history=None):
        try:
            context = self.system_prompt + "\n\n"
            if conversation_history:
                for msg in conversation_history:
                    context += f"Student: {msg.user_message}\nAssistant: {msg.bot_response}\n"
            context += f"Student: {user_message}\nAssistant:"

            response = self.model.generate_content(context)

            # Extract text properly
            if hasattr(response, "text"):
                return response.text.strip()
            elif hasattr(response, "candidates") and response.candidates:
                return str(response.candidates[0].content)
            else:
                return str(response)
        except Exception as e:
            logger.exception("Error generating response: %s", e)
            return "I encountered an error while generating a response. Please try again later."
