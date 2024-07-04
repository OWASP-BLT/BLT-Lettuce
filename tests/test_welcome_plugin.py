import pytest
from unittest import mock
import os
from app import handle_team_join

JOINS_CHANNEL_ID = "C06RMMRMGHE"

@pytest.fixture()
def setenvvar(monkeypatch):
    with mock.patch.dict(os.environ, clear=True):
        envvars = {
            "API_AUDIENCE": "https://mock.com",
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


def test_handle_team_join_successful(mocker, event_data, expected_message):
    # event_data={
    #     "event": {
    #         "user": {
    #             "id": "D0730R9KFC2"
    #         }
    #     }
    # }
    mock_client = mocker.patch("app.client")
    # Mock responses for chat_postMessage and conversations_open
    mock_client.chat_postMessage.return_value = {"ok": True}
    mock_client.conversations_open.return_value = {"channel": {"id": "C06RBJ779CH"}}

    mock_open_file = mocker.mock_open(read_data=expected_message)
    mocker.patch("builtins.open", mock_open_file)

    handle_team_join(event_data)

    # Assert that the chat_postMessage was called with the correct parameters
    mock_client.chat_postMessage.assert_any_call(
        channel=JOINS_CHANNEL_ID, text="<@D0730R9KFC2> joined the team."
    )

    mock_client.conversations_open.assert_called_once_with(users=["D0730R9KFC2"])
    welcome_message = expected_message.format(user_id="D0730R9KFC2")
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_message.strip()}}]
    mock_client.chat_postMessage.assert_any_call(
        channel="C06RBJ779CH", text="Welcome to the OWASP Slack Community!", blocks=blocks
    )


if __name__ == "__main__":
    pytest.main()
