#!/usr/bin/env python3
"""
Fetch OWASP projects from GitHub and extract metadata from index.md files.

This script:
1. Fetches all www-project-* repositories from github.com/OWASP
2. Downloads and parses index.md files from each repository
3. Extracts tags, project type, level, and description
4. Generates an enriched projects.json file with full metadata
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# Configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_ORG = "OWASP"
PROJECT_PREFIX = "www-project-"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "projects_metadata.json"
REQUEST_TIMEOUT = 30
GITHUB_TOKEN = None  # Set via environment variable if needed

# Headers for GitHub API requests
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "BLT-Lettuce-Bot/1.0 (+https://github.com/OWASP-BLT/BLT-Lettuce)",
}


def get_headers():
    """Get headers with optional GitHub token."""
    headers = HEADERS.copy()
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def fetch_owasp_repositories():
    """Fetch all OWASP repositories starting with www-project-."""
    print(f"Fetching repositories from {GITHUB_ORG}...")
    repos = []
    page = 1
    per_page = 100

    while True:
        url = f"{GITHUB_API_BASE}/orgs/{GITHUB_ORG}/repos"
        params = {"per_page": per_page, "page": page, "type": "public"}

        response = requests.get(url, headers=get_headers(), params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        page_repos = response.json()
        if not page_repos:
            break

        # Filter for www-project-* repos
        project_repos = [repo for repo in page_repos if repo["name"].startswith(PROJECT_PREFIX)]
        repos.extend(project_repos)

        print(f"  Page {page}: Found {len(project_repos)} project repos")
        page += 1

        # Stop if we've processed all repos
        if len(page_repos) < per_page:
            break

    print(f"Total project repositories found: {len(repos)}")
    return repos


def fetch_file_content(repo_name: str, file_path: str) -> str | None:
    """Fetch content of a file from a GitHub repository."""
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_ORG}/{repo_name}/contents/{file_path}"

    try:
        response = requests.get(url, headers=get_headers(), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        if "content" in data:
            import base64

            return base64.b64decode(data["content"]).decode("utf-8")
    except (requests.RequestException, KeyError, ValueError):
        pass

    return None


def parse_yaml_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from markdown content."""
    frontmatter = {}

    # Match YAML frontmatter between --- delimiters
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return frontmatter

    yaml_content = match.group(1)

    # Parse key-value pairs (simple YAML parser)
    for line in yaml_content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Handle key: value format
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes
            value = value.strip('"').strip("'")

            # Handle lists
            if value.startswith("[") and value.endswith("]"):
                # Parse simple list format
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
            elif not value and key:
                # Multi-line list format
                continue

            frontmatter[key] = value

    return frontmatter


def extract_tags_from_content(content: str) -> list[str]:
    """Extract tags from markdown content."""
    tags = []

    # Look for tag-like patterns in the content
    tag_patterns = [
        r"tags?:\s*\[(.*?)\]",
        r"tags?:\s*([^\n]+)",
        r"#\s*([\w-]+)",
    ]

    for pattern in tag_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str):
                # Split by comma and clean up
                tag_list = [tag.strip().strip('"').strip("'") for tag in match.split(",")]
                tags.extend([tag for tag in tag_list if tag and len(tag) < 50])

    return list(set(tags))


def categorize_by_technology(tags: list[str], description: str) -> list[str]:
    """Categorize project by technology stack."""
    tech_keywords = {
        "python": ["python", "django", "flask", "fastapi"],
        "java": ["java", "spring", "maven", "gradle"],
        "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
        "typescript": ["typescript", "ts"],
        "go": ["go", "golang"],
        "rust": ["rust"],
        "ruby": ["ruby", "rails"],
        "php": ["php", "laravel", "wordpress"],
        "dotnet": [".net", "c#", "csharp", "dotnet"],
        "mobile": ["android", "ios", "mobile", "swift", "kotlin"],
        "cloud": ["cloud", "aws", "azure", "gcp", "kubernetes", "docker"],
        "web": ["web", "html", "css", "frontend", "backend"],
        "security": ["security", "owasp", "appsec", "devsecops", "pentest"],
    }

    text = " ".join(tags).lower() + " " + description.lower()
    technologies = []

    for tech, keywords in tech_keywords.items():
        if any(keyword in text for keyword in keywords):
            technologies.append(tech)

    return technologies


