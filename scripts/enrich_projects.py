#!/usr/bin/env python3
"""
Enrich existing projects.json with metadata for categorization.

This script processes the existing projects.json file and adds:
- Technology categorization (Python, Java, JS, Mobile, Cloud, etc.)
- Mission categorization (Learning, Tools, Documentation, Testing, etc.)
- Difficulty level (Beginner, Intermediate, Advanced)
- Project type classification
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Configuration
INPUT_FILE = Path(__file__).parent.parent / "data" / "projects.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "projects_metadata.json"


def categorize_by_technology(name: str, description: str) -> list[str]:
    """Categorize project by technology stack based on name and description."""
    tech_keywords = {
        "python": ["python", "pytm", "pygoat", "nettacker", "securetea"],
        "java": ["java", "webgoat", "zap", "dependency-check", "benchmark"],
        "javascript": [
            "javascript",
            "js",
            "node",
            "react",
            "juice-shop",
            "vue",
            "angular",
        ],
        "go": ["go", "golang"],
        "rust": ["rust"],
        "ruby": ["ruby", "rails"],
        "php": ["php", "webgoat-php"],
        "dotnet": [".net", "c#", "csharp", "dotnet"],
        "mobile": ["android", "ios", "mobile", "igoat", "androgoat"],
        "cloud": ["cloud", "aws", "azure", "gcp", "kubernetes", "docker", "serverless"],
        "web": ["web", "html", "css", "frontend", "backend"],
        "devsecops": ["devsecops", "pipeline", "cicd", "ci-cd"],
        "api": ["api", "rest", "graphql"],
        "threat-modeling": ["threat", "dragon", "model"],
    }

    text = (name + " " + description).lower()
    technologies = []

    for tech, keywords in tech_keywords.items():
        if any(keyword in text for keyword in keywords):
            technologies.append(tech)

    return technologies


def categorize_by_mission(name: str, description: str) -> list[str]:
    """Categorize project by mission/purpose."""
    mission_keywords = {
        "learning": [
            "learn",
            "training",
            "education",
            "tutorial",
            "guide",
            "academy",
            "dojo",
            "shepherd",
        ],
        "tool": [
            "tool",
            "scanner",
            "analyzer",
            "framework",
            "library",
            "zap",
            "amass",
            "nettacker",
        ],
        "documentation": [
            "documentation",
            "docs",
            "guide",
            "handbook",
            "manual",
            "cheat-sheet",
            "testing-guide",
        ],
        "vulnerable-app": [
            "vulnerable",
            "goat",
            "juice",
            "dvwa",
            "dvsa",
            "webgoat",
            "nodegoat",
        ],
        "ctf": ["ctf", "challenge", "hackademic", "game"],
        "testing": ["testing", "test", "verification", "validation", "pentest"],
        "standard": ["standard", "top-10", "top-ten", "verification", "maturity", "samm", "asvs"],
        "research": ["research", "analysis", "study"],
        "security-tool": ["security", "scanner", "detector", "audit", "analyzer"],
    }

    text = (name + " " + description).lower()
    missions = []

    for mission, keywords in mission_keywords.items():
        if any(keyword in text for keyword in keywords):
            missions.append(mission)

    # Default to 'tool' if it mentions specific security functionality
    if not missions and any(
        word in text for word in ["scan", "detect", "protect", "security", "firewall"]
    ):
        missions.append("security-tool")

    return missions


def determine_difficulty_level(name: str, description: str) -> str:
    """Determine project difficulty level based on name and description."""
    text = (name + " " + description).lower()

    # Beginner indicators
    beginner_keywords = [
        "beginner",
        "learning",
        "tutorial",
        "starter",
        "introduction",
        "basic",
        "juice",
        "webgoat",
        "training",
        "education",
        "guide",
    ]
    if any(keyword in text for keyword in beginner_keywords):
        return "beginner"

    # Advanced indicators
    advanced_keywords = [
        "advanced",
        "expert",
        "enterprise",
        "framework",
        "professional",
        "production",
        "maturity",
        "verification-standard",
    ]
    if any(keyword in text for keyword in advanced_keywords):
        return "advanced"

    return "intermediate"


def determine_project_type(name: str, description: str, missions: list[str]) -> str:
    """Determine the type of project."""
    text = (name + " " + description).lower()

    if "vulnerable-app" in missions or "ctf" in missions:
        return "vulnerable-app"
    elif "tool" in missions or "security-tool" in missions:
        return "tool"
    elif "documentation" in missions:
        return "documentation"
    elif "standard" in missions:
        return "standard"
    elif "learning" in missions:
        return "training"

    # Fallback patterns
    if any(word in text for word in ["guide", "handbook", "documentation"]):
        return "documentation"
    elif any(word in text for word in ["tool", "scanner", "framework"]):
        return "tool"
    elif any(word in text for word in ["training", "learning", "tutorial"]):
        return "training"

    return "project"


def enrich_project(project_key: str, project_data: list[str]) -> dict[str, Any]:
    """Enrich a single project with metadata."""
    description = project_data[0] if len(project_data) > 0 else ""
    url = project_data[1] if len(project_data) > 1 else ""

    # Extract project name from key (remove www-project- prefix)
    display_name = project_key.replace("www-project-", "").replace("-", " ").title()

    # Categorize
    technologies = categorize_by_technology(project_key, description)
    missions = categorize_by_mission(project_key, description)
    level = determine_difficulty_level(project_key, description)
    project_type = determine_project_type(project_key, description, missions)

    return {
        "id": project_key,
        "name": display_name,
        "description": description,
        "url": url,
        "technologies": technologies,
        "missions": missions,
        "level": level,
        "type": project_type,
        "tags": technologies + missions,  # Combined for easier searching
    }


def main():
    """Main entry point."""
    try:
        print(f"Reading projects from {INPUT_FILE}...")

        # Load existing projects.json
        with open(INPUT_FILE, encoding="utf-8") as f:
            projects = json.load(f)

        print(f"Found {len(projects)} projects")
        print("Enriching projects with metadata...")

        # Enrich each project
        enriched_projects = []
        for project_key, project_data in projects.items():
            try:
                enriched = enrich_project(project_key, project_data)
                enriched_projects.append(enriched)
            except Exception as e:
                print(f"  Error processing {project_key}: {e}")
                continue

        # Create output with metadata
        output_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_projects": len(enriched_projects),
            "projects": enriched_projects,
            "technologies": list(
                set(tech for proj in enriched_projects for tech in proj["technologies"])
            ),
            "missions": list(
                set(mission for proj in enriched_projects for mission in proj["missions"])
            ),
            "levels": ["beginner", "intermediate", "advanced"],
            "types": list(set(proj["type"] for proj in enriched_projects)),
        }

        # Sort technologies and missions for better readability
        output_data["technologies"].sort()
        output_data["missions"].sort()
        output_data["types"].sort()

        # Save enriched metadata
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        print(f"\nEnriched metadata saved to {OUTPUT_FILE}")
        print(f"Total projects: {output_data['total_projects']}")
        print(f"Technologies: {', '.join(output_data['technologies'])}")
        print(f"Missions: {', '.join(output_data['missions'])}")
        print(f"Project types: {', '.join(output_data['types'])}")

        return 0

    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found", file=__import__("sys").stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
