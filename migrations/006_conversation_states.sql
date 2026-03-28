-- Migration: Add conversation_states table for Slack DM flowchart conversations

CREATE TABLE IF NOT EXISTS conversation_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    user_slack_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    step TEXT NOT NULL DEFAULT 'start',
    answers_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, user_slack_id)
);

CREATE INDEX IF NOT EXISTS idx_conv_states_workspace_user
ON conversation_states(workspace_id, user_slack_id);
