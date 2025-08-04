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
    - OpenAI GPT models (fully implemented)
    - Anthropic Claude (fully implemented)
    - Local/Custom models (fallback)
    """

    def __init__(self, provider="openai", model="gpt-3.5-turbo"):
        self.provider = provider
        self.model = model
        self.conversation_history: List[Dict] = []
        self.max_history = 10  # Keep last 10 messages for context

        # Initialize API settings
        self.api_key = self._get_api_key()
        self.api_url = self._get_api_url()

        # Enhanced system prompt for elderly-friendly community assistant
        self.system_prompt = {
            "role": "system",
            "content": """You are a helpful, patient, and caring AI assistant designed specifically for an elderly community forum. 

Key guidelines:
- Be warm, respectful, and patient in all interactions
- Use simple, clear language and avoid technical jargon
- Provide step-by-step explanations when needed
- Show empathy and understanding for elderly users' concerns
- Help with technology questions, health information (general only), community activities, and social connections
- Encourage community participation and social interaction
- If you don't know something, admit it and suggest where they might find help
- Be encouraging and positive while being honest
- Remember this is a community forum for elderly users to connect and support each other

Topics you can help with:
- General technology questions
- Community forum usage
- Health and wellness tips (general advice only, not medical diagnosis)
- Social activities and hobbies
- Family and relationships
- Local community information
- Basic computer/internet help

