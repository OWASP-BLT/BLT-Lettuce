"""
Poll plugin for BLT-Lettuce Slack Bot.

Implements the /blt_poll slash command to create polls in Slack.
Usage: /blt_poll Question | option1 | option2 | option3
"""

import json
import time
from datetime import datetime, timezone


def get_utc_now():
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def build_poll_blocks(poll_data):
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


class PollPlugin:
    """Plugin to handle poll creation and voting."""

    def __init__(self):
        """Initialize the poll plugin."""
        self.command = "/blt_poll"

    async def handle_poll_command(self, env, command_text, user_id, channel_id):
        """
        Handle /blt_poll command.
        
        Usage: /blt_poll Question | option1 | option2 | option3
        
        Args:
            env: Cloudflare Worker environment with SLACK_TOKEN
            command_text: The text after the command (question and options)
            user_id: ID of the user who invoked the command
            channel_id: Channel ID where the command was invoked
            
        Returns:
            dict: Slack response payload
        """
        try:
            # Parse the command text: "Question | option1 | option2 | ..."
            parts = [p.strip() for p in command_text.split("|")]
            
            if len(parts) < 3:
                return {
                    "response_type": "ephemeral",
                    "text": (
                        "❌ Invalid poll format.\n"
                        "Usage: `/blt_poll Question | option1 | option2 | option3`\n\n"
                        "Example: `/blt_poll Best programming language | Python | Go | Rust | JavaScript`"
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
            blocks = build_poll_blocks(poll_data)
            
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

    async def handle_poll_vote(self, env, payload, fetch):
        """
        Handle interactive button clicks for poll voting.
        
        Args:
            env: Cloudflare Worker environment
            payload: Interactive payload from Slack
            fetch: Fetch function for making HTTP requests
            
        Returns:
            dict: Response to acknowledge the interaction
        """
        try:
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

            poll_data = json.loads(poll_json)

            # Remove previous vote
            if user_id in poll_data.get("votes", {}):
                old_idx = poll_data["votes"][user_id]
                poll_data["options"][str(old_idx)]["votes"] = max(
                    0, poll_data["options"][str(old_idx)].get("votes", 0) - 1
                )

            # Add new vote
            poll_data.setdefault("votes", {})[user_id] = option_idx
            poll_data["options"][str(option_idx)]["votes"] = poll_data["options"][
                str(option_idx)
            ].get("votes", 0) + 1

            # Save back
            await kv.put(poll_id, json.dumps(poll_data), expiration_ttl=86400)

            # Build updated message
            updated_blocks = build_poll_blocks(poll_data)
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
                        body=json.dumps(update_payload),
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
