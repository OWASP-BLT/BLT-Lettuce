"""Tests for the recommendations functionality using the shared recommendation engine."""

from lettuce.recommendation_engine import (
    MISSION_KEYWORDS,
    TECH_KEYWORDS,
    build_fallback_blocks,
    build_recommendations_blocks,
    get_mission_recommendations,
    get_tech_recommendations,
)


SAMPLE_PROJECT_DATA = {
    "www-project-juice-shop": [
        "OWASP Foundation Web Repository",
        "https://github.com/OWASP/www-project-juice-shop",
    ],
    "www-project-webgoat": [
        "OWASP Foundation Training Web Repository",
        "https://github.com/OWASP/www-project-webgoat",
    ],
    "www-project-pytm": [
        "OWASP Foundation Web Repository",
        "https://github.com/OWASP/www-project-pytm",
    ],
    "www-project-cheat-sheets": [
        "OWASP Foundation Web Repository",
        "https://github.com/OWASP/www-project-cheat-sheets",
    ],
    "www-project-threat-dragon": [
        "OWASP Foundation Threat Dragon Project Web Repository",
        "https://github.com/OWASP/www-project-threat-dragon",
    ],
}


class TestRecommendationFunctions:
    """Tests for the OWASP project recommendations helper functions."""

    def test_tech_keywords_exist(self):
        """Test TECH_KEYWORDS configuration has all expected technology keys."""
        assert "python" in TECH_KEYWORDS
        assert "java" in TECH_KEYWORDS
        assert "javascript" in TECH_KEYWORDS
        assert "mobile" in TECH_KEYWORDS
        assert "cloud-native" in TECH_KEYWORDS
        assert "threat-modeling" in TECH_KEYWORDS
        assert "devsecops" in TECH_KEYWORDS

        # All values should be non-empty lists of strings
        for tech, keywords in TECH_KEYWORDS.items():
            assert isinstance(keywords, list), f"{tech} keywords should be a list"
            assert len(keywords) > 0, f"{tech} keywords should not be empty"
            assert all(isinstance(k, str) for k in keywords)

    def test_mission_keywords_exist(self):
        """Test MISSION_KEYWORDS configuration has all expected mission keys."""
        assert "learn-appsec" in MISSION_KEYWORDS
        assert "contribute-code" in MISSION_KEYWORDS
        assert "documentation" in MISSION_KEYWORDS
        assert "gsoc-prep" in MISSION_KEYWORDS
        assert "research" in MISSION_KEYWORDS
        assert "devsecops" in MISSION_KEYWORDS
        assert "ctf" in MISSION_KEYWORDS

        # All values should be non-empty lists of strings
        for mission, keywords in MISSION_KEYWORDS.items():
            assert isinstance(keywords, list), f"{mission} keywords should be a list"
            assert len(keywords) > 0, f"{mission} keywords should not be empty"
            assert all(isinstance(k, str) for k in keywords)

    def test_get_tech_recommendations_returns_list(self):
        """Test that get_tech_recommendations returns a list of at most 5 items."""
        recommendations = get_tech_recommendations(SAMPLE_PROJECT_DATA, "python", "beginner", "training")
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5

    def test_get_tech_recommendations_scores_matches(self):
        """Test that threat-modeling recommendations include threat-dragon."""
        recommendations = get_tech_recommendations(
            SAMPLE_PROJECT_DATA, "threat-modeling", "beginner", "tools"
        )
        project_names = [r[0] for r in recommendations]
        assert any("threat" in name.lower() for name in project_names)

    def test_get_tech_recommendations_tuple_structure(self):
        """Test that each recommendation is a (name, description, url, score) tuple."""
        recommendations = get_tech_recommendations(
            SAMPLE_PROJECT_DATA, "threat-modeling", "beginner", "tools"
        )
        for rec in recommendations:
            assert len(rec) == 4
            assert isinstance(rec[0], str)  # project name
            assert isinstance(rec[1], str)  # description
            assert isinstance(rec[2], str)  # url
            assert isinstance(rec[3], int)  # score

    def test_get_mission_recommendations_returns_list(self):
        """Test that get_mission_recommendations returns a list of at most 5 items."""
        recommendations = get_mission_recommendations(SAMPLE_PROJECT_DATA, "learn-appsec", "code")
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5

    def test_get_mission_recommendations_scores_documentation(self):
        """Test that documentation mission returns cheat-sheets project."""
        recommendations = get_mission_recommendations(
            SAMPLE_PROJECT_DATA, "documentation", "documentation"
        )
        project_names = [r[0] for r in recommendations]
        assert any("cheat" in name.lower() for name in project_names)

    def test_build_recommendations_blocks_with_results(self):
        """Test that build_recommendations_blocks creates valid Slack blocks with results."""
        recommendations = [
            ("www-project-juice-shop", "Test description", "https://example.com", 10),
            ("www-project-webgoat", "Another desc", "https://example2.com", 5),
        ]

        blocks = build_recommendations_blocks(recommendations, "_Test context_")

        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # First block should be the header
        first_block = blocks[0]
        assert first_block["type"] == "section"
        assert "Recommended Projects" in first_block["text"]["text"]

    def test_build_recommendations_blocks_project_names(self):
        """Test that project names are formatted correctly for display."""
        recommendations = [
            ("www-project-juice-shop", "Test description", "https://example.com", 10),
        ]

        blocks = build_recommendations_blocks(recommendations, "_Test context_")

        project_block = None
        for block in blocks:
            if block.get("type") == "section" and "Juice Shop" in block.get("text", {}).get("text", ""):
                project_block = block
                break

        assert project_block is not None

    def test_build_recommendations_blocks_empty_returns_fallback(self):
        """Test that build_recommendations_blocks delegates to fallback when empty."""
        blocks = build_recommendations_blocks([], "_Test context_")

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        # Fallback should contain the "couldn't find" message
        text_found = any(
            "couldn't find" in block.get("text", {}).get("text", "")
            for block in blocks
            if block.get("type") == "section"
        )
        assert text_found

    def test_build_fallback_blocks(self):
        """Test that build_fallback_blocks creates valid fallback blocks."""
        blocks = build_fallback_blocks()

        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # Check for the thinking face message
        text_found = any(
            "couldn't find" in block.get("text", {}).get("text", "")
            for block in blocks
            if block.get("type") == "section"
        )
        assert text_found

        # Check that popular projects are listed
        all_text = " ".join(
            block.get("text", {}).get("text", "")
            for block in blocks
            if block.get("type") == "section"
        )
        assert "Juice Shop" in all_text or "WebGoat" in all_text

    def test_action_value_parsing(self):
        """Test that action values are parsed correctly."""
        # Technology path value
        tech_value = "python|beginner|tools"
        tech, difficulty, project_type = tech_value.split("|")
        assert tech == "python"
        assert difficulty == "beginner"
        assert project_type == "tools"

        # Mission path value
        mission_value = "learn-appsec|code"
        mission, contribution = mission_value.split("|")
        assert mission == "learn-appsec"
        assert contribution == "code"

    def test_button_block_structure(self):
        """Test that button blocks have the correct structure."""
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": "Technology-Based"},
            "value": "technology",
            "action_id": "rec_path_technology",
            "style": "primary",
        }

        assert button["type"] == "button"
        assert button["text"]["type"] == "plain_text"
        assert button["value"] == "technology"
        assert button["action_id"] == "rec_path_technology"
        assert button["style"] == "primary"

    def test_scoring_beginner_project_ranked_higher(self):
        """Test that beginner difficulty boosts webgoat over non-training projects."""
        recommendations = get_tech_recommendations(
            SAMPLE_PROJECT_DATA, "java", "beginner", "training"
        )
        # webgoat is a Java training project - should be in results
        project_names = [r[0] for r in recommendations]
        assert "www-project-webgoat" in project_names

    def test_project_name_formatting(self):
        """Test that project names are formatted correctly for display."""
        project_name = "www-project-juice-shop"
        display_name = project_name.replace("www-project-", "").replace("-", " ").title()
        assert display_name == "Juice Shop"


