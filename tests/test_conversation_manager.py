"""
Unit tests for conversation manager
"""
import pytest
from src.lettuce.conversation_manager import (
    ConversationManager,
    UserConversation,
    ConversationState,
    get_welcome_message,
    get_tech_stack_message,
    get_difficulty_message,
)


class TestUserConversation:
    """Test UserConversation class"""
    
    def test_init(self):
        """Test conversation initialization"""
        conv = UserConversation("U12345")
        assert conv.user_id == "U12345"
        assert conv.state == ConversationState.INITIAL
        assert conv.data == {}
    
    def test_update_state(self):
        """Test state updates"""
        conv = UserConversation("U12345")
        conv.update_state(ConversationState.TECH_STACK, "preference", "technology")
        
        assert conv.state == ConversationState.TECH_STACK
        assert conv.data["preference"] == "technology"
    
    def test_get_data(self):
        """Test data retrieval"""
        conv = UserConversation("U12345")
        conv.data["technology"] = "python"
        
        assert conv.get_data("technology") == "python"
        assert conv.get_data("missing") is None
    
    def test_reset(self):
        """Test conversation reset"""
        conv = UserConversation("U12345")
        conv.update_state(ConversationState.TECH_STACK, "preference", "technology")
        conv.reset()
        
        assert conv.state == ConversationState.INITIAL
        assert conv.data == {}


class TestConversationManager:
    """Test ConversationManager class"""
    
    def test_get_or_create_conversation(self):
        """Test conversation creation and retrieval"""
        manager = ConversationManager()
        
        # Create new conversation
        conv1 = manager.get_or_create_conversation("U12345")
        assert isinstance(conv1, UserConversation)
        assert conv1.user_id == "U12345"
        
        # Get existing conversation
        conv2 = manager.get_or_create_conversation("U12345")
        assert conv1 is conv2
        
        # Create different user conversation
        conv3 = manager.get_or_create_conversation("U67890")
        assert conv3 is not conv1
        assert conv3.user_id == "U67890"
    
    def test_end_conversation(self):
        """Test conversation removal"""
        manager = ConversationManager()
        manager.get_or_create_conversation("U12345")
        
        assert "U12345" in manager.conversations
        
        manager.end_conversation("U12345")
        assert "U12345" not in manager.conversations
        
        # Ending non-existent conversation should not error
        manager.end_conversation("U99999")


class TestMessageTemplates:
    """Test message template functions"""
    
    def test_welcome_message_structure(self):
        """Test welcome message has correct structure"""
        msg = get_welcome_message()
        
        assert "text" in msg
        assert "blocks" in msg
        assert len(msg["blocks"]) > 0
        
        # Check for buttons
        actions_block = next(b for b in msg["blocks"] if b["type"] == "actions")
        assert len(actions_block["elements"]) == 2
        
        # Check button action IDs
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert "preference_technology" in action_ids
        assert "preference_mission" in action_ids
    
    def test_tech_stack_message(self):
        """Test tech stack message has technology options"""
        msg = get_tech_stack_message()
        
        assert "blocks" in msg
        
        # Should have multiple action blocks
        action_blocks = [b for b in msg["blocks"] if b["type"] == "actions"]
        assert len(action_blocks) >= 2
        
        # Check for at least Python, Java, JavaScript buttons
        all_buttons = []
        for block in action_blocks:
            all_buttons.extend(block["elements"])
        
        values = [b["value"] for b in all_buttons]
        assert "python" in values
        assert "java" in values
        assert "javascript" in values
    
    def test_difficulty_message(self):
        """Test difficulty message has all levels"""
        msg = get_difficulty_message()
        
        assert "blocks" in msg
        
        action_block = next(b for b in msg["blocks"] if b["type"] == "actions")
        buttons = action_block["elements"]
        
        assert len(buttons) == 3
        
        values = [b["value"] for b in buttons]
        assert "beginner" in values
        assert "intermediate" in values
        assert "advanced" in values
