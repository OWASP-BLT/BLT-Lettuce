"""Shared recommendation engine for OWASP project discovery.

This module contains keyword mappings and scoring functions used by both
app.py (Flask bot) and the slack-machine plugin to ensure consistent results.
"""

# Technology keywords for filtering
TECH_KEYWORDS = {
    "python": ["python", "django", "flask", "pygoat", "pytm", "honeypot"],
    "java": ["java", "webgoat", "encoder", "benchmark", "esapi"],
    "javascript": ["javascript", "js", "node", "juice-shop", "nodejs"],
    "mobile": ["mobile", "android", "ios", "igoat", "androgoat", "seraphimdroid"],
    "cloud-native": ["cloud", "kubernetes", "container", "docker", "serverless", "aws"],
    "threat-modeling": ["threat", "dragon", "pytm", "threatspec"],
    "devsecops": ["devsecops", "pipeline", "ci-cd", "securecodebox", "defectdojo"],
}

# Mission keywords for filtering
MISSION_KEYWORDS = {
    "learn-appsec": ["webgoat", "juice-shop", "security-shepherd", "training", "curriculum"],
    "contribute-code": ["tool", "scanner", "framework"],
    "documentation": ["guide", "cheat-sheets", "testing-guide", "standard"],
    "gsoc-prep": ["gsoc", "student", "beginner"],
    "research": ["research", "top-10", "standard", "framework"],
    "devsecops": ["devsecops", "pipeline", "automation"],
    "ctf": ["ctf", "hackademic", "shepherd", "juice-shop"],
}


def get_tech_recommendations(project_data, tech, difficulty, project_type):
    """Get project recommendations based on technology, difficulty, and type.

    Args:
        project_data: Dict mapping project names to [description, url] lists.
        tech: Selected technology (python, java, etc.)
        difficulty: Selected difficulty (beginner, intermediate, advanced)
        project_type: Selected project type (tools, code, docs, training)

    Returns:
        list: Up to 5 tuples of (project_name, description, url, score)
    """
    keywords = TECH_KEYWORDS.get(tech, [])
    type_keywords = {
        "tools": ["tool", "scanner", "checker", "detector"],
        "code": ["code", "app", "goat", "vulnerable"],
        "docs": ["guide", "standard", "cheat", "top-10", "documentation"],
        "training": ["training", "curriculum", "security-shepherd", "webgoat", "juice-shop"],
    }

    scored_projects = []

    for project_name, project_info in project_data.items():
        description = project_info[0] if isinstance(project_info, list) else ""
        url = ""
        if isinstance(project_info, list) and len(project_info) > 1:
            url = project_info[1]

        score = 0
        project_lower = project_name.lower()
        desc_lower = description.lower() if description else ""

        # Match technology keywords
        for keyword in keywords:
            if keyword in project_lower or keyword in desc_lower:
                score += 10

        # Match project type keywords
        for keyword in type_keywords.get(project_type, []):
            if keyword in project_lower or keyword in desc_lower:
                score += 5

        # Difficulty scoring
        if difficulty == "beginner":
            beginner_keywords = ["webgoat", "juice-shop", "training", "curriculum", "beginner"]
            for keyword in beginner_keywords:
                if keyword in project_lower or keyword in desc_lower:
                    score += 3
        elif difficulty == "advanced":
            advanced_keywords = ["framework", "enterprise", "standard", "verification"]
            for keyword in advanced_keywords:
                if keyword in project_lower or keyword in desc_lower:
                    score += 3

        if score > 0:
            scored_projects.append((project_name, description, url, score))

    scored_projects.sort(key=lambda x: x[3], reverse=True)
    return scored_projects[:5]


def get_mission_recommendations(project_data, mission, contribution):
    """Get project recommendations based on mission and contribution type.

    Args:
        project_data: Dict mapping project names to [description, url] lists.
        mission: Selected mission/goal
        contribution: Selected contribution type

    Returns:
        list: Up to 5 tuples of (project_name, description, url, score)
    """
    keywords = MISSION_KEYWORDS.get(mission, [])
    contrib_keywords = {
        "code": ["tool", "app", "scanner", "framework"],
        "documentation": ["guide", "standard", "cheat", "documentation"],
        "design": ["design", "ui", "frontend"],
        "research": ["research", "top-10", "standard", "framework"],
    }

    scored_projects = []

    for project_name, project_info in project_data.items():
        description = project_info[0] if isinstance(project_info, list) else ""
        url = ""
        if isinstance(project_info, list) and len(project_info) > 1:
            url = project_info[1]

        score = 0
        project_lower = project_name.lower()
        desc_lower = description.lower() if description else ""

        # Match mission keywords
        for keyword in keywords:
            if keyword in project_lower or keyword in desc_lower:
                score += 10

        # Match contribution type keywords
        for keyword in contrib_keywords.get(contribution, []):
            if keyword in project_lower or keyword in desc_lower:
                score += 5

        if score > 0:
            scored_projects.append((project_name, description, url, score))

    scored_projects.sort(key=lambda x: x[3], reverse=True)
    return scored_projects[:5]


def build_recommendations_blocks(recommendations, context_text):
    """Build Slack blocks for displaying recommendations.

    Args:
        recommendations: List of (name, description, url, score) tuples.
        context_text: Descriptive text shown in the header block.

    Returns:
        list: Slack Block Kit blocks ready for chat.postMessage.
    """
    if not recommendations:
        return build_fallback_blocks()

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":star: *Recommended Projects (Top {len(recommendations)})*\n"
                    f"{context_text}"
                ),
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

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ":rocket: *Want me to help you get started contributing?*",
        },
    })
    blocks.append({
        "type": "actions",
        "block_id": "final_actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Try Different Filters"},
                "value": "restart",
                "action_id": "rec_restart",
            },
        ],
    })

    return blocks


def build_fallback_blocks():
    """Build fallback blocks when no project matches are found.

    Returns:
        list: Slack Block Kit blocks showing popular OWASP projects.
    """
    fallback_projects = [
        (
            "OWASP Juice Shop",
            "Modern web app for security training",
            "https://github.com/OWASP/www-project-juice-shop",
        ),
        (
            "OWASP WebGoat",
            "Deliberately insecure application",
            "https://github.com/OWASP/www-project-webgoat",
        ),
        (
            "OWASP Cheat Sheets",
            "Security cheat sheets",
            "https://github.com/OWASP/www-project-cheat-sheets",
        ),
    ]

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":thinking_face: *I couldn't find exact matches, here are popular:*",
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

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "actions",
        "block_id": "fallback_actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Try Different Filters"},
                "value": "restart",
                "action_id": "rec_restart",
            },
        ],
    })

    return blocks
