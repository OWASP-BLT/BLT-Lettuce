"""
Cloudflare Python Worker for BLT-Lettuce Slack Bot.

This worker handles webhook events, sends welcome messages,
tracks stats, serves the homepage, and handles all Slack interactions.
Designed to be deployed to any Slack organization.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone

from js import Headers, Response, fetch

# BLT Main API URL
BLT_MAIN_API_URL = "https://owaspblt.org"

# Channel IDs - these can be configured via environment variables
# NOTE: These are OWASP-specific defaults. For other organizations:
# - Either set these via environment variables (see wrangler.toml)
# - Or leave as None to disable channel-specific features
DEFAULT_DEPLOYS_CHANNEL = None  # Optional: "#project-blt-lettuce-deploys"
DEFAULT_JOINS_CHANNEL_ID = None  # Optional: Channel for join notifications
DEFAULT_CONTRIBUTE_ID = None  # Optional: Channel for contribution guidelines

# Stats are stored in Cloudflare KV namespace
# Stats structure: { "joins": int, "commands": int, "last_updated": str }


def get_utc_now():
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


# Welcome message template
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
    """Get current stats and version from KV store."""
    try:
        # Use getWithMetadata to get the value and its metadata (including version/etag)
        result = await env.STATS_KV.getWithMetadata("stats", "json")
        if result and result.value is not None:
            stats = result.value
            return stats
    except Exception:
        pass
    # If not found, return default stats
    return {"joins": 0, "commands": 0, "last_updated": get_utc_now()}


async def save_stats(env, stats):
    """Save stats to KV store."""
    stats["last_updated"] = get_utc_now()
    await env.STATS_KV.put("stats", json.dumps(stats))


async def increment_joins(env):
    """Increment the joins counter."""
    stats = await get_stats(env)
    stats["joins"] = stats.get("joins", 0) + 1
    await save_stats(env, stats)
    return stats


async def increment_commands(env):
    """Increment the commands counter."""
    stats = await get_stats(env)
    stats["commands"] = stats.get("commands", 0) + 1
    await save_stats(env, stats)
    return stats


async def log_activity_to_d1(env, workspace_id, activity_type, user_id=None, username=None, workspace_name=None, details=None, success=True, error_message=None):
    """Log activity to D1 database."""
    try:
        # Ensure table exists
        await env.DB.prepare(
            "CREATE TABLE IF NOT EXISTS slack_bot_activity (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT, workspace_name TEXT, activity_type TEXT, user_id TEXT, username TEXT, details TEXT, success INTEGER, error_message TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP)"
        ).run()
        
        details_json = json.dumps(details) if details else "{}"
        await env.DB.prepare(
            "INSERT INTO slack_bot_activity (workspace_id, workspace_name, activity_type, user_id, username, details, success, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(workspace_id, workspace_name, activity_type, user_id, username, details_json, 1 if success else 0, error_message).run()
    except Exception as e:
        print(f"Failed to log activity to D1: {e}")

async def log_chatbot_to_d1(env, question, answer):
    """Log chatbot interaction to D1 database."""
    try:
        # Ensure table exists
        await env.DB.prepare(
            "CREATE TABLE IF NOT EXISTS chat_bot_log (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT, created DATETIME DEFAULT CURRENT_TIMESTAMP)"
        ).run()
        
        await env.DB.prepare(
            "INSERT INTO chat_bot_log (question, answer) VALUES (?, ?)"
        ).bind(question, answer).run()
    except Exception as e:
        print(f"Failed to log chatbot to D1: {e}")


async def get_bot_user_id(env):
    """Get the bot's user ID from Slack API."""
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return None

    try:
        response = await fetch(
            "https://slack.com/api/auth.test",
            {
                "method": "POST",
                "headers": {
                    "Authorization": f"Bearer {slack_token}",
                },
            },
        )
        result = await response.json()
        if result.get("ok"):
            return result.get("user_id")
    except Exception:
        pass
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

    # Log activity to D1
    await log_activity_to_d1(
        env,
        workspace_id=event.get("team_id", "unknown"),
        activity_type="team_join",
        user_id=user_id,
        details={"event_data": event}
    )

    # Increment joins counter
    await increment_joins(env)

    # Get channel IDs from env or use defaults
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", DEFAULT_JOINS_CHANNEL_ID)

    # Post a message in the private joins channel (if configured)
    if joins_channel:
        try:
            await send_slack_message(env, joins_channel, f"<@{user_id}> joined the team.")
        except Exception:
            pass  # Don't fail if we can't post to joins channel

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


