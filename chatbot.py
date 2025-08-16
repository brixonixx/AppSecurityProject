from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
import logging
import requests
import json
from datetime import datetime
import os

# Configure logging
logger = logging.getLogger(__name__)

# Create chatbot blueprint
chatbot = Blueprint('chatbot', __name__)

# OpenAI API configuration (you can also use Claude, Gemini, or local models)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Alternative: If using Claude API
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

class SilverSageAI:
    """AI Assistant for SilverSage - handles senior-focused conversations"""
    
    def __init__(self):
        self.system_prompt = """
        You are SageBot, an AI assistant for SilverSage, a community platform for senior citizens. 
        You are knowledgeable, patient, and empathetic. Your responses should be:
        
        - Clear and easy to understand
        - Respectful and age-appropriate
        - Focused on senior-related topics like health, technology, hobbies, family, and community
        - Helpful for navigating the SilverSage platform
        - Encouraging and positive
        
        You can help users with:
        - General questions about aging, health, and wellness
        - Technology support and explanations
        - SilverSage platform features
        - Event recommendations
        - Community engagement tips
        - Hobbies and activities for seniors
        
        Keep responses concise but warm and helpful.
        """
    
    def get_response_openai(self, user_message, conversation_history=[]):
        """Get response from OpenAI GPT"""
        if not OPENAI_API_KEY:
            return "I'm sorry, but the AI service is not configured. Please contact the administrator."
        
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history
            for msg in conversation_history[-10:]:  # Keep last 10 messages
                messages.append(msg)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            response = requests.post(OPENAI_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            return "I'm having trouble connecting to my AI service right now. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI response: {e}")
            return "I encountered an unexpected error. Please try again."
    
    def get_response_claude(self, user_message, conversation_history=[]):
        """Get response from Claude API (alternative)"""
        if not CLAUDE_API_KEY:
            return "I'm sorry, but the AI service is not configured. Please contact the administrator."
        
        try:
            headers = {
                "x-api-key": CLAUDE_API_KEY,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Format conversation for Claude
            conversation = ""
            for msg in conversation_history[-10:]:
                if msg["role"] == "user":
                    conversation += f"Human: {msg['content']}\n\n"
                else:
                    conversation += f"Assistant: {msg['content']}\n\n"
            
            conversation += f"Human: {user_message}\n\nAssistant:"
            
            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 500,
                "system": self.system_prompt,
                "messages": [{"role": "user", "content": user_message}]
            }
            
            response = requests.post(CLAUDE_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['content'][0]['text'].strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API request failed: {e}")
            return "I'm having trouble connecting to my AI service right now. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error in Claude response: {e}")
            return "I encountered an unexpected error. Please try again."
    
    def get_response_local(self, user_message, conversation_history=[]):
        """Fallback to simple rule-based responses when no API is available"""
        user_message_lower = user_message.lower()
        
        # Simple keyword-based responses
        responses = {
            'hello': "Hello! I'm SageBot, your friendly AI assistant. How can I help you today?",
            'help': "I'm here to help! I can assist with questions about health, technology, SilverSage features, or just have a friendly chat. What would you like to know?",
            'events': "You can find upcoming events in the Events section of SilverSage. There are often social gatherings, health workshops, and hobby groups to join!",
            'forum': "The Forum is a great place to connect with other community members. You can share experiences, ask questions, or join discussions on topics you're interested in.",
            'volunteer': "Volunteering is a wonderful way to stay active and give back! Check out the Volunteer section to find opportunities that match your interests and skills.",
            'health': "For health-related questions, I recommend consulting with your healthcare provider. However, I can share general wellness tips about staying active, eating well, and maintaining social connections.",
            'technology': "Technology can seem overwhelming, but take it one step at a time! I'm here to help explain things simply. What specific technology question do you have?",
            'thanks': "You're very welcome! I'm always here to help whenever you need assistance.",
            'goodbye': "Goodbye for now! Feel free to chat with me anytime you visit SilverSage. Have a wonderful day!"
        }
        
        # Check for keywords
        for keyword, response in responses.items():
            if keyword in user_message_lower:
                return response
        
        # Default response
        return "I understand you're asking about that topic. While I'd love to give you a detailed answer, my advanced AI features aren't available right now. Is there something specific about SilverSage I can help you with instead?"

# Initialize AI assistant
sage_ai = SilverSageAI()

@chatbot.route('/chat')
@login_required
def chat():
    """Main chat interface"""
    return render_template('chatbot.html')

@chatbot.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """API endpoint for chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get conversation history from session
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        conversation_history = session['chat_history']
        
        # Try different AI services in order of preference
        ai_response = None
        
        # Try OpenAI first
        if OPENAI_API_KEY:
            ai_response = sage_ai.get_response_openai(user_message, conversation_history)
        # Try Claude if OpenAI not available
        elif CLAUDE_API_KEY:
            ai_response = sage_ai.get_response_claude(user_message, conversation_history)
        # Fallback to local responses
        else:
            ai_response = sage_ai.get_response_local(user_message, conversation_history)
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        # Keep only last 20 messages (10 exchanges)
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        session['chat_history'] = conversation_history
        session.permanent = True
        
        # Log the interaction (for debugging/improvement)
        logger.info(f"Chat interaction - User: {current_user.username}, Message length: {len(user_message)}")
        
        return jsonify({
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return jsonify({'error': 'Sorry, I encountered an error. Please try again.'}), 500

@chatbot.route('/api/chat/clear', methods=['POST'])
@login_required
def clear_chat():
    """Clear chat history"""
    session['chat_history'] = []
    return jsonify({'success': True})

@chatbot.route('/api/chat/history', methods=['GET'])
@login_required
def chat_history():
    """Get chat history for current session"""
    history = session.get('chat_history', [])
    return jsonify({'history': history})

@chatbot.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_code=404, 
                         error_message='Chat page not found'), 404

@chatbot.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, 
                         error_message='Chat service error'), 500