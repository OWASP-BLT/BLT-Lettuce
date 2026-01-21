# Project Recommendation System Implementation

This document describes how the project recommendation system implements the flowchart defined in `slack-bot-flowchart.md`.

## Overview

The recommendation system provides two primary approaches for discovering OWASP projects:
1. **Technology-based**: Filter projects by programming language or technology stack
2. **Mission-based**: Filter projects by goal or purpose

## Architecture

### Components

1. **Data Layer** (`data/projects_metadata.json`)
   - Enriched metadata for 338 OWASP projects
   - Categorized by technologies, missions, levels, and types
   - Generated from existing `projects.json` with enhanced metadata

2. **Recommendation Engine** (`cloudflare-worker/project_recommender.py`)
   - `ProjectRecommender` class with filtering and ranking logic
   - Technology-based and mission-based recommendation methods
   - Fallback recommendations for low-confidence scenarios

3. **API Endpoints** (`cloudflare-worker/worker.py`)
   - `GET /projects` - List available categories
   - `POST /recommend` - Get personalized recommendations

## Implementation Mapping to Flowchart

### Technology-Based Path (Left Branch)

**Step 1: Ask Technology**
```python
# API Call
POST /recommend
{
  "approach": "technology",
  "technology": "python"
}
```

**Step 2: Ask Difficulty**
```python
# API Call with level filter
POST /recommend
{
  "approach": "technology",
  "technology": "python",
  "level": "beginner"
}
```

**Step 3: Ask Project Type**
```python
# API Call with type filter
POST /recommend
{
  "approach": "technology",
  "technology": "python",
  "level": "beginner",
  "type": "tool"
}
```

**Step 4-5: Metadata Filtering & Ranking**
- Filters applied automatically by `recommend_by_technology()`
- Ranking considers:
  - Exact technology match (50 points)
  - Level match (30 points)
  - Type match (20 points)
  - Beginner-friendly bonus (15 points)
  - Description quality (10 points)

### Mission-Based Path (Right Branch)

**Step 1: Ask Mission**
```python
# API Call
POST /recommend
{
  "approach": "mission",
  "mission": "learning"
}
```

**Step 2: Ask Contribution Type**
```python
# API Call with contribution type
POST /recommend
{
  "approach": "mission",
  "mission": "learning",
  "contribution_type": "code"
}
```

**Step 3-4: Metadata Filtering & Ranking**
- Filters applied automatically by `recommend_by_mission()`
- Ranking considers:
  - Mission match (50 points)
  - Contribution type match (20 points)
  - Multiple matching criteria bonus

### Fallback Logic

When no specific criteria are provided or results are empty:
```python
# Automatic fallback
recommendations = recommender.get_fallback_recommendations(top_n=3)
```

Returns:
- Beginner-friendly learning projects
- Popular vulnerable applications for practice
- Well-documented starter projects

## Available Categories

### Technologies
- **Languages**: python, java, javascript, go, rust, ruby, php, dotnet
- **Platforms**: mobile (Android/iOS), web, cloud, api
- **Focus Areas**: devsecops, threat-modeling

### Missions
- **Learning**: learning, ctf, vulnerable-app
- **Tools**: tool, security-tool, testing
- **Knowledge**: documentation, standard, research

### Levels
- beginner
- intermediate
- advanced

### Project Types
- tool
- documentation
- training
- vulnerable-app
- standard
- project

## Example Workflow

### Scenario 1: New Developer Learning Python

```bash
# Step 1: Technology preference
curl -X POST /recommend -d '{"approach":"technology","technology":"python"}'

# Step 2: Filter by beginner level
curl -X POST /recommend -d '{"approach":"technology","technology":"python","level":"beginner"}'

# Step 3: Get vulnerable apps for practice
curl -X POST /recommend -d '{"approach":"technology","technology":"python","level":"beginner","type":"vulnerable-app"}'
```

**Result**: PyGoat, Python Honeypot, and similar beginner-friendly Python projects

### Scenario 2: Security Professional Learning Cloud Security

```bash
# Mission-based approach
curl -X POST /recommend -d '{"approach":"mission","mission":"learning"}'

# Add cloud technology filter
curl -X POST /recommend -d '{"approach":"technology","technology":"cloud","mission":"learning"}'
```

**Result**: Cloud Security Testing Guide, Kubernetes Top Ten, Cloud Native Security projects

## Testing

Run the test suite:
```bash
python3 -m pytest tests/test_project_recommender.py -v
```

Run example demonstrations:
```bash
python3 examples/recommend_projects.py
```

## Future Enhancements

1. **Interactive Conversation Flow**
   - Multi-step filtering in Slack conversations
   - Natural language processing for user intent
   - Context-aware follow-up questions

2. **Enhanced Metadata**
   - Fetch real-time data from GitHub (stars, activity, contributors)
   - Parse index.md files from project repositories
   - Extract tags from project frontmatter

3. **Personalization**
   - User preference history
   - Activity-based recommendations
   - Collaborative filtering

4. **Analytics**
   - Track recommendation effectiveness
   - Popular project categories
   - User engagement metrics
