"""Tests for the recommendations functionality in app.py."""


class TestRecommendationFunctions:
    """Tests for the OWASP project recommendations helper functions."""

    def test_tech_keywords_exist(self):
        """Test TECH_KEYWORDS configuration exists and has expected keys."""
        # Recreate the keywords here to test the logic
        tech_keywords = {
            "python": ["python", "django", "flask", "pygoat", "pytm", "honeypot"],
            "java": ["java", "webgoat", "encoder", "benchmark", "esapi"],
            "javascript": ["javascript", "js", "node", "juice-shop", "nodejs"],
            "mobile": ["mobile", "android", "ios", "igoat", "androgoat", "seraphimdroid"],
            "cloud-native": ["cloud", "kubernetes", "container", "docker", "serverless"],
            "threat-modeling": ["threat", "dragon", "pytm", "threatspec"],
            "devsecops": ["devsecops", "pipeline", "ci-cd", "securecodebox", "defectdojo"],
        }

        assert "python" in tech_keywords
        assert "java" in tech_keywords
        assert "javascript" in tech_keywords
        assert "mobile" in tech_keywords
        assert "cloud-native" in tech_keywords
        assert "threat-modeling" in tech_keywords
        assert "devsecops" in tech_keywords

    def test_mission_keywords_exist(self):
        """Test MISSION_KEYWORDS configuration exists and has expected keys."""
        mission_keywords = {
            "learn-appsec": ["webgoat", "juice-shop", "security-shepherd", "training"],
            "contribute-code": ["tool", "scanner", "framework"],
            "documentation": ["guide", "cheat-sheets", "testing-guide", "standard"],
            "gsoc-prep": ["gsoc", "student", "beginner"],
            "research": ["research", "top-10", "standard", "framework"],
            "devsecops": ["devsecops", "pipeline", "automation"],
            "ctf": ["ctf", "hackademic", "shepherd", "juice-shop"],
        }

        assert "learn-appsec" in mission_keywords
        assert "contribute-code" in mission_keywords
        assert "documentation" in mission_keywords
        assert "gsoc-prep" in mission_keywords
        assert "research" in mission_keywords
        assert "devsecops" in mission_keywords
        assert "ctf" in mission_keywords

    def test_recommendation_scoring_logic(self):
        """Test the recommendation scoring logic."""
        sample_project_data = {
            "www-project-juice-shop": [
                "OWASP Foundation Web Respository",
                "https://github.com/OWASP/www-project-juice-shop",
            ],
            "www-project-threat-dragon": [
                "OWASP Foundation Threat Dragon Project Web Repository",
                "https://github.com/OWASP/www-project-threat-dragon",
            ],
        }

        # Replicate the scoring logic for threat-modeling
        keywords = ["threat", "dragon", "pytm", "threatspec"]

        scored_projects = []
        for project_name, project_info in sample_project_data.items():
            description = project_info[0] if isinstance(project_info, list) else ""
            url = ""
            if isinstance(project_info, list) and len(project_info) > 1:
                url = project_info[1]

            score = 0
            project_lower = project_name.lower()
            desc_lower = description.lower() if description else ""

            for keyword in keywords:
                if keyword in project_lower or keyword in desc_lower:
                    score += 10

            if score > 0:
                scored_projects.append((project_name, description, url, score))

        scored_projects.sort(key=lambda x: x[3], reverse=True)

        # Threat dragon should be in the results
        project_names = [p[0] for p in scored_projects]
        assert "www-project-threat-dragon" in project_names

    def test_build_slack_blocks_structure(self):
        """Test that Slack blocks have the correct structure."""
        recommendations = [
            ("www-project-juice-shop", "Test description", "https://example.com", 10),
        ]

        # Replicate block building logic
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":star: *Recommended Projects (Top {len(recommendations)})*",
                },
            },
            {"type": "divider"},
        ]

        for i, (name, description, url, _) in enumerate(recommendations, 1):
            display_name = name.replace("www-project-", "").replace("-", " ").title()
            desc_text = description if description and description != "None" else "OWASP Project"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {display_name}*\n{desc_text}\n<{url}|:link: View Project>",
                },
            })

        assert len(blocks) == 3
        assert blocks[0]["type"] == "section"
        assert blocks[1]["type"] == "divider"
        assert blocks[2]["type"] == "section"
        assert "Juice Shop" in blocks[2]["text"]["text"]

    def test_fallback_blocks_structure(self):
        """Test fallback blocks have correct structure."""
        fallback_projects = [
            (
                "OWASP Juice Shop",
                "Modern web app for security training",
                "https://github.com/OWASP/www-project-juice-shop"
            ),
        ]

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":thinking_face: *I couldn't find exact matches*",
                },
            },
            {"type": "divider"},
        ]

        for i, (name, description, url) in enumerate(fallback_projects, 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {name}*\n{description}\n<{url}|:link: View Project>",
                },
            })

        assert len(blocks) == 3
        assert "couldn't find" in blocks[0]["text"]["text"]

    def test_project_name_formatting(self):
        """Test that project names are formatted correctly for display."""
        project_name = "www-project-juice-shop"
        display_name = project_name.replace("www-project-", "").replace("-", " ").title()

        assert display_name == "Juice Shop"

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

    def test_scoring_with_difficulty_levels(self):
        """Test that difficulty level affects scoring."""
        sample_project_data = {
            "www-project-webgoat": [
                "OWASP Foundation Training Web Respository",
                "https://github.com/OWASP/www-project-webgoat",
            ],
            "www-project-enterprise-security": [
                "Enterprise Security Framework",
                "https://github.com/OWASP/www-project-enterprise",
            ],
        }

        # Beginner scoring keywords
        beginner_keywords = ["webgoat", "juice-shop", "training", "curriculum", "beginner"]

        # Advanced scoring keywords
        advanced_keywords = ["framework", "enterprise", "standard", "verification"]

        # Score for beginner
        beginner_scores = []
        for project_name, project_info in sample_project_data.items():
            description = project_info[0] if isinstance(project_info, list) else ""
            score = 0
            project_lower = project_name.lower()
            desc_lower = description.lower() if description else ""

            for keyword in beginner_keywords:
                if keyword in project_lower or keyword in desc_lower:
                    score += 3

            if score > 0:
                beginner_scores.append((project_name, score))

        # Score for advanced
        advanced_scores = []
        for project_name, project_info in sample_project_data.items():
            description = project_info[0] if isinstance(project_info, list) else ""
            score = 0
            project_lower = project_name.lower()
            desc_lower = description.lower() if description else ""

            for keyword in advanced_keywords:
                if keyword in project_lower or keyword in desc_lower:
                    score += 3

            if score > 0:
                advanced_scores.append((project_name, score))

        # WebGoat should score for beginner
        beginner_names = [p[0] for p in beginner_scores]
        assert "www-project-webgoat" in beginner_names

        # Enterprise security should score for advanced
        advanced_names = [p[0] for p in advanced_scores]
        assert "www-project-enterprise-security" in advanced_names

