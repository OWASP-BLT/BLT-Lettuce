import os
from unittest import mock

import pytest

from app import create_slack_client, create_slack_event_adapter, handle_team_join

JOINS_CHANNEL_ID = "C06RMMRMGHE"


@pytest.fixture()
def setenvvar(monkeypatch):
    with mock.patch.dict(os.environ, clear=True):
        envvars = {
            "SIGNING_SECRET": "xapp-token",
            "SLACK_BOT_TOKEN": "xoxb-token",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield


@pytest.fixture
def event_data():
    return {"event": {"user": {"id": "D0730R9KFC2"}}}


@pytest.fixture
def expected_message():
    return (
        ":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
        "We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, "
        "this Slack workspace is the perfect place to connect, collaborate, and stay informed "
        "about all things OWASP.\n\n"
        ":small_blue_diamond: *Get Involved:*\n"
        "• Check out the *#contribute* channel to find ways to get involved with OWASP"
        " projects and initiatives.\n"
        "• Explore individual project channels, which are named *#project-name*,"
        " to dive into specific projects that interest you.\n"
        "• Join our chapter channels, named *#chapter-name*, to connect with "
        "local OWASP members in your area.\n\n"
        ":small_blue_diamond: *Stay Updated:*\n"
        "• Visit *#newsroom* for the latest updates and announcements.\n"
        "• Follow *#external-activities* for news about OWASP's engagement "
        "with the wider security community.\n\n"
        ":small_blue_diamond: *Connect and Learn:*\n"
        "• *#jobs*: Looking for new opportunities? Check out the latest job postings here.\n"
        "• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.\n"
        "• *#project-committee*: Engage with the committee overseeing OWASP projects.\n"
        "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
        "• *#github-admins*: Get support and discuss issues "
        "related to OWASP's GitHub repositories.\n"
        "• *#learning*: Share and find resources to expand your knowledge "
        "in the field of application security.\n\n"
        "We're excited to see the amazing contributions you'll make. "
        "If you have any questions or need assistance, don't hesitate to ask. "
        "Let's work together to make software security visible and improve the"
        " security of the software we all rely on.\n\n"
        "Welcome aboard! :rocket:"
    )


@pytest.fixture
def slack_event_adapter_mock():
    with mock.patch("app.SlackEventAdapter") as mock_adapter:
        yield mock_adapter


@pytest.fixture
def slack_client_mock():
    with mock.patch("app.WebClient") as mock_client:
        yield mock_client


@pytest.fixture
def slack_event_adapter():
    return create_slack_event_adapter("xapp-token", "/slack/events", None)


@pytest.fixture
def slack_client():
    return create_slack_client("xoxb-token")


def test_handle_team_join(
    setenvvar,
    slack_event_adapter_mock,
    slack_client_mock,
    event_data,
    slack_client,
):
    # Configure the mock Slack client to return a specific response for conversations_open
    slack_client_mock.conversations_open.return_value = {"channel": {"id": "mock_channel_id"}}

    with open("welcome_message.txt", "r", encoding="utf-8") as file:
        welcome_message_template = file.read()

    # Call the handle_team_join function with the event data
    handle_team_join(event_data)

    # Check that the Slack client methods were called as expected
    slack_client_mock.chat_postMessage.assert_called_once_with(
        channel=JOINS_CHANNEL_ID, text="<@D0730R9KFC2> joined the team."
    )

    # Check that the direct message was sent
    slack_client_mock.chat_postMessage.assert_any_call(
        channel="mock_channel_id",
        text="Welcome to the OWASP Slack Community!",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": welcome_message_template.format(user_id="D0730R9KFC2").strip(),
                },
            }
        ],
    )
