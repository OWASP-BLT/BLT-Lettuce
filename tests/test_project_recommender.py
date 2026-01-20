"""
Unit tests for project recommender
"""
import json
import os

import pytest

from src.lettuce.project_recommender import ProjectRecommender, format_recommendations_message


class TestProjectRecommender:
    """Test ProjectRecommender class"""

    @pytest.fixture
    def recommender(self):
        """Create recommender with real projects data"""
        projects_path = os.path.join(os.path.dirname(__file__), "..", "data", "projects.json")
        return ProjectRecommender(projects_path)

    def test_recommend_tech_based_python(self, recommender):
        """Test technology-based recommendations for Python"""
        results = recommender.recommend_tech_based(
            technology="python", difficulty="beginner", project_type="tools"
        )

        # Should return at most 3 projects
        assert len(results) <= 3

        # Each result should have required fields
        for project in results:
            assert "name" in project
            assert "description" in project
            assert "url" in project
            assert "key" in project

    def test_recommend_tech_based_javascript_training(self, recommender):
        """Test JavaScript training recommendations"""
        results = recommender.recommend_tech_based(
            technology="javascript", difficulty="beginner", project_type="training"
        )

        assert len(results) <= 3

        # Should prioritize well-known training projects like Juice Shop
        if results:
            names = [p["name"].lower() for p in results]
            # At least one popular training project should be recommended
            has_training = any(
                "juice" in name or "webgoat" in name or "shepherd" in name for name in names
            )
            assert has_training

    def test_recommend_mission_based_learn(self, recommender):
        """Test mission-based recommendations for learning"""
        results = recommender.recommend_mission_based(goal="learn", contribution_type="code")

        assert len(results) <= 3

        for project in results:
            assert "name" in project
            assert "description" in project
            assert "url" in project

    def test_recommend_mission_based_gsoc(self, recommender):
        """Test GSoC preparation recommendations"""
        results = recommender.recommend_mission_based(goal="gsoc", contribution_type="code")

        assert len(results) <= 3

        # Should recommend active projects suitable for GSoC
        if results:
            # ZAP, Juice Shop, Dependency Check are common GSoC projects
            names = [p["name"].lower() for p in results]
            has_gsoc_project = any(
                "zap" in name or "juice" in name or "dependency" in name for name in names
            )
            assert has_gsoc_project

    def test_empty_results_handling(self, recommender):
        """Test handling when no projects match criteria"""
        # Use obscure criteria that likely won't match
        results = recommender.recommend_tech_based(
            technology="unknown_tech", difficulty="advanced", project_type="unknown_type"
        )

        # Should return empty list or minimal results
        assert isinstance(results, list)

    def test_format_project_name(self, recommender):
        """Test project name formatting"""
        formatted = recommender._format_project_name("www-project-juice-shop")
        assert "OWASP" in formatted
        assert "Juice Shop" in formatted
        assert "www-project" not in formatted


class TestMessageFormatting:
    """Test recommendation message formatting"""

    def test_format_with_recommendations(self):
        """Test formatting with valid recommendations"""
        recommendations = [
            {
                "name": "OWASP Juice Shop",
                "description": "Modern insecure web application",
                "url": "https://github.com/OWASP/juice-shop",
            },
            {
                "name": "OWASP ZAP",
                "description": "Web application security scanner",
                "url": "https://github.com/OWASP/zap",
            },
        ]

        user_choices = {"technology": "python", "difficulty": "beginner"}

        msg = format_recommendations_message(recommendations, user_choices)

        assert "text" in msg
        assert "blocks" in msg
        assert len(msg["blocks"]) > 0

        # Check for project names in blocks
        blocks_text = json.dumps(msg["blocks"])
        assert "Juice Shop" in blocks_text
        assert "ZAP" in blocks_text

    def test_format_with_no_recommendations(self):
        """Test formatting when no projects match"""
        msg = format_recommendations_message([], {})

        assert "text" in msg
        assert "blocks" in msg

        # Should have fallback message
        blocks_text = json.dumps(msg["blocks"])
        assert "No matching projects" in blocks_text or "not found" in blocks_text.lower()

    def test_format_includes_action_buttons(self):
        """Test that formatted message includes action buttons"""
        recommendations = [
            {"name": "OWASP Juice Shop", "description": "Test", "url": "https://example.com"}
        ]

        msg = format_recommendations_message(recommendations, {})

        # Find action blocks
        action_blocks = [b for b in msg["blocks"] if b.get("type") == "actions"]
        assert len(action_blocks) > 0

        # Should have restart and/or done buttons
        all_actions = []
        for block in action_blocks:
            all_actions.extend([e["action_id"] for e in block.get("elements", [])])

        assert "restart_conversation" in all_actions or "end_conversation" in all_actions
