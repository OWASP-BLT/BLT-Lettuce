"""OWASP Project Recommendation Plugin.

This plugin implements the flowchart logic from docs/slack-bot-flowchart.md
to guide users through Technology-based or Mission-based project discovery.
"""

import json
import logging
import os
import re

from machine.clients.slack import SlackClient
from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import action, command
from machine.storage import PluginStorage
from machine.utils.collections import CaseInsensitiveDict

from lettuce.recommendation_engine import (
    build_recommendations_blocks,
    get_mission_recommendations as _get_mission_recommendations,
    get_tech_recommendations as _get_tech_recommendations,
)


class RecommendationsPlugin(MachineBasePlugin):
    """Plugin for OWASP project recommendations using interactive buttons."""

    def __init__(self, client: SlackClient, settings: CaseInsensitiveDict, storage: PluginStorage):
        """Initialize the recommendations plugin."""
        super().__init__(client, settings, storage)

        # Load project data - use environment variable or default to current directory
        project_home = os.environ.get("PROJECT_HOME", os.getcwd())
        data_path = os.path.join(project_home, "data", "projects.json")
        try:
            with open(data_path) as f:
                self.project_data = json.load(f)
        except FileNotFoundError:
            self.project_data = {}

    @command("/recommend")
    async def recommend(self, command):
        """Start the project recommendation flow with clickable buttons."""
        channel_id = command._cmd_payload["channel_id"]

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
                        "text": {"type": "plain_text", "text": ":computer: Technology-Based"},
                        "value": "technology",
                        "action_id": "rec_path_technology",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":dart: Mission-Based"},
                        "value": "mission",
                        "action_id": "rec_path_mission",
                        "style": "primary",
                    },
                ],
            },
        ]

        await self.web_client.chat_postMessage(
            channel=channel_id,
            text="Hi! I can help you find OWASP projects. Choose Technology or Mission based.",
            blocks=blocks,
        )

    # ==========================================
    # Technology-Based Path
    # ==========================================

    @action(action_id="rec_path_technology", block_id=None)
    async def handle_technology_path(self, action):
        """Handle Technology-Based path selection - Step 1: Ask technology."""
        channel_id = action.payload.channel.id

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
                        "text": {"type": "plain_text", "text": ":snake: Python"},
                        "value": "python",
                        "action_id": "rec_tech_python",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":coffee: Java"},
                        "value": "java",
                        "action_id": "rec_tech_java",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":javascript: JavaScript"},
                        "value": "javascript",
                        "action_id": "rec_tech_javascript",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":iphone: Mobile"},
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
                        "text": {"type": "plain_text", "text": ":cloud: Cloud Native"},
                        "value": "cloud-native",
                        "action_id": "rec_tech_cloud-native",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":shield: Threat Modeling"},
                        "value": "threat-modeling",
                        "action_id": "rec_tech_threat-modeling",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":gear: DevSecOps"},
                        "value": "devsecops",
                        "action_id": "rec_tech_devsecops",
                    },
                ],
            },
        ]

        await self.web_client.chat_postMessage(
            channel=channel_id,
            text="Step 1/3: Which technology/stack are you interested in?",
            blocks=blocks,
        )

    @action(action_id=re.compile(r"rec_tech_.*"), block_id=None)
    async def handle_tech_selection(self, action):
        """Handle technology selection - Step 2: Ask difficulty level."""
        channel_id = action.payload.channel.id
        tech = action.payload.actions[0].value

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
                        "text": {"type": "plain_text", "text": ":seedling: Beginner"},
                        "value": f"{tech}|beginner",
                        "action_id": "rec_diff_beginner",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":herb: Intermediate"},
                        "value": f"{tech}|intermediate",
                        "action_id": "rec_diff_intermediate",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":evergreen_tree: Advanced"},
                        "value": f"{tech}|advanced",
                        "action_id": "rec_diff_advanced",
                    },
                ],
            },
        ]

        await self.web_client.chat_postMessage(
            channel=channel_id,
            text=f"Step 2/3: What is your experience level? Selected: {tech.title()}",
            blocks=blocks,
        )

    @action(action_id=re.compile(r"rec_diff_.*"), block_id=None)
    async def handle_difficulty_selection(self, action):
        """Handle difficulty selection - Step 3: Ask project type."""
        channel_id = action.payload.channel.id
        value = action.payload.actions[0].value
        try:
            tech, difficulty = value.split("|")
        except ValueError:
            logging.warning("Invalid action_value for rec_diff_: %r", value)
            return

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
                        "text": {"type": "plain_text", "text": ":hammer_and_wrench: Tools"},
                        "value": f"{tech}|{difficulty}|tools",
                        "action_id": "rec_type_tools",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":file_folder: Code Repos"},
                        "value": f"{tech}|{difficulty}|code",
                        "action_id": "rec_type_code",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":books: Documentation"},
                        "value": f"{tech}|{difficulty}|docs",
                        "action_id": "rec_type_docs",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":mortar_board: Training"},
                        "value": f"{tech}|{difficulty}|training",
                        "action_id": "rec_type_training",
                    },
                ],
            },
        ]

        await self.web_client.chat_postMessage(
            channel=channel_id,
            text=(
                f"Step 3/3: What type of project? "
                f"Selected: {tech.title()} | {difficulty.title()}"
            ),
            blocks=blocks,
        )

    @action(action_id=re.compile(r"rec_type_.*"), block_id=None)
    async def handle_project_type_selection(self, action):
        """Handle project type selection - Show technology-based recommendations."""
        channel_id = action.payload.channel.id
        value = action.payload.actions[0].value
        try:
            tech, difficulty, project_type = value.split("|")
        except ValueError:
            logging.warning("Invalid action_value for rec_type_: %r", value)
            return

        # Get recommendations and send using shared engine
        recommendations = _get_tech_recommendations(self.project_data, tech, difficulty, project_type)
        context_text = (
            f"_Based on: {tech.title()} | {difficulty.title()} | {project_type.title()}_"
        )
        blocks = build_recommendations_blocks(recommendations, context_text)
        await self.web_client.chat_postMessage(
            channel=channel_id,
            text=f"Here are your recommended OWASP projects for {tech}!",
            blocks=blocks,
        )

    # ==========================================
    # Mission-Based Path
    # ==========================================

    @action(action_id="rec_path_mission", block_id=None)
    async def handle_mission_path(self, action):
        """Handle Mission-Based path selection - Step 1: Ask goal."""
        channel_id = action.payload.channel.id

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
                        "text": {"type": "plain_text", "text": ":books: Learn AppSec"},
                        "value": "learn-appsec",
                        "action_id": "rec_mission_learn-appsec",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":keyboard: Contribute Code"},
                        "value": "contribute-code",
                        "action_id": "rec_mission_contribute-code",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":memo: Documentation"},
                        "value": "documentation",
                        "action_id": "rec_mission_documentation",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":sunny: GSoC Prep"},
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
                        "text": {"type": "plain_text", "text": ":microscope: Research"},
                        "value": "research",
                        "action_id": "rec_mission_research",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":gear: DevSecOps"},
                        "value": "devsecops",
                        "action_id": "rec_mission_devsecops",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":triangular_flag_on_post: CTF"},
                        "value": "ctf",
                        "action_id": "rec_mission_ctf",
                    },
                ],
            },
        ]

        await self.web_client.chat_postMessage(
            channel=channel_id,
            text="Step 1/2: What is your goal?",
            blocks=blocks,
        )

    @action(action_id=re.compile(r"rec_mission_.*"), block_id=None)
    async def handle_mission_selection(self, action):
        """Handle mission selection - Step 2: Ask contribution type."""
        channel_id = action.payload.channel.id
        mission = action.payload.actions[0].value

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
                        "text": {"type": "plain_text", "text": ":computer: Code"},
                        "value": f"{mission}|code",
                        "action_id": "rec_contrib_code",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":pencil: Documentation"},
                        "value": f"{mission}|documentation",
                        "action_id": "rec_contrib_documentation",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":art: Design"},
                        "value": f"{mission}|design",
                        "action_id": "rec_contrib_design",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":mag: Research"},
                        "value": f"{mission}|research",
                        "action_id": "rec_contrib_research",
                    },
                ],
            },
        ]

        await self.web_client.chat_postMessage(
            channel=channel_id,
            text=(
                "Step 2/2: How would you like to contribute? "
                f"Selected: {mission.replace('-', ' ').title()}"
            ),
            blocks=blocks,
        )

    @action(action_id=re.compile(r"rec_contrib_.*"), block_id=None)
    async def handle_contribution_selection(self, action):
        """Handle contribution type selection - Show mission-based recommendations."""
        channel_id = action.payload.channel.id
        value = action.payload.actions[0].value
        try:
            mission, contribution = value.split("|")
        except ValueError:
            logging.warning("Invalid action_value for rec_contrib_: %r", value)
            return

        # Get recommendations based on selections
        recommendations = _get_mission_recommendations(self.project_data, mission, contribution)
        context_text = (
            f"_Based on: {mission.replace('-', ' ').title()} | {contribution.title()}_"
        )
        blocks = build_recommendations_blocks(recommendations, context_text)
        await self.web_client.chat_postMessage(
            channel=channel_id,
            text=f"Here are your recommended OWASP projects for {mission}!",
            blocks=blocks,
        )

    # ==========================================
    # Recommendation Logic (delegated to shared engine)
    # ==========================================

    @action(action_id="rec_restart", block_id=None)
    async def handle_restart(self, action):
        """Handle restart button to start the recommendation flow again."""
        channel_id = action.payload.channel.id

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
                        "text": {"type": "plain_text", "text": ":computer: Technology-Based"},
                        "value": "technology",
                        "action_id": "rec_path_technology",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":dart: Mission-Based"},
                        "value": "mission",
                        "action_id": "rec_path_mission",
                        "style": "primary",
                    },
                ],
            },
        ]

        await self.web_client.chat_postMessage(
            channel=channel_id,
            text="Let's find you another OWASP project! Choose Technology or Mission based.",
            blocks=blocks,
        )
