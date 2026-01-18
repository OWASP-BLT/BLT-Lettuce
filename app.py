import logging
import os
import json
from pathlib import Path

import git
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from slack import WebClient
from slack_sdk.errors import SlackApiError
# Not using SlackEventAdapter - we handle events manually
# from slackeventsapi import SlackEventAdapter

from src.lettuce.conversation_manager import (
    ConversationManager,
    ConversationState,
    get_welcome_message,
    get_tech_stack_message,
    get_difficulty_message,
    get_project_type_message,
    get_mission_goal_message,
    get_contribution_type_message,
)
from src.lettuce.project_recommender import (
    ProjectRecommender,
    format_recommendations_message,
)

DEPLOYS_CHANNEL_NAME = "#project-blt-lettuce-deploys"
JOINS_CHANNEL_ID = "C06RMMRMGHE"
CONTRIBUTE_ID = "C04DH8HEPTR"

load_dotenv()

logging.basicConfig(
    filename="slack_messages.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)

# Initialize conversation manager and project recommender
conversation_manager = ConversationManager()
projects_data_path = os.path.join(os.path.dirname(__file__), "data", "projects.json")
project_recommender = ProjectRecommender(projects_data_path)

# Don't use SlackEventAdapter - we'll handle events manually
# This allows us to work without a valid signing secret during setup
client = WebClient(token=os.environ.get("SLACK_TOKEN", ""))

# Send startup message if credentials are valid
try:
    if os.environ.get("SLACK_TOKEN") and os.environ.get("SLACK_TOKEN") != "xoxb-123-123-abcdefg":
        client.chat_postMessage(channel=DEPLOYS_CHANNEL_NAME, text="bot started v1.9 240611-1 top")
except SlackApiError as e:
    logging.warning(f"Could not send startup message: {e.response['error']}")


@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    # Respond to Slack's URL verification challenge
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # Handle other event types here
    event = data.get("event", {})
    
    # Handle team join events
    if event.get("type") == "team_join":
        handle_team_join_event(event)
    
    # Handle message events
    elif event.get("type") == "message":
        handle_message_event(event)

    return jsonify({"status": "ok"}), 200


# keep for debugging purposes
# @app.before_request
# def log_request():
#    if request.path == '/slack/events' and request.method == 'POST':
#        # Log the request headers and body
#        logging.info(f"Headers: {request.headers}")
#        logging.info(f"Body: {request.get_data(as_text=True)}")


# Determine the root directory (assumes the script is run from the root folder)
root_dir = Path(__file__).resolve().parent


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


def handle_team_join_event(event):
    """Handle team_join event"""
    user_id = event["user"]["id"]

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


def handle_message_event(message):
    """Handle message event"""
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
        channel = message.get("channel")  # The DM channel ID
        text = message.get("text", "").lower()  # The text of the message
        try:
            if message.get("user") != bot_user_id:
                # Log to monitoring channel (optional)
                try:
                    client.chat_postMessage(channel=JOINS_CHANNEL_ID, text=f"<@{user}> said {text}")
                except:
                    pass  # Don't fail if monitoring channel doesn't exist
                
                # Handle conversational flow - pass the channel, not user_id
                handle_dm_conversation(channel, user, text)
        except SlackApiError as e:
            print(f"Error sending response: {e.response['error']}")


def handle_dm_conversation(channel_id: str, user_id: str, text: str):
    """Handle conversational DM with user following the flowchart"""
    conversation = conversation_manager.get_or_create_conversation(user_id)
    
    # Trigger words to start conversation
    start_keywords = ['help', 'start', 'project', 'recommend', 'find', 'looking']
    
    if conversation.state == ConversationState.INITIAL:
        # Start conversation if user uses trigger words
        if any(keyword in text for keyword in start_keywords):
            msg = get_welcome_message()
            client.chat_postMessage(channel=channel_id, **msg)
            conversation.update_state(ConversationState.PREFERENCE_CHOICE)
        else:
            # Default response for non-conversation messages
            client.chat_postMessage(
                channel=channel_id, 
                text=f"Hello! 👋 Say 'help' or 'find project' to get personalized OWASP project recommendations."
            )


@app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    """Handle interactive button clicks"""
    payload = json.loads(request.form["payload"])
    user_id = payload["user"]["id"]
    action = payload["actions"][0]
    action_id = action["action_id"]
    action_value = action["value"]
    
    conversation = conversation_manager.get_or_create_conversation(user_id)
    
    # Handle preference choice (Technology vs Mission)
    if action_id.startswith("preference_"):
        if action_value == "technology":
            conversation.update_state(ConversationState.TECH_STACK, "preference", "technology")
            msg = get_tech_stack_message()
            client.chat_postMessage(channel=user_id, **msg)
        elif action_value == "mission":
            conversation.update_state(ConversationState.MISSION_GOAL, "preference", "mission")
            msg = get_mission_goal_message()
            client.chat_postMessage(channel=user_id, **msg)
    
    # Handle technology stack choice
    elif action_id.startswith("tech_") and conversation.state == ConversationState.TECH_STACK:
        conversation.update_state(ConversationState.TECH_DIFFICULTY, "technology", action_value)
        msg = get_difficulty_message()
        client.chat_postMessage(channel=user_id, **msg)
    
    # Handle difficulty choice
    elif action_id.startswith("difficulty_"):
        conversation.update_state(ConversationState.TECH_PROJECT_TYPE, "difficulty", action_value)
        msg = get_project_type_message()
        client.chat_postMessage(channel=user_id, **msg)
    
    # Handle project type choice - generate tech recommendations
    elif action_id.startswith("type_"):
        conversation.data["project_type"] = action_value
        
        # Get recommendations
        recommendations = project_recommender.recommend_tech_based(
            technology=conversation.get_data("technology"),
            difficulty=conversation.get_data("difficulty"),
            project_type=action_value
        )
        
        msg = format_recommendations_message(recommendations, conversation.data)
        client.chat_postMessage(channel=user_id, **msg)
        conversation.update_state(ConversationState.COMPLETED)
    
    # Handle mission goal choice
    elif action_id.startswith("mission_") and conversation.state == ConversationState.MISSION_GOAL:
        conversation.update_state(ConversationState.MISSION_CONTRIBUTION, "goal", action_value)
        msg = get_contribution_type_message()
        client.chat_postMessage(channel=user_id, **msg)
    
    # Handle contribution type choice - generate mission recommendations
    elif action_id.startswith("contrib_"):
        conversation.data["contribution_type"] = action_value
        
        # Get recommendations
        recommendations = project_recommender.recommend_mission_based(
            goal=conversation.get_data("goal"),
            contribution_type=action_value
        )
        
        msg = format_recommendations_message(recommendations, conversation.data)
        client.chat_postMessage(channel=user_id, **msg)
        conversation.update_state(ConversationState.COMPLETED)
    
    # Handle restart
    elif action_id == "restart_conversation":
        conversation.reset()
        msg = get_welcome_message()
        client.chat_postMessage(channel=user_id, **msg)
        conversation.update_state(ConversationState.PREFERENCE_CHOICE)
    
    # Handle end conversation
    elif action_id == "end_conversation":
        client.chat_postMessage(
            channel=user_id,
            text="Thanks for using the OWASP project finder! Feel free to message me anytime. 👋"
        )
        conversation_manager.end_conversation(user_id)
    
    # Acknowledge the interaction
    return "", 200


if __name__ == "__main__":
    print("🤖 Starting OWASP Slack Bot...")
    print("📡 Server running on http://localhost:5000")
    print("🌐 Ngrok URL: https://preeligible-eleonor-guileful.ngrok-free.dev")
    app.run(debug=True, port=5000)