Always prioritize user safety and well-being."""
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
                logger.warning(f"No API key found for {self.provider}. Using fallback response.")
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
                "response": "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment."
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

                logger.info(f"OpenAI API successful response: {len(ai_message)} characters")
                return {
                    "success": True,
                    "response": ai_message
                }
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                error_message = self._handle_api_error(response.status_code, response.text)
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "response": error_message
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "response": "I'm taking a bit longer than usual to respond. Please try again."
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "I'm having trouble connecting to my AI service. Please check your internet connection and try again."
            }

    def _get_anthropic_response(self) -> Dict:
        """Get response from Anthropic Claude API"""
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Convert conversation history to Anthropic format
        messages = []
        for msg in self.conversation_history:
            if msg["role"] != "system":
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 500,
            "system": self.system_prompt["content"],
            "messages": messages
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
                ai_message = data['content'][0]['text'].strip()

                # Add to conversation history
                self.add_assistant_message(ai_message)

                logger.info(f"Anthropic API successful response: {len(ai_message)} characters")
                return {
                    "success": True,
                    "response": ai_message
                }
            else:
                logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                error_message = self._handle_api_error(response.status_code, response.text)
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "response": error_message
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "response": "I'm taking a bit longer than usual to respond. Please try again."
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Anthropic API request error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "I'm having trouble connecting to my AI service. Please check your internet connection and try again."
            }

    def _handle_api_error(self, status_code: int, error_text: str) -> str:
        """Handle different API error codes with user-friendly messages"""
        if status_code == 401:
            return "I'm having authentication issues. Please contact support to check the API configuration."
        elif status_code == 429:
            return "I'm experiencing high demand right now. Please wait a moment and try again."
        elif status_code == 500:
            return "The AI service is temporarily unavailable. Please try again in a few minutes."
        elif status_code == 400:
            return "There was an issue with your message format. Please try rephrasing your question."
        else:
            return "I'm experiencing some technical difficulties. Please try again."

    def _fallback_response(self, user_message: str) -> Dict:
        """
        Enhanced fallback response when AI API is not available
        Provides contextual responses for elderly community forum
        """
        message_lower = user_message.lower()

        # Community-focused responses
        community_responses = {
            # Greetings
            "hello": "Hello! Welcome to our community forum. I'm here to help you connect with others and find information. What would you like to talk about today?",
            "hi": "Hi there! It's wonderful to see you here. How can I assist you with the forum or answer any questions you might have?",
            "good morning": "Good morning! I hope you're having a lovely day. How can I help you today?",
            "good afternoon": "Good afternoon! What can I do for you this afternoon?",
            "good evening": "Good evening! How has your day been? What can I help you with?",

            # About the person
            "how are you": "I'm doing well, thank you for asking! I'm here and ready to help you with anything you need. How are you feeling today?",
            "what is your name": "I'm your AI assistant for this community forum! I'm here to help you navigate the forum, answer questions, and connect with other community members.",

            # Gratitude
            "thank you": "You're very welcome! I'm so glad I could help. Please don't hesitate to ask if you need anything else.",
            "thanks": "You're welcome! It's my pleasure to help. Is there anything else you'd like to know?",

            # Farewells
            "bye": "Goodbye! Take care and have a wonderful day. Feel free to come back anytime you need help!",
            "goodbye": "Goodbye! It was lovely chatting with you. Remember, this community is here whenever you need support or just want to talk.",
            "see you later": "See you later! I'll be here whenever you need me. Take care!",

            # Help and support
            "help": "I'm here to help! You can ask me about:\n• How to use this forum\n• Connecting with other community members\n• General questions about technology\n• Health and wellness tips\n• Community activities\n• Or just have a friendly chat!\n\nWhat would you like to know?",
            "forum": "This forum is a wonderful place for our community to connect! You can share stories, ask questions, offer help to others, and make new friends. Would you like me to explain how to post a message or find specific topics?",
            "technology": "Technology can be confusing sometimes, but don't worry - we're here to help each other learn! What specific technology question do you have? It could be about using this website, your computer, or your phone.",

            # Health and wellness
            "health": "While I can't provide medical advice, I'm happy to share general wellness tips! For specific health concerns, please consult with your doctor. Is there a general wellness topic you'd like to discuss?",
            "doctor": "For any medical concerns, it's always best to speak with your healthcare provider. They know your situation best. Is there something general about health and wellness I can help with instead?",

            # Loneliness and social
            "lonely": "I'm sorry you're feeling lonely. This community forum is here to help connect you with others who understand. Have you tried posting in our general discussion area? Many members are very welcoming and would love to chat.",
            "friends": "Making friends is one of the wonderful benefits of this community! Try commenting on posts that interest you, or share something about yourself in the introductions section. People here are very friendly.",

            # Technology help
            "computer": "Computer troubles can be frustrating! What specific issue are you having? I might be able to give you some simple steps to try, or I can suggest posting your question in our tech help section.",
            "internet": "Internet issues can be tricky. Are you having trouble with this website specifically, or with your internet connection in general? Sometimes a simple restart of your router can help!",
            "password": "Password issues are common! If you're having trouble with your forum password, look for a 'Forgot Password' link on the login page. For other passwords, make sure to write them down in a safe place.",

            # Family
            "family": "Family is so important! Many of our community members love sharing stories about their families. Consider posting about your family in our family stories section - others would love to hear about them!",
            "grandchildren": "Grandchildren bring such joy! Our community has many grandparents who love sharing stories and photos. Have you thought about posting about your grandchildren in our family section?",

            # Activities
            "activities": "There are many wonderful activities discussed in our forum! From gardening and cooking to crafts and reading groups. What kinds of activities interest you?",
            "hobbies": "Hobbies are a great way to stay active and meet people with similar interests! What hobbies do you enjoy? I'm sure there are others here who share your interests."
        }

        # Check for keyword matches
        for keyword, response in community_responses.items():
            if keyword in message_lower:
                self.add_assistant_message(response)
                return {
                    "success": True,
                    "response": response
                }

        # Context-aware responses based on message content
        if any(word in message_lower for word in ["sad", "depressed", "down", "upset"]):
            response = "I'm sorry you're feeling this way. Remember that you're not alone - this community cares about you. Sometimes talking with others who understand can help. Consider sharing your feelings in our support section, or speak with a trusted friend or counselor."
            self.add_assistant_message(response)
            return {"success": True, "response": response}

        if any(word in message_lower for word in ["pain", "hurt", "sick", "illness"]):
            response = "I'm sorry to hear you're not feeling well. While I can't provide medical advice, I encourage you to speak with your healthcare provider about any health concerns. In the meantime, our community support section might offer comfort and understanding."
            self.add_assistant_message(response)
            return {"success": True, "response": response}

        if any(word in message_lower for word in ["confused", "don't understand", "lost", "stuck"]):
            response = "It's completely normal to feel confused sometimes! Don't worry - we're all learning together. Can you tell me more specifically what you're having trouble with? I'd be happy to try to explain it step by step."
            self.add_assistant_message(response)
            return {"success": True, "response": response}

        # Default response with helpful context
        default_response = f"Thank you for sharing that with me. I understand you mentioned: '{user_message}'. While I'm currently running in basic mode, I'm still here to help! You can ask me about using this forum, connecting with community members, or general questions. For full AI capabilities with detailed answers, our technical team is working on the connection. What would you like to know more about?"

        self.add_assistant_message(default_response)
        return {
            "success": True,
            "response": default_response
        }

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = [self.system_prompt]
        logger.info("Conversation history cleared")

    def get_conversation_summary(self) -> Dict:
        """Get summary of current conversation"""
        return {
            "total_messages": len(self.conversation_history) - 1,  # Exclude system prompt
            "conversation_length": len(self.conversation_history),
            "model": self.model,
            "provider": self.provider,
            "api_key_configured": bool(self.api_key)
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
    user_input = user_input.strip()[:2000]  # Limit message length

    return chatbot.get_ai_response(user_input)


# Example usage and testing
if __name__ == "__main__":
    print("🤖 Community Chatbot Test")
    print("=" * 50)

    # Test with different providers
    providers_to_test = ["openai"]  # Add "anthropic" if you have that key

    for provider in providers_to_test:
        print(f"\nTesting {provider.upper()} provider...")
        bot = create_chatbot_instance(provider=provider)

        # Test API key configuration
        summary = bot.get_conversation_summary()
        print(f"API Key configured: {summary['api_key_configured']}")

        if summary['api_key_configured']:
            print(f"✅ {provider} API key found")
        else:
            print(f"⚠️  {provider} API key not found - will use fallback responses")

        break  # Just test the first available provider

    # Interactive chat
    bot = create_chatbot_instance()
    print("\n🎯 Chatbot initialized! Type 'quit' to exit.")
    print("Try asking: 'hello', 'help', 'how to use forum', or any question!")
    print("=" * 50)

    while True:
        user_input = input("\n👤 You: ").strip()

        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("🤖 Bot: Take care! Have a wonderful day!")
            break

        if not user_input:
            continue

        # Get AI response
        result = process_user_input(bot, user_input)

        if result["success"]:
            print(f"🤖 Bot: {result['response']}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            print(f"🤖 Bot: {result['response']}")

    # Print conversation summary
    summary = bot.get_conversation_summary()
    print(f"\n📊 Conversation Summary:")
    print(f"   Messages exchanged: {summary['total_messages']}")
    print(f"   Provider: {summary['provider']}")
    print(f"   Model: {summary['model']}")
    print(f"   API configured: {summary['api_key_configured']}")