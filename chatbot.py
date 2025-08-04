import os
import json
import time
import requests
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatbotAI:
    """
    AI Chatbot class that handles conversation logic and AI API integration.

    This implementation supports multiple AI providers:
    - OpenAI GPT models
    - Anthropic Claude (example)
    - Local/Custom models
    """

    def __init__(self, provider="openai", model="gpt-3.5-turbo"):
        self.provider = provider
        self.model = model
        self.conversation_history: List[Dict] = []
        self.max_history = 10  # Keep last 10 messages for context

        # Initialize API settings
        self.api_key = self._get_api_key()
        self.api_url = self._get_api_url()

        # System prompt for the AI
        self.system_prompt = {
            "role": "system",
            "content": """You are a helpful, friendly AI assistant. Be concise but informative in your responses. 
            Show personality while being professional. If you don't know something, admit it rather than guessing."""
        }

        # Add system prompt to history
        self.conversation_history.append(self.system_prompt)

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variables"""
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        return None

    def _get_api_url(self) -> str:
        """Get API URL based on provider"""
        if self.provider == "openai":
            return "https://api.openai.com/v1/chat/completions"
        elif self.provider == "anthropic":
            return "https://api.anthropic.com/v1/messages"
        return ""

    def add_user_message(self, message: str):
        """Add user message to conversation history"""
        user_msg = {"role": "user", "content": message}
        self.conversation_history.append(user_msg)
        self._trim_history()

    def add_assistant_message(self, message: str):
        """Add assistant message to conversation history"""
        assistant_msg = {"role": "assistant", "content": message}
        self.conversation_history.append(assistant_msg)
        self._trim_history()

    def _trim_history(self):
        """Keep conversation history within limits"""
        # Always keep system prompt + last max_history messages
        if len(self.conversation_history) > self.max_history + 1:
            # Keep system prompt and last max_history messages
            self.conversation_history = [self.system_prompt] + self.conversation_history[-(self.max_history):]

    def get_ai_response(self, user_message: str) -> Dict:
        """
        Get AI response from the configured provider

        Returns:
            Dict with 'success', 'response', and optional 'error' keys
        """
        try:
            # Add user message to history
            self.add_user_message(user_message)

            # Check if API key is available
            if not self.api_key:
                return self._fallback_response(user_message)

            # Get response from AI provider
            if self.provider == "openai":
                response = self._get_openai_response()
            elif self.provider == "anthropic":
                response = self._get_anthropic_response()
            else:
                response = self._fallback_response(user_message)

            return response

        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "I'm sorry, I'm having trouble processing your request right now. Please try again."
            }

    def _get_openai_response(self) -> Dict:
        """Get response from OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": self.conversation_history,
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                ai_message = data['choices'][0]['message']['content'].strip()

                # Add to conversation history
                self.add_assistant_message(ai_message)

                return {
                    "success": True,
                    "response": ai_message
                }
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "response": "I'm experiencing some technical difficulties. Please try again."
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "response": "I'm taking too long to respond. Please try again."
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response": "I'm having trouble connecting to my AI service. Please try again."
            }

    def _get_anthropic_response(self) -> Dict:
        """Get response from Anthropic Claude API (example implementation)"""
        # This is a placeholder for Anthropic API integration
        # You would implement similar logic to OpenAI but with Anthropic's API format
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Convert conversation history to Anthropic format
        messages = [msg for msg in self.conversation_history if msg["role"] != "system"]

        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 500,
            "system": self.system_prompt["content"],
            "messages": messages
        }

        # Similar implementation to OpenAI...
        # For brevity, returning fallback response
        return self._fallback_response(self.conversation_history[-1]["content"])

    def _fallback_response(self, user_message: str) -> Dict:
        """
        Fallback response when AI API is not available
        Provides rule-based responses for common queries
        """
        message_lower = user_message.lower()

        # Simple rule-based responses
        responses = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What can I do for you?",
            "how are you": "I'm doing well, thank you for asking! How are you?",
            "what is your name": "I'm an AI assistant here to help you with your questions!",
            "thank you": "You're welcome! Is there anything else I can help you with?",
            "thanks": "You're welcome! Feel free to ask me anything else.",
            "bye": "Goodbye! Have a great day!",
            "goodbye": "Goodbye! Feel free to come back anytime if you need help.",
            "help": "I'm here to help! You can ask me questions about various topics, and I'll do my best to provide useful answers.",
        }

        # Check for keyword matches
        for keyword, response in responses.items():
            if keyword in message_lower:
                self.add_assistant_message(response)
                return {
                    "success": True,
                    "response": response
                }

        # Default fallback response
        default_response = f"I understand you said '{user_message}'. I'm currently running in basic mode. For full AI capabilities, please configure your API key in the environment variables."

        self.add_assistant_message(default_response)
        return {
            "success": True,
            "response": default_response
        }

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = [self.system_prompt]

    def get_conversation_summary(self) -> Dict:
        """Get summary of current conversation"""
        return {
            "total_messages": len(self.conversation_history) - 1,  # Exclude system prompt
            "conversation_length": len(self.conversation_history),
            "model": self.model,
            "provider": self.provider
        }


# Utility functions for the chatbot
def create_chatbot_instance(provider="openai", model="gpt-3.5-turbo"):
    """Factory function to create chatbot instance"""
    return ChatbotAI(provider=provider, model=model)


def process_user_input(chatbot: ChatbotAI, user_input: str) -> Dict:
    """Process user input and return AI response"""
    if not user_input or not user_input.strip():
        return {
            "success": False,
            "error": "Empty message",
            "response": "Please enter a message."
        }

    # Basic input sanitization
    user_input = user_input.strip()[:1000]  # Limit message length

    return chatbot.get_ai_response(user_input)


# Example usage and testing
if __name__ == "__main__":
    # Create chatbot instance
    bot = create_chatbot_instance()

    print("Chatbot initialized! Type 'quit' to exit.")
    print("=" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Bot: Goodbye!")
            break

        if not user_input:
            continue

        # Get AI response
        result = process_user_input(bot, user_input)

        if result["success"]:
            print(f"Bot: {result['response']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Bot: {result['response']}")

    # Print conversation summary
    summary = bot.get_conversation_summary()
    print(f"\nConversation Summary: {summary}")