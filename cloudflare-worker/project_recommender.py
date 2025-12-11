"""
Project recommendation engine for OWASP projects.

This module provides filtering and ranking logic for recommending OWASP projects
based on technology, mission, difficulty level, and other criteria.
"""

from typing import Any


class ProjectRecommender:
    """Recommends OWASP projects based on user preferences."""

    def __init__(self, projects_data: dict[str, Any]):
        """Initialize with projects metadata."""
        self.projects = projects_data.get("projects", [])
        self.technologies = projects_data.get("technologies", [])
        self.missions = projects_data.get("missions", [])
        self.levels = projects_data.get("levels", ["beginner", "intermediate", "advanced"])

    def filter_by_technology(self, technology: str) -> list[dict[str, Any]]:
        """Filter projects by technology stack."""
        technology = technology.lower()
        return [
            proj
            for proj in self.projects
            if technology in [t.lower() for t in proj.get("technologies", [])]
        ]

    def filter_by_mission(self, mission: str) -> list[dict[str, Any]]:
        """Filter projects by mission/purpose."""
        mission = mission.lower()
        return [
            proj
            for proj in self.projects
            if mission in [m.lower() for m in proj.get("missions", [])]
        ]

    def filter_by_level(self, level: str) -> list[dict[str, Any]]:
        """Filter projects by difficulty level."""
        level = level.lower()
        return [proj for proj in self.projects if proj.get("level", "").lower() == level]

    def filter_by_type(self, project_type: str) -> list[dict[str, Any]]:
        """Filter projects by type (tool, documentation, training, etc.)."""
        project_type = project_type.lower()
        return [proj for proj in self.projects if proj.get("type", "").lower() == project_type]

    def search_by_keyword(self, keyword: str) -> list[dict[str, Any]]:
        """Search projects by keyword in name or description."""
        keyword = keyword.lower()
        return [
            proj
            for proj in self.projects
            if keyword in proj.get("name", "").lower()
            or keyword in proj.get("description", "").lower()
        ]

    def rank_projects(
        self,
        projects: list[dict[str, Any]],
        preferences: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rank projects based on relevance and other factors.

        Scoring factors:
        - Exact match on technology/mission (higher weight)
        - Multiple matching criteria
        - Beginner-friendly projects get bonus for learning mission
        - Well-described projects rank higher
        """
        if not preferences:
            preferences = {}

        scored_projects = []
        for proj in projects:
            score = 0

            # Base score
            score += 10

            # Technology match bonus
            if preferences.get("technology"):
                tech = preferences["technology"].lower()
                if tech in [t.lower() for t in proj.get("technologies", [])]:
                    score += 50

            # Mission match bonus
            if preferences.get("mission"):
                mission = preferences["mission"].lower()
                if mission in [m.lower() for m in proj.get("missions", [])]:
                    score += 50

            # Level match bonus
            if preferences.get("level"):
                level = preferences["level"].lower()
                if proj.get("level", "").lower() == level:
                    score += 30

            # Type match bonus
            if preferences.get("type"):
                ptype = preferences["type"].lower()
                if proj.get("type", "").lower() == ptype:
                    score += 20

            # Beginner bonus for learning mission
            if (
                "learning" in proj.get("missions", [])
                and proj.get("level") == "beginner"
            ):
                score += 15

            # Well-described projects
            if proj.get("description") and len(proj["description"]) > 50:
                score += 10

            # Multiple technologies/missions (versatility bonus)
            score += len(proj.get("technologies", [])) * 2
            score += len(proj.get("missions", [])) * 2

            scored_projects.append({"project": proj, "score": score})

        # Sort by score descending
        scored_projects.sort(key=lambda x: x["score"], reverse=True)

        return [item["project"] for item in scored_projects]

    def recommend_by_technology(
        self,
        technology: str,
        level: str | None = None,
        project_type: str | None = None,
        top_n: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Recommend projects based on technology preference.

        Args:
            technology: Technology stack (python, java, javascript, etc.)
            level: Optional difficulty level filter
            project_type: Optional project type filter
            top_n: Number of recommendations to return

        Returns:
            List of recommended projects
        """
        # Start with technology filter
        candidates = self.filter_by_technology(technology)

        # Apply additional filters
        if level:
            candidates = [proj for proj in candidates if proj.get("level") == level]

        if project_type:
            candidates = [proj for proj in candidates if proj.get("type") == project_type]

        # Rank and return top N
        preferences = {"technology": technology, "level": level, "type": project_type}
        ranked = self.rank_projects(candidates, preferences)

        return ranked[:top_n]

    def recommend_by_mission(
        self,
        mission: str,
        contribution_type: str | None = None,
        top_n: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Recommend projects based on mission/goal.

        Args:
            mission: Mission/goal (learning, tool, documentation, etc.)
            contribution_type: Optional contribution type preference
            top_n: Number of recommendations to return

        Returns:
            List of recommended projects
        """
        # Start with mission filter
        candidates = self.filter_by_mission(mission)

        # Map contribution type to project type
        if contribution_type:
            type_mapping = {
                "code": "tool",
                "documentation": "documentation",
                "research": "standard",
                "training": "training",
            }
            mapped_type = type_mapping.get(contribution_type.lower())
            if mapped_type:
                candidates = [proj for proj in candidates if proj.get("type") == mapped_type]

        # Rank and return top N
        preferences = {"mission": mission, "type": contribution_type}
        ranked = self.rank_projects(candidates, preferences)

        return ranked[:top_n]

    def get_fallback_recommendations(self, top_n: int = 3) -> list[dict[str, Any]]:
        """
        Get fallback recommendations for low-confidence scenarios.

        Returns popular and beginner-friendly projects.
        """
        # Prioritize beginner-friendly learning projects
        beginner_learning = [
            proj
            for proj in self.projects
            if proj.get("level") == "beginner" and "learning" in proj.get("missions", [])
        ]

        # Add popular vulnerable apps for practice
        vulnerable_apps = [
            proj for proj in self.projects if proj.get("type") == "vulnerable-app"
        ]

        # Combine and rank
        candidates = beginner_learning + vulnerable_apps
        preferences = {"mission": "learning", "level": "beginner"}
        ranked = self.rank_projects(candidates, preferences)

        return ranked[:top_n]

    def format_recommendation(self, project: dict[str, Any]) -> str:
        """Format a project recommendation as markdown text."""
        name = project.get("name", "Unknown Project")
        description = project.get("description", "No description available")
        url = project.get("url", "")
        technologies = ", ".join(project.get("technologies", []))
        level = project.get("level", "intermediate").capitalize()

        text = f"**{name}**\n"
        text += f"_{description}_\n"
        if technologies:
            text += f"• Tech: {technologies}\n"
        text += f"• Level: {level}\n"
        text += f"• Link: {url}\n"

        return text


def load_projects_metadata() -> dict[str, Any]:
    """Load projects metadata from JSON file."""
    import json
    from pathlib import Path

    metadata_file = Path(__file__).parent.parent / "data" / "projects_metadata.json"

    try:
        with open(metadata_file, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Return empty structure if file doesn't exist
        return {
            "projects": [],
            "technologies": [],
            "missions": [],
            "levels": ["beginner", "intermediate", "advanced"],
        }
