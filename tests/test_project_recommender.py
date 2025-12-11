"""Tests for project recommendation engine."""

import json
from pathlib import Path

import pytest

# Import the recommender
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "cloudflare-worker"))
from project_recommender import ProjectRecommender


@pytest.fixture
def sample_projects_data():
    """Sample projects data for testing."""
    return {
        "total_projects": 5,
        "technologies": ["python", "java", "javascript", "cloud"],
        "missions": ["learning", "tool", "documentation", "vulnerable-app"],
        "levels": ["beginner", "intermediate", "advanced"],
        "types": ["tool", "documentation", "training", "vulnerable-app"],
        "projects": [
            {
                "id": "www-project-juice-shop",
                "name": "Juice Shop",
                "description": "OWASP Juice Shop is an insecure web application for training",
                "url": "https://github.com/OWASP/www-project-juice-shop",
                "technologies": ["javascript", "web"],
                "missions": ["learning", "vulnerable-app"],
                "level": "beginner",
                "type": "vulnerable-app",
                "tags": ["javascript", "web", "learning", "vulnerable-app"],
            },
            {
                "id": "www-project-zap",
                "name": "ZAP",
                "description": "OWASP Zed Attack Proxy security testing tool",
                "url": "https://github.com/OWASP/www-project-zap",
                "technologies": ["java"],
                "missions": ["tool", "testing"],
                "level": "intermediate",
                "type": "tool",
                "tags": ["java", "tool", "testing"],
            },
            {
                "id": "www-project-pygoat",
                "name": "PyGoat",
                "description": "Python vulnerable web application for learning",
                "url": "https://github.com/OWASP/www-project-pygoat",
                "technologies": ["python"],
                "missions": ["learning", "vulnerable-app"],
                "level": "beginner",
                "type": "vulnerable-app",
                "tags": ["python", "learning", "vulnerable-app"],
            },
            {
                "id": "www-project-cheat-sheets",
                "name": "Cheat Sheets",
                "description": "OWASP Cheat Sheet Series documentation",
                "url": "https://github.com/OWASP/www-project-cheat-sheets",
                "technologies": [],
                "missions": ["documentation", "learning"],
                "level": "beginner",
                "type": "documentation",
                "tags": ["documentation", "learning"],
            },
            {
                "id": "www-project-kubernetes-top-ten",
                "name": "Kubernetes Top Ten",
                "description": "Top 10 security risks for Kubernetes",
                "url": "https://github.com/OWASP/www-project-kubernetes-top-ten",
                "technologies": ["cloud"],
                "missions": ["standard", "documentation"],
                "level": "advanced",
                "type": "standard",
                "tags": ["cloud", "standard", "documentation"],
            },
        ],
    }


@pytest.fixture
def recommender(sample_projects_data):
    """Create a ProjectRecommender instance."""
    return ProjectRecommender(sample_projects_data)


class TestProjectRecommender:
    """Test the ProjectRecommender class."""

    def test_filter_by_technology(self, recommender):
        """Test filtering projects by technology."""
        python_projects = recommender.filter_by_technology("python")
        assert len(python_projects) == 1
        assert python_projects[0]["id"] == "www-project-pygoat"

        java_projects = recommender.filter_by_technology("java")
        assert len(java_projects) == 1
        assert java_projects[0]["id"] == "www-project-zap"

    def test_filter_by_mission(self, recommender):
        """Test filtering projects by mission."""
        learning_projects = recommender.filter_by_mission("learning")
        assert len(learning_projects) >= 3

        tool_projects = recommender.filter_by_mission("tool")
        assert len(tool_projects) >= 1

    def test_filter_by_level(self, recommender):
        """Test filtering projects by difficulty level."""
        beginner_projects = recommender.filter_by_level("beginner")
        assert len(beginner_projects) == 3

        advanced_projects = recommender.filter_by_level("advanced")
        assert len(advanced_projects) == 1

    def test_filter_by_type(self, recommender):
        """Test filtering projects by type."""
        vulnerable_apps = recommender.filter_by_type("vulnerable-app")
        assert len(vulnerable_apps) == 2

        documentation = recommender.filter_by_type("documentation")
        assert len(documentation) == 1

    def test_search_by_keyword(self, recommender):
        """Test searching projects by keyword."""
        results = recommender.search_by_keyword("shop")
        assert len(results) == 1
        assert results[0]["id"] == "www-project-juice-shop"

        results = recommender.search_by_keyword("security")
        assert len(results) >= 1

    def test_recommend_by_technology(self, recommender):
        """Test technology-based recommendations."""
        recommendations = recommender.recommend_by_technology("python", top_n=3)
        assert len(recommendations) >= 1
        assert recommendations[0]["id"] == "www-project-pygoat"

    def test_recommend_by_technology_with_level(self, recommender):
        """Test technology-based recommendations with level filter."""
        recommendations = recommender.recommend_by_technology(
            "javascript", level="beginner", top_n=3
        )
        assert len(recommendations) >= 1
        assert all(proj["level"] == "beginner" for proj in recommendations)

    def test_recommend_by_mission(self, recommender):
        """Test mission-based recommendations."""
        recommendations = recommender.recommend_by_mission("learning", top_n=3)
        assert len(recommendations) >= 3
        # Should include learning projects

    def test_get_fallback_recommendations(self, recommender):
        """Test fallback recommendations."""
        recommendations = recommender.get_fallback_recommendations(top_n=3)
        assert len(recommendations) >= 1
        # Should prioritize beginner and learning projects

    def test_format_recommendation(self, recommender, sample_projects_data):
        """Test formatting a recommendation."""
        project = sample_projects_data["projects"][0]
        formatted = recommender.format_recommendation(project)

        assert "Juice Shop" in formatted
        assert "javascript" in formatted
        assert "Beginner" in formatted
        assert "github.com" in formatted

    def test_rank_projects(self, recommender, sample_projects_data):
        """Test project ranking logic."""
        projects = sample_projects_data["projects"]
        preferences = {"technology": "python", "level": "beginner"}

        ranked = recommender.rank_projects(projects, preferences)

        # PyGoat should rank high due to matching preferences
        assert ranked[0]["id"] == "www-project-pygoat"

    def test_empty_results(self, recommender):
        """Test handling of empty results."""
        results = recommender.filter_by_technology("nonexistent")
        assert len(results) == 0

        recommendations = recommender.recommend_by_technology("nonexistent", top_n=3)
        assert len(recommendations) == 0


def test_load_projects_metadata():
    """Test loading actual projects metadata."""
    from project_recommender import load_projects_metadata

    # This will load the actual file if it exists
    metadata = load_projects_metadata()

    assert isinstance(metadata, dict)
    assert "projects" in metadata

    # If the file exists, check structure
    if metadata["projects"]:
        assert "technologies" in metadata
        assert "missions" in metadata
        assert "levels" in metadata