def categorize_by_mission(tags: list[str], description: str) -> list[str]:
    """Categorize project by mission/goal."""
    mission_keywords = {
        "learning": ["learn", "training", "education", "tutorial", "guide", "academy"],
        "tool": ["tool", "scanner", "analyzer", "framework", "library"],
        "documentation": ["documentation", "docs", "guide", "handbook", "manual"],
        "vulnerable-app": ["vulnerable", "goat", "juice", "dvwa", "ctf", "challenge"],
        "testing": ["testing", "test", "verification", "validation"],
        "standard": ["standard", "top-10", "verification", "maturity"],
        "research": ["research", "analysis", "study"],
        "community": ["community", "chapter", "meetup"],
    }

    text = " ".join(tags).lower() + " " + description.lower()
    missions = []

    for mission, keywords in mission_keywords.items():
        if any(keyword in text for keyword in keywords):
            missions.append(mission)

    return missions


def determine_difficulty_level(repo_data: dict, description: str) -> str:
    """Determine project difficulty level."""
    text = description.lower()

    # Beginner indicators
    if any(
        keyword in text
        for keyword in ["beginner", "learning", "tutorial", "starter", "introduction", "basic"]
    ):
        return "beginner"

    # Advanced indicators
    if any(
        keyword in text
        for keyword in [
            "advanced",
            "expert",
            "enterprise",
            "complex",
            "professional",
            "production",
        ]
    ):
        return "advanced"

    # Check stars/forks as proxy for complexity
    stars = repo_data.get("stargazers_count", 0)
    if stars > 1000:
        return "intermediate"
    elif stars > 100:
        return "beginner"

    return "intermediate"


def process_repository(repo: dict) -> dict[str, Any]:
    """Process a single repository and extract metadata."""
    repo_name = repo["name"]
    print(f"Processing {repo_name}...")

    # Fetch index.md
    index_content = fetch_file_content(repo_name, "index.md")
    if not index_content:
        index_content = fetch_file_content(repo_name, "README.md")

    # Extract metadata
    metadata = {
        "name": repo_name,
        "full_name": repo["full_name"],
        "url": repo["html_url"],
        "description": repo.get("description", ""),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "language": repo.get("language", ""),
        "last_updated": repo.get("updated_at", ""),
        "created_at": repo.get("created_at", ""),
        "is_archived": repo.get("archived", False),
        "tags": [],
        "technologies": [],
        "missions": [],
        "level": "intermediate",
        "project_type": "unknown",
        "pitch": "",
    }

    if index_content:
        # Parse frontmatter
        frontmatter = parse_yaml_frontmatter(index_content)

        # Extract tags
        tags = []
        if "tags" in frontmatter:
            tag_value = frontmatter["tags"]
            if isinstance(tag_value, list):
                tags = tag_value
            elif isinstance(tag_value, str):
                tags = [t.strip() for t in tag_value.split(",")]

        # Also extract tags from content
        content_tags = extract_tags_from_content(index_content)
        tags.extend(content_tags)

        metadata["tags"] = list(set(tags))

        # Extract project type
        if "type" in frontmatter:
            metadata["project_type"] = frontmatter["type"]
        elif "level" in frontmatter:
            metadata["level"] = frontmatter["level"]

        # Extract pitch/description from content
        # Remove frontmatter and get first paragraph
        content_no_fm = re.sub(r"^---\s*\n.*?\n---\s*\n", "", index_content, flags=re.DOTALL)
        paragraphs = [p.strip() for p in content_no_fm.split("\n\n") if p.strip()]
        if paragraphs:
            # Get first substantial paragraph (more than 50 chars)
            for para in paragraphs[:3]:
                # Remove markdown formatting
                clean_para = re.sub(r"[#*`\[\]]", "", para)
                if len(clean_para) > 50:
                    metadata["pitch"] = clean_para[:500]
                    break

    # Use description as fallback pitch
    if not metadata["pitch"] and metadata["description"]:
        metadata["pitch"] = metadata["description"]

    # Categorize
    text_for_categorization = (
        " ".join(metadata["tags"])
        + " "
        + metadata["description"]
        + " "
        + metadata["pitch"]
    )
    metadata["technologies"] = categorize_by_technology(
        metadata["tags"], text_for_categorization
    )
    metadata["missions"] = categorize_by_mission(metadata["tags"], text_for_categorization)
    metadata["level"] = determine_difficulty_level(repo, text_for_categorization)

    return metadata


def save_metadata(projects: list[dict[str, Any]]):
    """Save project metadata to JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_projects": len(projects),
        "projects": projects,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nMetadata saved to {OUTPUT_FILE}")


def main():
    """Main entry point."""
    try:
        # Fetch all OWASP project repositories
        repos = fetch_owasp_repositories()

        # Process each repository
        projects = []
        for repo in repos:
            try:
                metadata = process_repository(repo)
                projects.append(metadata)
            except Exception as e:
                print(f"  Error processing {repo['name']}: {e}")
                continue

        # Save metadata
        save_metadata(projects)

        print(f"\nSuccessfully processed {len(projects)} projects!")
        return 0

    except requests.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
