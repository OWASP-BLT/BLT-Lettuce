-- Migration: Create Slack Bot Activity and Chat Bot Log tables
-- Date: 2026-02-23

CREATE TABLE IF NOT EXISTS slack_bot_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    workspace_name TEXT,
    activity_type TEXT NOT NULL,
    user_id TEXT,
    username TEXT,
    details TEXT, -- JSON string
    success INTEGER DEFAULT 1, -- 0 for false, 1 for true
    error_message TEXT,
    created DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_slack_activity_workspace ON slack_bot_activity(workspace_id);
CREATE INDEX IF NOT EXISTS idx_slack_activity_type ON slack_bot_activity(activity_type);
CREATE INDEX IF NOT EXISTS idx_slack_activity_created ON slack_bot_activity(created);

CREATE TABLE IF NOT EXISTS chat_bot_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created DATETIME DEFAULT CURRENT_TIMESTAMP
);
