import json
import logging
import os
from pathlib import Path

import git
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from slack import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

DEPLOYS_CHANNEL_NAME = "#project-blt-lettuce-deploys"
JOINS_CHANNEL_ID = "C06RMMRMGHE"
CONTRIBUTE_ID = "C04DH8HEPTR"

load_dotenv()

# Load project data for recommendations
root_dir = Path(__file__).resolve().parent
try:
    with open(root_dir / "data" / "projects.json") as f:
        PROJECT_DATA = json.load(f)
except FileNotFoundError:
    PROJECT_DATA = {}

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

logging.basicConfig(
    filename="slack_messages.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(os.environ["SIGNING_SECRET"], "/slack/events", app)
client = WebClient(token=os.environ["SLACK_TOKEN"])
client.chat_postMessage(channel=DEPLOYS_CHANNEL_NAME, text="bot started v2.0 with recommendations")


def get_tech_recommendations(tech, difficulty, project_type):
    """Get project recommendations based on technology, difficulty, and type."""
    keywords = TECH_KEYWORDS.get(tech, [])
    type_keywords = {
        "tools": ["tool", "scanner", "checker", "detector"],
        "code": ["code", "app", "goat", "vulnerable"],
        "docs": ["guide", "standard", "cheat", "top-10", "documentation"],
        "training": ["training", "curriculum", "security-shepherd", "webgoat", "juice-shop"],
    }

    scored_projects = []

    for project_name, project_info in PROJECT_DATA.items():
        description = project_info[0] if isinstance(project_info, list) else ""
        url = project_info[1] if isinstance(project_info, list) and len(project_info) > 1 else ""

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


def get_mission_recommendations(mission, contribution):
    """Get project recommendations based on mission and contribution type."""
    keywords = MISSION_KEYWORDS.get(mission, [])
    contrib_keywords = {
        "code": ["tool", "app", "scanner", "framework"],
        "documentation": ["guide", "standard", "cheat", "documentation"],
        "design": ["design", "ui", "frontend"],
        "research": ["research", "top-10", "standard", "framework"],
    }

    scored_projects = []

    for project_name, project_info in PROJECT_DATA.items():
        description = project_info[0] if isinstance(project_info, list) else ""
        url = project_info[1] if isinstance(project_info, list) and len(project_info) > 1 else ""

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
    """Build Slack blocks for displaying recommendations."""
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
    """Build fallback blocks when no matches are found."""
    fallback_projects = [
        ("OWASP Juice Shop", "Modern web app for security training",
         "https://github.com/OWASP/www-project-juice-shop"),
        ("OWASP WebGoat", "Deliberately insecure application",
         "https://github.com/OWASP/www-project-webgoat"),
        ("OWASP Cheat Sheets", "Security cheat sheets",
         "https://github.com/OWASP/www-project-cheat-sheets"),
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


@app.route("/slack/interactivity", methods=["POST"])
def handle_interactivity():
    """Handle interactive button clicks from Slack."""
    payload = json.loads(request.form.get("payload", "{}"))
    action_id = payload.get("actions", [{}])[0].get("action_id", "")
    action_value = payload.get("actions", [{}])[0].get("value", "")
    channel_id = payload.get("channel", {}).get("id", "")

    try:
        # Initial path selection
        if action_id == "rec_path_technology":
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Step 1/3: Which technology/stack are you interested in?*",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "tech_select",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Python"},
                            "value": "python",
                            "action_id": "rec_tech_python",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Java"},
                            "value": "java",
                            "action_id": "rec_tech_java",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "JavaScript"},
                            "value": "javascript",
                            "action_id": "rec_tech_javascript",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Mobile"},
                            "value": "mobile",
                            "action_id": "rec_tech_mobile",
                        },
                    ],
                },
                {
                    "type": "actions",
                    "block_id": "tech_select_2",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Cloud Native"},
                            "value": "cloud-native",
                            "action_id": "rec_tech_cloud-native",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Threat Modeling"},
                            "value": "threat-modeling",
                            "action_id": "rec_tech_threat-modeling",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "DevSecOps"},
                            "value": "devsecops",
                            "action_id": "rec_tech_devsecops",
                        },
                    ],
                },
            ]
            client.chat_postMessage(
                channel=channel_id,
                text="Step 1/3: Which technology/stack are you interested in?",
                blocks=blocks,
            )

        elif action_id == "rec_path_mission":
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Step 1/2: What is your goal?*",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "mission_select",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Learn AppSec"},
                            "value": "learn-appsec",
                            "action_id": "rec_mission_learn-appsec",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Contribute Code"},
                            "value": "contribute-code",
                            "action_id": "rec_mission_contribute-code",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Documentation"},
                            "value": "documentation",
                            "action_id": "rec_mission_documentation",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "GSoC Prep"},
                            "value": "gsoc-prep",
                            "action_id": "rec_mission_gsoc-prep",
                        },
                    ],
                },
                {
                    "type": "actions",
                    "block_id": "mission_select_2",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Research"},
                            "value": "research",
                            "action_id": "rec_mission_research",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "DevSecOps"},
                            "value": "devsecops",
                            "action_id": "rec_mission_devsecops",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "CTF"},
                            "value": "ctf",
                            "action_id": "rec_mission_ctf",
                        },
                    ],
                },
            ]
            client.chat_postMessage(
                channel=channel_id,
                text="Step 1/2: What is your goal?",
                blocks=blocks,
            )

        # Technology selection -> Difficulty
        elif action_id.startswith("rec_tech_"):
            tech = action_value
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Step 2/3: What is your experience level?*\n"
                            f"_Selected: {tech.title()}_"
                        ),
                    },
                },
                {
                    "type": "actions",
                    "block_id": "difficulty_select",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Beginner"},
                            "value": f"{tech}|beginner",
                            "action_id": "rec_diff_beginner",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Intermediate"},
                            "value": f"{tech}|intermediate",
                            "action_id": "rec_diff_intermediate",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Advanced"},
                            "value": f"{tech}|advanced",
                            "action_id": "rec_diff_advanced",
                        },
                    ],
                },
            ]
            client.chat_postMessage(
                channel=channel_id,
                text=f"Step 2/3: What is your experience level? Selected: {tech.title()}",
                blocks=blocks,
            )

        # Difficulty selection -> Project type
        elif action_id.startswith("rec_diff_"):
            tech, difficulty = action_value.split("|")
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Step 3/3: What type of project are you looking for?*\n"
                            f"_Selected: {tech.title()} | {difficulty.title()}_"
                        ),
                    },
                },
                {
                    "type": "actions",
                    "block_id": "project_type_select",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Tools"},
                            "value": f"{tech}|{difficulty}|tools",
                            "action_id": "rec_type_tools",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Code Repos"},
                            "value": f"{tech}|{difficulty}|code",
                            "action_id": "rec_type_code",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Documentation"},
                            "value": f"{tech}|{difficulty}|docs",
                            "action_id": "rec_type_docs",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Training"},
                            "value": f"{tech}|{difficulty}|training",
                            "action_id": "rec_type_training",
                        },
                    ],
                },
            ]
            client.chat_postMessage(
                channel=channel_id,
                text=(
                    f"Step 3/3: What type of project? "
                    f"Selected: {tech.title()} | {difficulty.title()}"
                ),
                blocks=blocks,
            )

        # Project type selection -> Show recommendations
        elif action_id.startswith("rec_type_"):
            tech, difficulty, project_type = action_value.split("|")
            recommendations = get_tech_recommendations(tech, difficulty, project_type)
            context = f"_Based on: {tech.title()} | {difficulty.title()} | {project_type.title()}_"
            blocks = build_recommendations_blocks(recommendations, context)
            client.chat_postMessage(
                channel=channel_id,
                text=f"Here are your recommended OWASP projects for {tech}!",
                blocks=blocks,
            )

        # Mission selection -> Contribution type
        elif action_id.startswith("rec_mission_"):
            mission = action_value
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Step 2/2: How would you like to contribute?*\n"
                            f"_Selected goal: {mission.replace('-', ' ').title()}_"
                        ),
                    },
                },
                {
                    "type": "actions",
                    "block_id": "contribution_select",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Code"},
                            "value": f"{mission}|code",
                            "action_id": "rec_contrib_code",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Documentation"},
                            "value": f"{mission}|documentation",
                            "action_id": "rec_contrib_documentation",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Design"},
                            "value": f"{mission}|design",
                            "action_id": "rec_contrib_design",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Research"},
                            "value": f"{mission}|research",
                            "action_id": "rec_contrib_research",
                        },
                    ],
                },
            ]
            client.chat_postMessage(
                channel=channel_id,
                text=(
                    "Step 2/2: How would you like to contribute? "
                    f"Selected: {mission.replace('-', ' ').title()}"
                ),
                blocks=blocks,
            )

        # Contribution type selection -> Show recommendations
        elif action_id.startswith("rec_contrib_"):
            mission, contribution = action_value.split("|")
            recommendations = get_mission_recommendations(mission, contribution)
            context = (
                f"_Based on: {mission.replace('-', ' ').title()} | {contribution.title()}_"
            )
            blocks = build_recommendations_blocks(recommendations, context)
            client.chat_postMessage(
                channel=channel_id,
                text=f"Here are your recommended OWASP projects for {mission.replace('-', ' ')}!",
                blocks=blocks,
            )

        # Restart flow
        elif action_id == "rec_restart":
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            ":wave: *Let's find you another OWASP project!*\n\n"
                            "Would you like recommendations based on *Technology* or *Mission*?"
                        ),
                    },
                },
                {
                    "type": "actions",
                    "block_id": "recommendation_restart",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Technology-Based"},
                            "value": "technology",
                            "action_id": "rec_path_technology",
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Mission-Based"},
                            "value": "mission",
                            "action_id": "rec_path_mission",
                            "style": "primary",
                        },
                    ],
                },
            ]
            client.chat_postMessage(
                channel=channel_id,
                text="Let's find you another OWASP project!",
                blocks=blocks,
            )

    except SlackApiError as e:
        logging.error(f"Error handling interactivity: {e.response['error']}")

    return "", 200


