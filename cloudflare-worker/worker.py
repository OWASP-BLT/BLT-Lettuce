"""
Cloudflare Python Worker for BLT-Lettuce Slack Bot.

This worker handles webhook events, sends welcome messages,
and tracks stats for joins and commands.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone

# Cloudflare Python Workers expose Response/fetch via cloudflare.workers.
# In some local tooling this import may not resolve, so fall back to js module.
try:  # pragma: no cover - runtime-provided
    from cloudflare.workers import Response, fetch
except Exception:  # pragma: no cover - fallback for lints
    from js import Response, fetch
# Stats are stored in Cloudflare KV namespace
# Stats structure: { "joins": int, "commands": int, "last_updated": str }


def get_utc_now():
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


WELCOME_MESSAGE = (
    ":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
    "We're thrilled to have you here! Whether you're new to OWASP or a "
    "long-time contributor, this Slack workspace is the perfect place to "
    "connect, collaborate, and stay informed about all things OWASP.\n\n"
    ":small_blue_diamond: *Get Involved:*\n"
    "• Check out the *#contribute* channel to find ways to get involved "
    "with OWASP projects and initiatives.\n"
    "• Explore individual project channels, which are named *#project-name*, "
    "to dive into specific projects that interest you.\n"
    "• Join our chapter channels, named *#chapter-name*, to connect with "
    "local OWASP members in your area.\n\n"
    ":small_blue_diamond: *Stay Updated:*\n"
    "• Visit *#newsroom* for the latest updates and announcements.\n"
    "• Follow *#external-activities* for news about OWASP's engagement "
    "with the wider security community.\n\n"
    ":small_blue_diamond: *Connect and Learn:*\n"
    "• *#jobs*: Looking for new opportunities? Check out the latest "
    "job postings here.\n"
    "• *#leaders*: Connect with OWASP leaders and stay informed about "
    "leadership activities.\n"
    "• *#project-committee*: Engage with the committee overseeing "
    "OWASP projects.\n"
    "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
    "• *#github-admins*: Get support and discuss issues related to "
    "OWASP's GitHub repositories.\n"
    "• *#learning*: Share and find resources to expand your knowledge "
    "in the field of application security.\n\n"
    "We're excited to see the amazing contributions you'll make. If you "
    "have any questions or need assistance, don't hesitate to ask. Let's "
    "work together to make software security visible and improve the "
    "security of the software we all rely on.\n\n"
    "Welcome aboard! :rocket:"
)


async def get_stats(env):
    """Get current stats from KV store."""
    try:
        kv = getattr(env, "STATS_KV", None)
        if not kv:
            return {"joins": 0, "commands": 0, "last_updated": get_utc_now()}

        result = await kv.get("stats")
        if result:
            return json.loads(result)
    except Exception as e:
        print(f"Error getting stats: {e}")
    # If not found, return default stats
    return {"joins": 0, "commands": 0, "last_updated": get_utc_now()}


async def save_stats(env, stats):
    """Save stats to KV store."""
    try:
        kv = getattr(env, "STATS_KV", None)
        if not kv:
            print("Warning: STATS_KV not available")
            return

        stats["last_updated"] = get_utc_now()
        await kv.put("stats", json.dumps(stats))
    except Exception as e:
        print(f"Error saving stats: {e}")


async def increment_joins(env):
    """Increment the joins counter."""
    try:
        stats = await get_stats(env)
        stats["joins"] = stats.get("joins", 0) + 1
        await save_stats(env, stats)
        return stats
    except Exception as e:
        print(f"Error incrementing joins: {e}")
        return None


async def increment_commands(env):
    """Increment the commands counter."""
    try:
        stats = await get_stats(env)
        stats["commands"] = stats.get("commands", 0) + 1
        await save_stats(env, stats)
        return stats
    except Exception as e:
        print(f"Error incrementing commands: {e}")
        return None


async def send_slack_message(env, channel, text, blocks=None):
    """Send a message to Slack."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}

    payload = {
        "channel": channel,
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks

    response = await fetch(
        "https://slack.com/api/chat.postMessage",
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {slack_token}",
            },
            "body": json.dumps(payload),
        },
    )
    return await response.json()