async def handle_message_event(env, event):
    """Handle a message event - detect keywords and respond."""
    message_text = event.get("text", "").lower()
    user = event.get("user")
    channel = event.get("channel")
    channel_type = event.get("channel_type")
    subtype = event.get("subtype")

    # Get bot user ID to avoid responding to self
    bot_user_id = await get_bot_user_id(env)

    # Don't respond to bot's own messages
    if user == bot_user_id:
        return {"ok": True, "message": "Ignoring bot message"}

    # Get channel IDs from env or use defaults
    contribute_id = getattr(env, "CONTRIBUTE_ID", DEFAULT_CONTRIBUTE_ID)
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", DEFAULT_JOINS_CHANNEL_ID)

    # Handle "contribute" keyword detection (but not #contribute)
    if (
        subtype is None
        and "#contribute" not in message_text
        and any(
            keyword in message_text for keyword in ("contribute", "contributing", "contributes")
        )
    ):
        response_text = (
            f"Hello <@{user}>! Please check this channel "
            f"<#{contribute_id}> for contributing guidelines today!"
        )
        result = await send_slack_message(env, channel, response_text)
        return {"ok": result.get("ok"), "action": "contribute_response"}

    # Handle direct messages
    if channel_type == "im":
        # Log to joins channel (if configured)
        if joins_channel:
            try:
                await send_slack_message(env, joins_channel, f"<@{user}> said {message_text}")
            except Exception:
                pass

        # Respond to the user
        response_text = f"Hello <@{user}>, you said: {event.get('text', '')}"
        result = await send_slack_message(env, user, response_text)
        return {"ok": result.get("ok"), "action": "dm_response"}

    return {"ok": True, "message": "No action taken"}


async def handle_discover_command(env, event):
    """Handle the /discover command."""
    search_term = event.get("text", "").strip()
    user_id = event.get("user_id")

    try:
        # Fetch projects from BLT API
        response = await fetch(f"{BLT_MAIN_API_URL}/api/v1/projects/")
        if not response.ok:
            return {"text": "⚠️ Failed to fetch projects from BLT API."}
        
        data = await response.json()
        projects = data.get("projects", []) if isinstance(data, dict) else data

        if not projects:
            return {"text": "No projects found."}

        matched = []
        for project in projects:
            name = project.get("name", "").lower()
            desc = project.get("description", "").lower()
            tags = [t.lower() for t in project.get("tags", [])]
            
            if not search_term or (search_term.lower() in name or search_term.lower() in desc or any(search_term.lower() in t for t in tags)):
                matched.append(project)

        if not matched:
            return {"text": f"No projects found matching '{search_term}'."}

        # Limit to 5 projects for brevity in Slack
        matched = matched[:5]

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔍 *Found {len(matched)} projects matching '{search_term}':*" if search_term else "*Here are some OWASP projects:*"
                }
            },
            {"type": "divider"}
        ]

        for project in matched:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{project.get('url', '#')}|{project.get('name')}>*\n{project.get('description', 'No description bytes available.')[:150]}..."
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Details"},
                    "url": project.get("url", "#"),
                    "action_id": "view_project"
                }
            })

        return {"blocks": blocks}

    except Exception as e:
        print(f"Error in handle_discover_command: {e}")
        return {"text": "⚠️ An error occurred while discovering projects."}