@app.route("/slack/commands", methods=["POST"])
def handle_slash_commands():
    """Handle slash commands from Slack."""
    command = request.form.get("command", "")
    channel_id = request.form.get("channel_id", "")

    if command == "/recommend":
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":wave: *Hi! I can help you find OWASP projects.*\n\n"
                        "Would you like recommendations based on *Technology* or *Mission*?"
                    ),
                },
            },
            {
                "type": "actions",
                "block_id": "recommendation_start",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Technology-Based"},
                        "value": "technology",
                        "action_id": "rec_path_technology",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Mission-Based"},
                        "value": "mission",
                        "action_id": "rec_path_mission",
                        "style": "primary",
                    },
                ],
            },
        ]

        try:
            client.chat_postMessage(
                channel=channel_id,
                text="Hi! I can help you find OWASP projects. Choose Technology or Mission based.",
                blocks=blocks,
            )
        except SlackApiError as e:
            logging.error(f"Error sending recommendation message: {e.response['error']}")

        return "", 200

    return "", 200


@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    # Respond to Slack's URL verification challenge
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # Handle other event types here
    event = data.get("event", {})
    handle_message(event)

    return "Event received", 200


# keep for debugging purposes
# @app.before_request
# def log_request():
#    if request.path == '/slack/events' and request.method == 'POST':
#        # Log the request headers and body
#        logging.info(f"Headers: {request.headers}")
#        logging.info(f"Body: {request.get_data(as_text=True)}")