async def open_conversation(env, user_id):
    """Open a DM conversation with a user."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}

    response = await fetch(
        "https://slack.com/api/conversations.open",
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {slack_token}",
            },
            "body": json.dumps({"users": user_id}),
        },
    )
    return await response.json()


async def handle_team_join(env, event):
    """Handle a team_join event - send welcome message to new user."""
    user_id = event.get("user", {}).get("id")
    if not user_id:
        return {"error": "No user ID in event"}

    # Increment joins counter
    await increment_joins(env)

    # Open DM with user
    dm_response = await open_conversation(env, user_id)
    if not dm_response.get("ok"):
        return {"error": f"Failed to open DM: {dm_response.get('error')}"}

    dm_channel = dm_response.get("channel", {}).get("id")
    if not dm_channel:
        return {"error": "Failed to get DM channel ID"}

    # Format welcome message
    welcome_text = WELCOME_MESSAGE.format(user_id=user_id)
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_text.strip()}}]

    # Send welcome message
    result = await send_slack_message(
        env,
        dm_channel,
        "Welcome to the OWASP Slack Community!",
        blocks,
    )

    return {"ok": result.get("ok"), "user_id": user_id}


async def handle_command(env, event):
    """Handle a command event."""
    # Increment commands counter
    await increment_commands(env)
    return {"ok": True, "message": "Command tracked"}


async def handle_poll_command(env, command_text, user_id, channel_id):
    """
    Handle /blt_poll slash command.
    Usage: /blt_poll Question | option1 | option2 | option3
    """
    try:
        import time

        # Parse command text: "Question | option1 | option2 | ..."
        parts = [p.strip() for p in command_text.split("|")]

        if len(parts) < 3:
            return {
                "response_type": "ephemeral",
                "text": (
                    "❌ Invalid poll format.\n"
                    "Usage: `/blt_poll Question | option1 | option2 | option3`\n\n"
                ),
            }

        question = parts[0]
        options = parts[1:]

        if len(options) > 5:
            return {
                "response_type": "ephemeral",
                "text": "❌ Maximum 5 options allowed per poll.",
            }

        # Create poll metadata and store in KV
        poll_id = f"poll_{channel_id}_{user_id}_{int(time.time())}"
        poll_data = {
            "id": poll_id,
            "question": question,
            "options": {str(i): {"text": opt, "votes": 0} for i, opt in enumerate(options)},
            "created_by": user_id,
            "channel_id": channel_id,
            "votes": {},  # user_id -> option_index mapping
        }

        # Store poll in KV (expires in 24 hours)
        try:
            kv = getattr(env, "STATS_KV", None)
            if kv:
                await kv.put(
                    poll_id,
                    json.dumps(poll_data),
                    expiration_ttl=86400,
                )
            else:
                print("Warning: STATS_KV not available")
        except Exception as e:
            print(f"Failed to store poll in KV: {e}")
            import traceback

            traceback.print_exc()

        # Build interactive poll message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 *{question}*\n_Poll by <@{user_id}>_",
                },
            }
        ]

        # Add option buttons (numbered emoji + button)
        emoji_map = {0: "1️⃣", 1: "2️⃣", 2: "3️⃣", 3: "4️⃣", 4: "5️⃣"}

        for i, option in enumerate(options):
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji_map[i]} {option}\n0 votes",
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Vote"},
                        "value": f"{poll_id}_{i}",
                        "action_id": f"poll_vote_{poll_id}_{i}",
                    },
                }
            )

        # Increment command counter
        await increment_commands(env)

        # Return the poll message for posting to channel
        return {
            "response_type": "in_channel",
            "text": f"📊 {question}",
            "blocks": blocks,
        }

    except Exception as e:
        print(f"poll command error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ Error creating poll: {str(e)}",
        }


def _build_poll_blocks(poll_data):
    """Render poll blocks with current vote counts."""
    question = poll_data.get("question", "Poll")
    user_id = poll_data.get("created_by", "")
    options = poll_data.get("options", {})

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📊 *{question}*\n_Poll by <@{user_id}>_",
            },
        }
    ]

    emoji_map = {0: "1️⃣", 1: "2️⃣", 2: "3️⃣", 3: "4️⃣", 4: "5️⃣"}
    for i, opt in options.items():
        idx = int(i)
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji_map.get(idx, '')} {opt['text']}\n{opt.get('votes', 0)} votes",
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Vote"},
                    "value": f"{poll_data.get('id')}_{idx}",
                    "action_id": f"poll_vote_{poll_data.get('id')}_{idx}",
                },
            }
        )

    return blocks


async def handle_poll_vote(env, payload):
    """Handle interactive button clicks for poll voting."""
    try:
        import json as json_lib

        actions = payload.get("actions", [])
        if not actions:
            return {"response_type": "ephemeral", "text": "No action found."}

        action = actions[0]
        value = action.get("value", "")
        user_id = payload.get("user", {}).get("id")
        response_url = payload.get("response_url")

        if "_" not in value:
            return {"response_type": "ephemeral", "text": "Invalid poll vote payload."}

        poll_id, option_idx = value.rsplit("_", 1)
        option_idx = int(option_idx)

        # Load poll
        kv = getattr(env, "STATS_KV", None)
        if not kv:
            return {"response_type": "ephemeral", "text": "KV storage not available."}

        poll_json = await kv.get(poll_id)
        if not poll_json:
            return {"response_type": "ephemeral", "text": "Poll not found or expired."}

        poll_data = json_lib.loads(poll_json)

        # Remove previous vote
        if user_id in poll_data.get("votes", {}):
            old_idx = poll_data["votes"][user_id]
            poll_data["options"][str(old_idx)]["votes"] = max(
                0, poll_data["options"][str(old_idx)].get("votes", 0) - 1
            )

        # Add new vote
        poll_data.setdefault("votes", {})[user_id] = option_idx
        poll_data["options"][str(option_idx)]["votes"] = (
            poll_data["options"][str(option_idx)].get("votes", 0) + 1
        )

        # Save back
        await kv.put(poll_id, json_lib.dumps(poll_data), expiration_ttl=86400)

        # Build updated message
        updated_blocks = _build_poll_blocks(poll_data)
        question = poll_data.get("question", "Poll")

        # Send update to response_url if available
        if response_url:
            try:
                update_payload = {
                    "replace_original": True,
                    "text": f"📊 {question}",
                    "blocks": updated_blocks,
                }
                response = await fetch(
                    response_url,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    body=json_lib.dumps(update_payload),
                )
                print(f"Update response status: {response.status}")
            except Exception as e:
                print(f"Error sending update to response_url: {e}")

        # Acknowledge the interaction immediately (required by Slack)
        return {"text": ""}

    except Exception as e:
        print(f"poll vote error: {e}")
        import traceback

        traceback.print_exc()
        return {"response_type": "ephemeral", "text": f"Error recording vote: {e}"}


def verify_slack_signature(signing_secret, timestamp, body, signature):
    """Verify that the request came from Slack using the signing secret."""
    if not signing_secret or not timestamp or not signature:
        return False

    # Check timestamp to prevent replay attacks (allow 5 minutes)
    try:
        request_time = int(timestamp)
        current_time = int(datetime.now(timezone.utc).timestamp())
        if abs(current_time - request_time) > 300:
            return False
    except (ValueError, TypeError):
        return False

    # Calculate expected signature
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_signature = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    # Compare signatures using constant-time comparison
    return hmac.compare_digest(expected_signature, signature)


async def on_fetch(request, env, ctx):
    """Main entry point for the Cloudflare Worker."""
    url = request.url
    method = request.method

    # Handle CORS preflight
    if method == "OPTIONS":
        return Response.new(
            "",
            {
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            },
        )

    # Stats endpoint - returns current stats as JSON
    if "/stats" in url and method == "GET":
        stats = await get_stats(env)
        return Response.json(
            stats,
            {
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                },
            },
        )

    # Webhook endpoint for Slack events
    if "/webhook" in url and method == "POST":
        try:
            # Get raw body for signature verification
            body_text = await request.text()
            content_type = request.headers.get("content-type", "")

            # Parse content type
            if "application/x-www-form-urlencoded" in content_type:
                import urllib.parse

                parsed = urllib.parse.parse_qs(body_text)
                body_json = {k: v[0] if v else "" for k, v in parsed.items()}
                # If this is an interactive payload, decode JSON inside 'payload'
                if "payload" in body_json:
                    body_json = json.loads(body_json.get("payload", "{}"))
            else:
                body_json = json.loads(body_text)

            if body_json.get("type") != "url_verification":
                signing_secret = getattr(env, "SIGNING_SECRET", None)
                # Some gateways lowercase header names; check both.
                timestamp = request.headers.get(
                    "X-Slack-Request-Timestamp"
                ) or request.headers.get("x-slack-request-timestamp")
                signature = request.headers.get("X-Slack-Signature") or request.headers.get(
                    "x-slack-signature"
                )

                if not verify_slack_signature(signing_secret, timestamp, body_text, signature):
                    return Response.json({"error": "Invalid signature"}, {"status": 401})

            # Handle Slack URL verification challenge
            if body_json.get("type") == "url_verification":
                return Response.json({"challenge": body_json.get("challenge")})

            # Handle interactive actions (e.g., poll votes) - check this BEFORE slash commands
            if body_json.get("type") == "block_actions":
                print(f"Handling block_actions for user {body_json.get('user', {}).get('id')}")
                result = await handle_poll_vote(env, body_json)
                print(f"Poll vote result: {result}")
                return Response.json(result)

            # Handle slash commands
            if body_json.get("type") == "slash_commands" or body_json.get("command"):
                command = body_json.get("command")
                command_text = body_json.get("text", "")
                user_id = body_json.get("user_id")
                channel_id = body_json.get("channel_id")

                if command == "/blt_poll":
                    result = await handle_poll_command(env, command_text, user_id, channel_id)
                    return Response.json(result)

                # Handle other commands
                result = await handle_command(env, {})
                return Response.json(result)

            # Handle events
            event = body_json.get("event", {})
            event_type = event.get("type")

            if event_type == "team_join":
                result = await handle_team_join(env, event)
                return Response.json(result)

            if event_type == "app_mention":
                result = await handle_command(env, event)
                return Response.json(result)

            return Response.json({"ok": True, "message": "Event received"})

        except Exception:
            # Return sanitized error message to avoid exposing internal details
            return Response.json({"error": "Internal server error"}, {"status": 500})

    # Health check endpoint
    if "/health" in url:
        return Response.json({"status": "ok", "timestamp": get_utc_now()})

    # Default response
    return Response.json(
        {
            "message": "BLT-Lettuce Cloudflare Worker",
            "endpoints": {
                "/webhook": "POST - Slack webhook endpoint",
                "/stats": "GET - Get current stats",
                "/health": "GET - Health check",
            },
        }
    )