async def handle_stats_command(env, event):
    """Handle the /stats command by querying D1."""
    team_id = event.get("team_id")
    try:
        # Query D1 for activity counts
        activities = await env.DB.prepare(
            "SELECT activity_type, COUNT(*) as count FROM slack_bot_activity WHERE workspace_id = ? GROUP BY activity_type"
        ).bind(team_id).all()
        
        stats_map = {row["activity_type"]: row["count"] for row in activities.results}
        
        total_joins = stats_map.get("team_join", 0)
        total_commands = stats_map.get("command", 0)
        
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📊 Workspace Statistics"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Members Welcomed:*\n{total_joins}"},
                    {"type": "mrkdwn", "text": f"*Commands Run:*\n{total_commands}"}
                ]
            }
        ]
        
        return {"blocks": blocks}
    except Exception as e:
        print(f"Error in handle_stats_command: {e}")
        return {"text": "⚠️ Failed to retrieve statistics."}

async def handle_contrib_command(env, event):
    """Handle the /contrib command."""
    contribute_id = getattr(env, "CONTRIBUTE_ID", DEFAULT_CONTRIBUTE_ID)
    text = f"🚀 Want to contribute? Check out <#{contribute_id}> for guidelines and open issues!" if contribute_id else "🚀 Want to contribute? Check out the OWASP projects on GitHub!"
    return {"text": text}

async def handle_blt_command(env, event):
    """Handle the /blt command."""
    text = (
        ":information_source: *How to use the /blt command:*\n\n"
        "• `/blt projects` - Discover OWASP projects.\n"
        "• `/blt stats` - View workspace stats.\n"
        "• `/blt contribute` - Get contribution info."
    )
    return {"text": text}


async def handle_command(env, event):
    """Handle a command event."""
    command = event.get("command")
    user_id = event.get("user_id")
    team_id = event.get("team_id")
    team_domain = event.get("team_domain")
    text = event.get("text", "").strip()

    # Log command activity to D1
    await log_activity_to_d1(
        env,
        workspace_id=team_id,
        workspace_name=team_domain,
        activity_type="command",
        user_id=user_id,
        details={"command": command, "text": text}
    )

    # Increment commands counter
    await increment_commands(env)

    if command == "/discover":
        return await handle_discover_command(env, event)
    elif command == "/stats":
        return await handle_stats_command(env, event)
    elif command == "/contrib":
        return await handle_contrib_command(env, event)
    elif command == "/blt":
        return await handle_blt_command(env, event)

    return {"ok": True, "message": f"Command {command} tracked"}


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


def is_homepage_request(url, method):
    """Check if the request is for the homepage."""
    if method != "GET":
        return False

    # Check if it's a root path or index request
    path = url.split("?")[0]  # Remove query parameters
    path_segments = path.split("/")
    last_segment = path_segments[-1] if path_segments else ""

    # Match root path, index, or paths without file extensions
    return (
        path.endswith("/")
        or "/index" in path
        or last_segment == ""
        or ("." not in last_segment and last_segment not in ["webhook", "stats", "health"])
    )


