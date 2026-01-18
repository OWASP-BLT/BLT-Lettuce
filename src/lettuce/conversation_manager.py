"""
Conversation Manager for Slack Bot 2.0
Handles multi-step conversations with users via DM
"""
import json
from enum import Enum
from typing import Dict, Optional, List


class ConversationState(Enum):
    """States in the conversation flowchart"""
    INITIAL = "initial"
    PREFERENCE_CHOICE = "preference_choice"
    
    # Technology path
    TECH_STACK = "tech_stack"
    TECH_DIFFICULTY = "tech_difficulty"
    TECH_PROJECT_TYPE = "tech_project_type"
    TECH_RESULTS = "tech_results"
    
    # Mission path
    MISSION_GOAL = "mission_goal"
    MISSION_CONTRIBUTION = "mission_contribution"
    MISSION_RESULTS = "mission_results"
    
    # End states
    COMPLETED = "completed"


class UserConversation:
    """Represents a user's conversation state and collected data"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = ConversationState.INITIAL
        self.data = {}
        
    def update_state(self, new_state: ConversationState, key: Optional[str] = None, value: Optional[str] = None):
        """Update conversation state and optionally store data"""
        self.state = new_state
        if key and value:
            self.data[key] = value
            
    def get_data(self, key: str) -> Optional[str]:
        """Get stored conversation data"""
        return self.data.get(key)
        
    def reset(self):
        """Reset conversation to initial state"""
        self.state = ConversationState.INITIAL
        self.data = {}


class ConversationManager:
    """Manages all active user conversations"""
    
    def __init__(self):
        self.conversations: Dict[str, UserConversation] = {}
        
    def get_or_create_conversation(self, user_id: str) -> UserConversation:
        """Get existing conversation or create new one"""
        if user_id not in self.conversations:
            self.conversations[user_id] = UserConversation(user_id)
        return self.conversations[user_id]
        
    def end_conversation(self, user_id: str):
        """End and remove a conversation"""
        if user_id in self.conversations:
            del self.conversations[user_id]


# Message templates with Slack Block Kit format
def get_welcome_message() -> dict:
    """Initial greeting when user starts conversation"""
    return {
        "text": "Hi! I can help you find OWASP projects.",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "👋 *Hi! I can help you find OWASP projects.*\n\nWould you like recommendations based on *Technology* or *Mission*?"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔧 Technology-Based"},
                        "value": "technology",
                        "action_id": "preference_technology"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🎯 Mission-Based"},
                        "value": "mission",
                        "action_id": "preference_mission"
                    }
                ]
            }
        ]
    }


def get_tech_stack_message() -> dict:
    """Ask about technology/stack preference"""
    return {
        "text": "Which technology/stack are you interested in?",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🔧 *Which technology/stack are you interested in?*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🐍 Python"},
                        "value": "python",
                        "action_id": "tech_python"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "☕ Java"},
                        "value": "java",
                        "action_id": "tech_java"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📱 JavaScript"},
                        "value": "javascript",
                        "action_id": "tech_javascript"
                    }
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📱 Mobile"},
                        "value": "mobile",
                        "action_id": "tech_mobile"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "☁️ Cloud Native"},
                        "value": "cloud",
                        "action_id": "tech_cloud"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🛡️ DevSecOps"},
                        "value": "devsecops",
                        "action_id": "tech_devsecops"
                    }
                ]
            }
        ]
    }


def get_difficulty_message() -> dict:
    """Ask about difficulty level"""
    return {
        "text": "What difficulty level?",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📊 *What difficulty level are you looking for?*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🌱 Beginner"},
                        "value": "beginner",
                        "action_id": "difficulty_beginner"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⚙️ Intermediate"},
                        "value": "intermediate",
                        "action_id": "difficulty_intermediate"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🚀 Advanced"},
                        "value": "advanced",
                        "action_id": "difficulty_advanced"
                    }
                ]
            }
        ]
    }


def get_project_type_message() -> dict:
    """Ask about project type preference"""
    return {
        "text": "What type of project?",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📦 *What type of project are you interested in?*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔨 Tools"},
                        "value": "tools",
                        "action_id": "type_tools"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💻 Code Repos"},
                        "value": "code",
                        "action_id": "type_code"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📚 Documentation"},
                        "value": "documentation",
                        "action_id": "type_documentation"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🎓 Training"},
                        "value": "training",
                        "action_id": "type_training"
                    }
                ]
            }
        ]
    }


def get_mission_goal_message() -> dict:
    """Ask about mission/goal"""
    return {
        "text": "What is your goal?",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🎯 *What is your goal?*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📖 Learn AppSec"},
                        "value": "learn",
                        "action_id": "mission_learn"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💻 Contribute Code"},
                        "value": "code",
                        "action_id": "mission_code"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📝 Documentation"},
                        "value": "docs",
                        "action_id": "mission_docs"
                    }
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🏆 GSoC Prep"},
                        "value": "gsoc",
                        "action_id": "mission_gsoc"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔬 Research"},
                        "value": "research",
                        "action_id": "mission_research"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🚀 DevSecOps"},
                        "value": "devsecops",
                        "action_id": "mission_devsecops"
                    }
                ]
            }
        ]
    }


def get_contribution_type_message() -> dict:
    """Ask about contribution type"""
    return {
        "text": "What type of contribution?",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🤝 *What type of contribution are you interested in?*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💻 Code"},
                        "value": "code",
                        "action_id": "contrib_code"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📝 Documentation"},
                        "value": "documentation",
                        "action_id": "contrib_documentation"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🎨 Design"},
                        "value": "design",
                        "action_id": "contrib_design"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔬 Research"},
                        "value": "research",
                        "action_id": "contrib_research"
                    }
                ]
            }
        ]
    }