@app.route("/update_server", methods=["POST"])
def webhook():
    if request.method == "POST":
        current_directory = os.path.dirname(os.path.abspath(__file__))
        repo = git.Repo(current_directory)
        origin = repo.remotes.origin
        origin.pull()
        latest_commit_message = repo.head.commit.message.strip()
        client.chat_postMessage(
            channel=DEPLOYS_CHANNEL_NAME,
            text=f"Deployed the latest version 1.8. Latest commit: {latest_commit_message}",
        )
        return "OK", 200

    return "Error", 400


@slack_events_adapter.on("team_join")
def handle_team_join(event_data):
    user_id = event_data["event"]["user"]["id"]

    # Post a message in the private joins channel
    response = client.chat_postMessage(
        channel=JOINS_CHANNEL_ID, text=f"<@{user_id}> joined the team."
    )

    if not response["ok"]:
        client.chat_postMessage(
            channel=DEPLOYS_CHANNEL_NAME,
            text=f"Error sending message: {response['error']}",
        )
        logging.error(f"Error sending message: {response['error']}")

    try:
        response = client.conversations_open(users=[user_id])
        dm_channel_id = response["channel"]["id"]

        with open("welcome_message.txt", "r", encoding="utf-8") as file:
            welcome_message_template = file.read()

        welcome_message = welcome_message_template.format(user_id=user_id)
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_message.strip()}}]

        client.chat_postMessage(
            channel=dm_channel_id, text="Welcome to the OWASP Slack Community!", blocks=blocks
        )
    except Exception as e:
        logging.error(f"Error sending welcome message: {e}")


@slack_events_adapter.on("message")
def handle_message(payload):
    message = payload.get("event", {})
    try:
        response = client.auth_test()
        bot_user_id = response["user_id"]
    except SlackApiError:
        bot_user_id = None
    # Check if the message was not sent by the bot itself
    if message.get("user") != bot_user_id:
        if (
            message.get("subtype") is None
            and not any(keyword in message.get("text", "").lower() for keyword in ["#contribute"])
            and any(
                keyword in message.get("text", "").lower()
                for keyword in ("contribute", "contributing", "contributes")
            )
        ):
            user = message.get("user")
            channel = message.get("channel")
            logging.info(f"detected contribute sending to channel: {channel}")
            response = client.chat_postMessage(
                channel=channel,
                text=(
                    f"Hello <@{user}>! Please check this channel "
                    f"<#{CONTRIBUTE_ID}> for contributing guidelines today!"
                ),
            )
            if not response["ok"]:
                client.chat_postMessage(
                    channel=DEPLOYS_CHANNEL_NAME,
                    text=f"Error sending message: {response['error']}",
                )
                logging.error(f"Error sending message: {response['error']}")
    if message.get("channel_type") == "im":
        user = message["user"]  # The user ID of the person who sent the message
        text = message.get("text", "")  # The text of the message
        try:
            if message.get("user") != bot_user_id:
                client.chat_postMessage(channel=JOINS_CHANNEL_ID, text=f"<@{user}> said {text}")
            # Respond to the direct message
            client.chat_postMessage(channel=user, text=f"Hello <@{user}>, you said: {text}")
        except SlackApiError as e:
            print(f"Error sending response: {e.response['error']}")