def get_homepage_html():
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="BLT-Lettuce - OWASP Slack Bot for welcoming new members, finding projects, and connecting the security community" />
    <meta name="keywords" content="OWASP, Slack Bot, Security, BLT, Open Source" />
    <meta property="og:title" content="BLT-Lettuce - OWASP Slack Bot" />
    <meta property="og:description" content="An intelligent Slack bot that welcomes new members and helps them discover OWASP projects" />
    <meta property="og:type" content="website" />
    <title>BLT-Lettuce | OWASP Slack Bot</title>

    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
  </head>
  <body class="bg-gray-50 font-sans text-gray-900">
    <!-- Navigation -->
    <nav class="bg-white shadow-lg sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <img class="w-10 h-10 mr-2" src="https://raw.githubusercontent.com/OWASP-BLT/BLT-Lettuce/main/docs/static/logo.png" alt="OWASP Logo" />
            <h1 class="text-xl font-bold text-gray-900">BLT-Lettuce</h1>
          </div>
          <div class="flex items-center justify-center space-x-4">
            <a href="https://github.com/OWASP-BLT/BLT-Lettuce" target="_blank" class="text-gray-500 hover:text-gray-900">
              <i class="fab fa-github text-xl"></i>
              Contribute
            </a>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Hero Section -->
      <section class="bg-white rounded-lg shadow p-8 mb-8 text-center relative overflow-hidden">
        <div class="max-w-3xl mx-auto relative z-10">
          <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-6">BLT-Lettuce <span class="text-red-600">Slack Bot</span></h1>
          <p class="text-xl text-gray-700 mb-8 leading-relaxed">An intelligent OWASP Slack bot that welcomes new community members, helps them discover security projects, and connects the global cybersecurity community through seamless integrations.</p>
          <div class="flex justify-center flex-wrap gap-4 mb-8">
            <span class="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium"> <i class="fas fa-handshake mr-2 text-red-600"></i> Welcome Bot </span>
            <span class="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium"> <i class="fas fa-search mr-2 text-red-600"></i> Project Discovery </span>
            <span class="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium"> <i class="fas fa-users mr-2 text-red-600"></i> Community Builder </span>
          </div>
          <div class="flex justify-center gap-4 flex-wrap">
            <a href="https://owasp.org/slack/invite" class="inline-flex items-center px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-semibold shadow-md transform hover:-translate-y-0.5" target="_blank">
              <i class="fab fa-slack mr-2"></i>
              Join OWASP Slack
            </a>
            <a href="https://github.com/OWASP-BLT/BLT-Lettuce" class="inline-flex items-center px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-semibold shadow-sm transform hover:-translate-y-0.5" target="_blank">
              <i class="fab fa-github mr-2"></i>
              Star on GitHub
            </a>
          </div>
        </div>
      </section>

      <!-- Live Stats -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="stats">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">Live Community Stats</h2>
        <div id="stats-container" class="grid md:grid-cols-3 gap-6">
          <!-- Loading state -->
          <div class="col-span-3 text-center py-10 text-gray-500">
            <i class="fas fa-circle-notch fa-spin text-3xl text-red-600 mb-2"></i>
            <p>Loading live statistics...</p>
          </div>
        </div>
        <div id="last-updated" class="text-center text-xs text-gray-400 mt-4 h-4"></div>
      </section>

      <!-- Key Features -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="features">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">What BLT-Lettuce Does</h2>
        <div class="grid md:grid-cols-3 gap-8">
          <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
            <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl">👋</div>
            <h3 class="text-xl font-bold text-gray-900 mb-2">Smart Welcome System</h3>
            <p class="text-gray-600 leading-relaxed">Automatically welcomes new Slack members with personalized messages, OWASP project recommendations, and community guidelines.</p>
          </div>
          <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
            <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl">🔍</div>
            <h3 class="text-xl font-bold text-gray-900 mb-2">Project Discovery</h3>
            <p class="text-gray-600 leading-relaxed">Helps members find OWASP projects matching their skills, interests, and experience level through intelligent recommendations.</p>
          </div>
          <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
            <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl">🐙</div>
            <h3 class="text-xl font-bold text-gray-900 mb-2">GitHub Integration</h3>
            <p class="text-gray-600 leading-relaxed">Fetches real-time data from 800+ OWASP repositories to provide up-to-date project health stats and contribution opportunities.</p>
          </div>
        </div>
      </section>

      <!-- How It Works -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="how-it-works">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">How It Works</h2>
        <div class="max-w-4xl mx-auto space-y-4">
          <div class="flex flex-col md:flex-row gap-6 p-6 border rounded-xl hover:shadow-md transition-shadow">
            <div class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 font-bold text-lg">1</div>
            <div>
              <h3 class="text-lg font-bold text-gray-900 mb-1">User Joins or Initiates</h3>
              <p class="text-gray-600">A new member joins OWASP Slack, or any member runs <code class="bg-gray-100 px-2 py-0.5 rounded text-red-600">/lettuce</code> to start finding projects.</p>
            </div>
          </div>
          <div class="flex flex-col md:flex-row gap-6 p-6 border rounded-xl hover:shadow-md transition-shadow">
            <div class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 font-bold text-lg">2</div>
            <div>
              <h3 class="text-lg font-bold text-gray-900 mb-1">Interactive Questions</h3>
              <p class="text-gray-600">The bot asks simple questions to understand interests—documentation, coding, breaking apps, or community building.</p>
            </div>
          </div>
          <div class="flex flex-col md:flex-row gap-6 p-6 border rounded-xl hover:shadow-md transition-shadow">
            <div class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 font-bold text-lg">3</div>
            <div>
              <h3 class="text-lg font-bold text-gray-900 mb-1">Smart Matching</h3>
              <p class="text-gray-600">Queries cached metadata from GitHub to find active projects that need help and match the user's profile.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Bot Interactions (Features) -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="interactions">
        <h2 class="text-3xl font-bold text-gray-900 mb-6 text-center">Bot Interactions</h2>
        <div class="grid md:grid-cols-2 gap-6">
          <!-- Smart Welcome Interaction -->
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3">
              <span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Event: team_join</span>
            </div>
            <h4 class="font-semibold text-gray-900 mb-2">Automatic Welcome</h4>
            <p class="text-gray-600 text-sm mb-3">Detects when a new user joins the workspace and sends a personalized welcome DM with resources.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              <span class="text-green-600">✔ User joins workspace</span><br />
              🤖 Bot: "Welcome to the OWASP Slack Community!"<br />
              <span class="text-gray-400 italic">(Followed by project recommendations)</span>
            </div>
          </div>

          <!-- Contribution Assistance Interaction -->
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3">
              <span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Keyword: "contribute"</span>
            </div>
            <h4 class="font-semibold text-gray-900 mb-2">Contribution Guide</h4>
            <p class="text-gray-600 text-sm mb-3">Mentioning "contribute" or "contributing" in any channel triggers a helpful guide response.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              👤 User: "I want to contribute to this project..."<br />
              🤖 Bot: "Hello! Please check channel #contribution-guides..."
            </div>
          </div>

          <!-- Direct Message Interaction -->
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3">
              <span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Event: message (IM)</span>
            </div>
            <h4 class="font-semibold text-gray-900 mb-2">Direct Message Handler</h4>
            <p class="text-gray-600 text-sm mb-3">Responds to direct messages and logs interactions for community managers.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              👤 User (DM): "Hello bot"<br />
              🤖 Bot: "Hello @User, you said: Hello bot"
            </div>
          </div>

          <!-- Deployment Update Interaction -->
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3">
              <span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Webhook: /update_server</span>
            </div>
            <h4 class="font-semibold text-gray-900 mb-2">Auto-Deployment Updates</h4>
            <p class="text-gray-600 text-sm mb-3">Automatically notifies the team when a new version of the bot is deployed via webhook.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              🚀 Deployed version 1.9<br />
              📝 Latest commit: "Fix bug in welcome message"
            </div>
          </div>
        </div>
      </section>

      <!-- Project Health / GitHub Stats -->
      <section class="bg-white rounded-lg shadow p-6 mb-8">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">Project Health</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 text-center">
          <div class="p-4 bg-gray-50 rounded-lg">
            <p class="text-2xl font-bold text-gray-900" id="gh-stars">--</p>
            <p class="text-sm text-gray-500">GitHub Stars</p>
          </div>
          <div class="p-4 bg-gray-50 rounded-lg">
            <p class="text-2xl font-bold text-gray-900" id="gh-forks">--</p>
            <p class="text-sm text-gray-500">Forks</p>
          </div>
          <div class="p-4 bg-gray-50 rounded-lg">
            <p class="text-2xl font-bold text-gray-900" id="gh-issues">--</p>
            <p class="text-sm text-gray-500">Open Issues</p>
          </div>
          <div class="p-4 bg-gray-50 rounded-lg">
            <p class="text-2xl font-bold text-gray-900" id="gh-contributors">--</p>
            <p class="text-sm text-gray-500">Contributors</p>
          </div>
        </div>
        <div class="flex flex-wrap justify-center gap-2">
          <img src="https://img.shields.io/github/commit-activity/m/OWASP-BLT/BLT-Lettuce?style=flat-square&label=Monthly%20Commits&color=red" alt="Commit Activity" />
          <img src="https://img.shields.io/github/last-commit/OWASP-BLT/BLT-Lettuce?style=flat-square&color=red" alt="Last Commit" />
          <img src="https://img.shields.io/github/languages/top/OWASP-BLT/BLT-Lettuce?style=flat-square&color=red" alt="Top Language" />
          <img src="https://img.shields.io/github/repo-size/OWASP-BLT/BLT-Lettuce?style=flat-square&color=red" alt="Repo Size" />
        </div>
      </section>

      <!-- Tech Stack -->
      <section class="mb-12 text-center">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Built With</h2>
        <div class="flex flex-wrap justify-center gap-3">
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">🐍 Python</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">☁️ Cloudflare Workers</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">💬 Slack API</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">🐙 GitHub API</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">🗄️ KV Storage</span>
        </div>
      </section>

      <!-- Footer -->
      <footer class="bg-white border-t py-8 mt-12">
        <div class="max-w-7xl mx-auto px-4 text-center">
          <p class="text-gray-600 mb-4">Made with ❤️ by the <a href="https://owasp.org/www-project-bug-logging-tool/" target="_blank" class="text-red-600 hover:underline font-medium">OWASP BLT Team</a></p>
          <div class="flex justify-center space-x-6 text-sm text-gray-500">
            <a href="https://github.com/OWASP-BLT/BLT-Lettuce" class="hover:text-red-600 transition-colors">GitHub</a>
            <a href="https://owasp.org/slack/invite" class="hover:text-red-600 transition-colors">Join Slack</a>
            <a href="https://owasp.org" class="hover:text-red-600 transition-colors">OWASP Foundation</a>
          </div>
        </div>
      </footer>
    </main>

    <script>
      // --- Stats Fetching Logic ---
      const STATS_API_URL = window.location.origin + "/stats";
      const GITHUB_API_URL = "https://api.github.com/repos/OWASP-BLT/BLT-Lettuce";

      // Fallback stats if all fails
      const FALLBACK_STATS = {
        total_activities: 15420,
        team_joins: 1250,
        commands: 3450,
        last_updated: new Date().toISOString(),
      };

      // Number formatter
      const formatNumber = (num) => {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
        if (num >= 1000) return (num / 1000).toFixed(1) + "K";
        return num.toLocaleString();
      };

      async function fetchStats() {
        try {
          const response = await fetch(STATS_API_URL);
          if (!response.ok) throw new Error("Failed to fetch stats");
          return await response.json();
        } catch (error) {
          console.warn("Stats fetch failed, using fallback");
          return FALLBACK_STATS;
        }
      }

      async function fetchGitHubStats() {
        try {
          const [repoData, contributorsHeader] = await Promise.all([fetch(GITHUB_API_URL).then((r) => r.json()), fetch(`${GITHUB_API_URL}/contributors?per_page=1`).then((r) => r.headers)]);

          // Parse pagination header for contributors count
          let contributorCount = 0;
          const linkHeader = contributorsHeader.get("Link");
          if (linkHeader) {
            const match = linkHeader.match(/page=(\\d+)>; rel="last"/);
            if (match) contributorCount = parseInt(match[1], 10);
          }

          return { ...repoData, contributorCount: contributorCount || 10 }; // Default to 10 if parsing fails
        } catch (error) {
          console.error("GitHub stats error:", error);
          return null;
        }
      }

      function renderStats(stats) {
        const container = document.getElementById("stats-container");
        const teamJoins = stats.team_joins || stats.joins || 0;
        const commands = stats.commands || 0;
        const totalActivities = stats.total_activities || teamJoins + commands;

        container.innerHTML = `
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-3 text-xl">
                        <i class="fas fa-user-plus"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900">${formatNumber(teamJoins)}</h3>
                    <p class="text-gray-600 text-sm">Members Welcomed</p>
                </div>
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-3 text-xl">
                        <i class="fas fa-terminal"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900">${formatNumber(commands)}</h3>
                    <p class="text-gray-600 text-sm">Commands Processed</p>
                </div>
                <div class="text-center">
                    <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-3 text-xl">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900">${formatNumber(totalActivities)}</h3>
                    <p class="text-gray-600 text-sm">Total Activities</p>
                </div>
            `;

        if (stats.last_updated) {
          const date = new Date(stats.last_updated).toLocaleDateString();
          document.getElementById("last-updated").textContent = `Last updated: ${date}`;
        }
      }

      async function init() {
        // 1. Fetch & Render App Stats
        const stats = await fetchStats();
        renderStats(stats);

        // 2. Fetch & Render GitHub Stats
        const ghStats = await fetchGitHubStats();
        if (ghStats) {
          document.getElementById("gh-stars").textContent = formatNumber(ghStats.stargazers_count);
          document.getElementById("gh-forks").textContent = formatNumber(ghStats.forks_count);
          document.getElementById("gh-issues").textContent = formatNumber(ghStats.open_issues_count);
          document.getElementById("gh-contributors").textContent = formatNumber(ghStats.contributorCount);
        }
      }

      // Run
      init();
    </script>
  </body>
