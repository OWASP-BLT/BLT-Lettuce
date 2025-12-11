#!/usr/bin/env python3
"""
Example script demonstrating project recommendations.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "cloudflare-worker"))
from project_recommender import ProjectRecommender, load_projects_metadata


def print_recommendations(title: str, recommendations: list):
    """Print formatted recommendations."""
    print(f"\n{'=' * 70}")
    print(f"{title}")
    print(f"{'=' * 70}\n")

    if not recommendations:
        print("No recommendations found.")
        return

    for i, proj in enumerate(recommendations, 1):
        print(f"{i}. **{proj['name']}**")
        desc = proj['description'][:100] if proj['description'] else "N/A"
        print(f"   Description: {desc}...")
        print(f"   Technologies: {', '.join(proj['technologies']) or 'N/A'}")
        print(f"   Level: {proj['level']}")
        print(f"   URL: {proj['url']}")
        print()


def main():
    """Run example recommendations."""
    print("Loading OWASP projects metadata...")
    metadata = load_projects_metadata()

    if not metadata.get("projects"):
        print("Error: No projects found.")
        return 1

    print(f"Loaded {metadata['total_projects']} projects")
    recommender = ProjectRecommender(metadata)

    # Example 1: Python projects for beginners
    print_recommendations(
        "Example 1: Python Projects for Beginners",
        recommender.recommend_by_technology("python", level="beginner", top_n=3),
    )

    # Example 2: Learning projects
    print_recommendations(
        "Example 2: Projects for Learning",
        recommender.recommend_by_mission("learning", top_n=5),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
