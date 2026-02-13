# BLT-Lettuce Cloudflare Worker

A Cloudflare Python Worker that handles Slack webhooks, sends welcome messages to new users, and tracks statistics.

## Features

- **Webhook Endpoint**: Receives Slack events via webhook
- **Welcome Messages**: Automatically sends welcome messages to new team members
- **Stats Tracking**: Tracks number of joins and commands run
- **Stats API**: Provides a JSON endpoint for stats consumption
- **Project Recommendations**: AI-powered OWASP project recommendations based on technology or mission
- **Project Discovery**: Browse available technologies, missions, and difficulty levels

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | Slack webhook endpoint for receiving events |
| `/stats` | GET | Returns current statistics as JSON |
| `/health` | GET | Health check endpoint |
| `/projects` | GET | Returns available technologies, missions, levels, and project types |
| `/recommend` | POST | Returns personalized project recommendations |

## Setup

### Prerequisites

- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- Cloudflare account
- Slack Bot Token and Signing Secret

### Installation

1. Install Wrangler:
   ```bash
   npm install -g wrangler
   ```

2. Login to Cloudflare:
   ```bash
   wrangler login
   ```

3. Create the KV namespace for stats:
   ```bash
   wrangler kv:namespace create "STATS_KV"
   ```

4. Update `wrangler.toml` with the KV namespace ID from the previous command.

5. Set up secrets:
   ```bash
   wrangler secret put SLACK_TOKEN
   wrangler secret put SIGNING_SECRET
   ```

6. Deploy the worker:
   ```bash
   wrangler deploy
   ```

## Configuration

### Slack App Setup

1. Go to [Slack API](https://api.slack.com/apps) and create a new app
2. Enable Event Subscriptions and add the webhook URL: `https://your-worker.workers.dev/webhook`
3. Subscribe to the `team_join` event
4. Install the app to your workspace
5. Copy the Bot User OAuth Token and use it for `SLACK_TOKEN`
6. Copy the Signing Secret and use it for `SIGNING_SECRET`

### Required Bot Permissions

- `chat:write` - Send messages
- `im:write` - Open DM conversations
- `users:read` - Read user information

## Stats

Stats are stored in Cloudflare KV and include:
- `joins`: Number of new team members who have joined
- `commands`: Number of commands run
- `last_updated`: Timestamp of last update

## Development

Run locally:
```bash
wrangler dev
```

View logs:
```bash
wrangler tail
```

## Stats Dashboard

View the stats dashboard at the GitHub Pages site for this repository.

## Project Recommendations API

### GET /projects

Returns metadata about available project categories.

**Response:**
```json
{
  "technologies": ["python", "java", "javascript", "cloud", "mobile", ...],
  "missions": ["learning", "tool", "documentation", "vulnerable-app", ...],
  "levels": ["beginner", "intermediate", "advanced"],
  "types": ["tool", "documentation", "training", "vulnerable-app", ...],
  "total_projects": 338
}
```

### POST /recommend

Get personalized project recommendations based on preferences.

**Request Body:**
```json
{
  "approach": "technology",
  "technology": "python",
  "level": "beginner",
  "type": "tool",
  "top_n": 3
}
```

Or for mission-based approach:
```json
{
  "approach": "mission",
  "mission": "learning",
  "contribution_type": "code",
  "top_n": 5
}
```

**Parameters:**
- `approach` (string): Either "technology" or "mission"
- `technology` (string): Technology stack (e.g., "python", "java", "javascript")
- `mission` (string): Project mission (e.g., "learning", "tool", "documentation")
- `level` (string, optional): Difficulty level ("beginner", "intermediate", "advanced")
- `type` (string, optional): Project type ("tool", "documentation", "training", etc.)
- `contribution_type` (string, optional): Type of contribution ("code", "documentation", "research")
- `top_n` (integer, optional): Number of recommendations to return (default: 3)

**Response:**
```json
{
  "ok": true,
  "approach": "technology",
  "criteria": {
    "technology": "python",
    "level": "beginner"
  },
  "recommendations": [
    {
      "name": "PyGoat",
      "description": "Python vulnerable web application for learning",
      "url": "https://github.com/OWASP/www-project-pygoat",
      "technologies": ["python"],
      "missions": ["learning", "vulnerable-app"],
      "level": "beginner",
      "type": "vulnerable-app"
    }
  ]
}
```

### Example Usage

**Technology-based recommendations:**
```bash
curl -X POST https://your-worker.workers.dev/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "approach": "technology",
    "technology": "python",
    "level": "beginner",
    "top_n": 3
  }'
```

**Mission-based recommendations:**
```bash
curl -X POST https://your-worker.workers.dev/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "approach": "mission",
    "mission": "learning",
    "top_n": 5
  }'
```

**Get available categories:**
```bash
curl https://your-worker.workers.dev/projects
```