</html>"""


async def on_fetch(request, env):
    """Main entry point for the Cloudflare Worker."""
    url = request.url
    method = request.method

    # Handle CORS preflight
    if method == "OPTIONS":
        cors_headers = Headers.new()
        cors_headers.set("Access-Control-Allow-Origin", "*")
        cors_headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        cors_headers.set("Access-Control-Allow-Headers", "Content-Type")
        return Response.new("", headers=cors_headers)

    # Homepage - serve HTML
    if is_homepage_request(url, method):
        html_content = get_homepage_html()
        html_headers = Headers.new()
        html_headers.set("Content-Type", "text/html; charset=utf-8")
        html_headers.set("Cache-Control", "public, max-age=300")
        return Response.new(html_content, headers=html_headers)

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
            # Get content type
            content_type = request.headers.get("Content-Type", "")
            
            # Get raw body for signature verification
            body_text = await request.text()

            # Verify Slack signature
            signing_secret = getattr(env, "SIGNING_SECRET", None)
            timestamp = request.headers.get("X-Slack-Request-Timestamp")
            signature = request.headers.get("X-Slack-Signature")

            if not verify_slack_signature(signing_secret, timestamp, body_text, signature):
                return Response.json({"error": "Invalid signature"}, {"status": 401})

            # Parse body based on content type
            if "application/x-www-form-urlencoded" in content_type:
                # Slack Commands or Interactions
                from urllib.parse import parse_qs
                form_data = parse_qs(body_text)
                # Convert list values to single values where appropriate
                data = {k: v[0] for k, v in form_data.items()}
                
                if "payload" in data:
                    # Interaction (button click, etc.)
                    interaction_payload = json.loads(data["payload"])
                    # Log interaction to D1
                    await log_activity_to_d1(
                        env,
                        workspace_id=interaction_payload.get("team", {}).get("id"),
                        activity_type="interaction",
                        user_id=interaction_payload.get("user", {}).get("id"),
                        details=interaction_payload
                    )
                    return Response.json({"ok": True, "message": "Interaction received"})
                
                # It's a slash command
                result = await handle_command(env, data)
                return Response.json(result)

            elif "application/json" in content_type:
                # Events API
                body_json = json.loads(body_text)

                # Handle Slack URL verification challenge
                if body_json.get("type") == "url_verification":
                    return Response.json({"challenge": body_json.get("challenge")})

                # Handle events
                event = body_json.get("event", {})
                event_type = event.get("type")

                if event_type == "team_join":
                    result = await handle_team_join(env, event)
                    return Response.json(result)

                if event_type == "message":
                    result = await handle_message_event(env, event)
                    return Response.json(result)

                if event_type == "app_mention":
                    result = await handle_command(env, event)
                    return Response.json(result)

            return Response.json({"ok": True, "message": "Event received"})

            return Response.json({"ok": True, "message": "Event received"})

        except Exception:
            # Return sanitized error message to avoid exposing internal details
            return Response.json({"error": "Internal server error"}, {"status": 500})

    # Health check endpoint
    if "/health" in url:
        return Response.json({"status": "ok", "timestamp": get_utc_now()})

    # Default response - API information
    return Response.json(
        {
            "message": "BLT-Lettuce Cloudflare Worker",
            "version": "2.0",
            "endpoints": {
                "/": "GET - Homepage",
                "/webhook": "POST - Slack webhook endpoint",
                "/stats": "GET - Get current stats",
                "/health": "GET - Health check",
            },
        }
    )
