"""
Cloudflare Python Worker for BLT-Lettuce Slack Bot.

This worker handles webhook events, sends welcome messages,
tracks stats for joins and commands, and provides project recommendations.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone

from js import Response, fetch

# Import project recommender
try:
    from project_recommender import ProjectRecommender, load_projects_metadata
except ImportError as e:
    # Fallback if module not available (e.g., during initial deployment)
    print(f"Warning: project_recommender not available: {e}")
    ProjectRecommender = None
    load_projects_metadata = None

# Stats are stored in Cloudflare KV namespace
# Stats structure: { "joins": int, "commands": int, "last_updated": str }

# Load projects metadata for recommendations
PROJECTS_METADATA = None
if load_projects_metadata:
    try:
        PROJECTS_METADATA = load_projects_metadata()
    except FileNotFoundError:
        print("Warning: projects_metadata.json not found, recommendations disabled")
    except Exception as e:
        print(f"Error loading projects metadata: {e}")


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
    """Get current stats and version from KV store."""
    try:
        # Use getWithMetadata to get the value and its metadata (including version/etag)
        result = await env.STATS_KV.getWithMetadata("stats", "json")
        if result and result.value is not None:
            stats = result.value
            etag = getattr(result, "etag", None)
            return stats, etag
    except Exception:
        pass
    # If not found, return default stats and None for etag
    return {"joins": 0, "commands": 0, "last_updated": get_utc_now()}, None


async def save_stats(env, stats, etag=None):
    """Save stats to KV store with optional optimistic locking."""
    stats["last_updated"] = get_utc_now()
    options = {}
    if etag:
        options["if_match"] = etag
    await env.STATS_KV.put("stats", json.dumps(stats), **options)


async def increment_joins(env, max_retries=5):
    """Increment the joins counter atomically with optimistic locking."""
    for _ in range(max_retries):
        stats, etag = await get_stats(env)
        stats["joins"] = stats.get("joins", 0) + 1
        try:
            await save_stats(env, stats, etag)
            return stats
        except Exception:
            # If the put failed due to version conflict, retry
            continue
    raise Exception("Failed to increment joins after multiple retries due to concurrent updates.")


async def increment_commands(env, max_retries=5):
    """Increment the commands counter atomically with optimistic locking."""
    for _ in range(max_retries):
        stats, etag = await get_stats(env)
        stats["commands"] = stats.get("commands", 0) + 1
        try:
            await save_stats(env, stats, etag)
            return stats
        except Exception:
            # If the put failed due to version conflict, retry
            continue
    raise Exception(
        "Failed to increment commands after multiple retries due to concurrent updates."
    )


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


async def handle_projects_endpoint(request):
    """Handle GET /projects endpoint - return available categories."""
    if not PROJECTS_METADATA or not ProjectRecommender:
        return Response.json(
            {"error": "Project recommendation service not available"},
            {"status": 503},
        )

    return Response.json(
        {
            "technologies": PROJECTS_METADATA.get("technologies", []),
            "missions": PROJECTS_METADATA.get("missions", []),
            "levels": PROJECTS_METADATA.get("levels", []),
            "types": PROJECTS_METADATA.get("types", []),
            "total_projects": PROJECTS_METADATA.get("total_projects", 0),
        },
        {"headers": {"Access-Control-Allow-Origin": "*"}},
    )


async def handle_recommendation_request(request):
    """Handle POST /recommend endpoint - return project recommendations."""
    if not PROJECTS_METADATA or not ProjectRecommender:
        return Response.json(
            {"error": "Project recommendation service not available"},
            {"status": 503},
        )

    try:
        body = await request.json()
        recommender = ProjectRecommender(PROJECTS_METADATA)

        # Extract parameters
        approach = body.get("approach", "technology")  # 'technology' or 'mission'
        technology = body.get("technology")
        mission = body.get("mission")
        level = body.get("level")
        project_type = body.get("type")
        contribution_type = body.get("contribution_type")
        top_n = body.get("top_n", 3)

        recommendations = []

        if approach == "technology" and technology:
            # Technology-based recommendations
            recommendations = recommender.recommend_by_technology(
                technology=technology,
                level=level,
                project_type=project_type,
                top_n=top_n,
            )
        elif approach == "mission" and mission:
            # Mission-based recommendations
            recommendations = recommender.recommend_by_mission(
                mission=mission,
                contribution_type=contribution_type,
                top_n=top_n,
            )
        else:
            # Fallback recommendations
            recommendations = recommender.get_fallback_recommendations(top_n=top_n)

        # Format recommendations
        formatted = []
        for proj in recommendations:
            formatted.append(
                {
                    "name": proj.get("name"),
                    "description": proj.get("description"),
                    "url": proj.get("url"),
                    "technologies": proj.get("technologies", []),
                    "missions": proj.get("missions", []),
                    "level": proj.get("level"),
                    "type": proj.get("type"),
                }
            )

        return Response.json(
            {
                "ok": True,
                "approach": approach,
                "criteria": {
                    "technology": technology,
                    "mission": mission,
                    "level": level,
                    "type": project_type,
                },
                "recommendations": formatted,
            },
            {"headers": {"Access-Control-Allow-Origin": "*"}},
        )

    except Exception as e:
        return Response.json(
            {"error": f"Failed to generate recommendations: {str(e)}"},
            {"status": 400},
        )


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


async def on_fetch(request, env):
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

            # Verify Slack signature (skip for url_verification)
            body_json = json.loads(body_text)
            if body_json.get("type") != "url_verification":
                signing_secret = getattr(env, "SIGNING_SECRET", None)
                timestamp = request.headers.get("X-Slack-Request-Timestamp")
                signature = request.headers.get("X-Slack-Signature")

                if not verify_slack_signature(signing_secret, timestamp, body_text, signature):
                    return Response.json({"error": "Invalid signature"}, {"status": 401})

            # Handle Slack URL verification challenge
            if body_json.get("type") == "url_verification":
                return Response.json({"challenge": body_json.get("challenge")})

            # Handle events
            event = body_json.get("event", {})
            event_type = event.get("type")

            if event_type == "team_join":
                result = await handle_team_join(env, event)
                return Response.json(result)

            if event_type == "app_mention" or body_json.get("command"):
                result = await handle_command(env, event)
                return Response.json(result)

            return Response.json({"ok": True, "message": "Event received"})

        except Exception:
            # Return sanitized error message to avoid exposing internal details
            return Response.json({"error": "Internal server error"}, {"status": 500})

    # Health check endpoint
    if "/health" in url:
        return Response.json({"status": "ok", "timestamp": get_utc_now()})

    # Project recommendation endpoints
    if "/projects" in url and method == "GET":
        return await handle_projects_endpoint(request)

    if "/recommend" in url and method == "POST":
        return await handle_recommendation_request(request)

    # Default response
    return Response.json(
        {
            "message": "BLT-Lettuce Cloudflare Worker",
            "endpoints": {
                "/webhook": "POST - Slack webhook endpoint",
                "/stats": "GET - Get current stats",
                "/health": "GET - Health check",
                "/projects": "GET - List available technologies, missions, and metadata",
                "/recommend": "POST - Get project recommendations",
            },
        }
    )
