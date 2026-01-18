"""
Project Recommendation Engine
Filters and ranks OWASP projects based on user preferences
"""
import json
import os
from typing import List, Dict, Optional


class ProjectRecommender:
    """Recommends OWASP projects based on user criteria"""
    
    def __init__(self, projects_data_path: str):
        """Initialize with projects data"""
        with open(projects_data_path, 'r', encoding='utf-8') as f:
            self.projects = json.load(f)
    
    def recommend_tech_based(
        self, 
        technology: str, 
        difficulty: str, 
        project_type: str
    ) -> List[Dict[str, str]]:
        """
        Recommend projects based on technology preferences
        
        Args:
            technology: Technology stack (python, java, javascript, etc.)
            difficulty: Difficulty level (beginner, intermediate, advanced)
            project_type: Type of project (tools, code, documentation, training)
        
        Returns:
            List of recommended projects with name, description, and URL
        """
        recommendations = []
        
        # Keywords mapping for filtering
        tech_keywords = {
            'python': ['python', 'py', 'flask', 'django'],
            'java': ['java', 'spring', 'maven'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
            'mobile': ['mobile', 'android', 'ios', 'swift', 'kotlin'],
            'cloud': ['cloud', 'kubernetes', 'docker', 'container'],
            'devsecops': ['devsecops', 'cicd', 'pipeline', 'security']
        }
        
        type_keywords = {
            'tools': ['tool', 'scanner', 'analyzer', 'detector'],
            'code': ['library', 'framework', 'api'],
            'documentation': ['guide', 'standard', 'cheat', 'top'],
            'training': ['training', 'workshop', 'learning', 'vulnerable', 'dvwa', 'juice']
        }
        
        # Well-known projects for each category
        recommended_projects = {
            'python_beginner': ['juice-shop', 'pytm', 'security-shepherd'],
            'python_tools': ['zap', 'dependency-check', 'amass'],
            'java_beginner': ['webgoat', 'security-shepherd'],
            'javascript_beginner': ['juice-shop', 'nodejsscan'],
            'training': ['juice-shop', 'webgoat', 'security-shepherd', 'dvwa']
        }
        
        # Search keywords
        search_keywords = tech_keywords.get(technology, []) + type_keywords.get(project_type, [])
        
        # Filter projects
        for project_key, project_info in self.projects.items():
            project_name = project_key.lower()
            description = project_info[0].lower() if len(project_info) > 0 else ""
            url = project_info[1] if len(project_info) > 1 else ""
            
            # Check if project matches criteria
            matches = False
            for keyword in search_keywords:
                if keyword in project_name or keyword in description:
                    matches = True
                    break
            
            # Check recommended lists
            for rec_key, rec_projects in recommended_projects.items():
                if technology in rec_key or project_type in rec_key:
                    for rec_proj in rec_projects:
                        if rec_proj in project_name:
                            matches = True
                            break
            
            if matches:
                recommendations.append({
                    'name': self._format_project_name(project_key),
                    'description': project_info[0] if len(project_info) > 0 else "OWASP Project",
                    'url': url,
                    'key': project_key
                })
        
        # Rank by relevance and popularity
        ranked = self._rank_projects(recommendations, technology, difficulty, project_type)
        
        # Return top 3
        return ranked[:3]
    
    def recommend_mission_based(
        self,
        goal: str,
        contribution_type: str
    ) -> List[Dict[str, str]]:
        """
        Recommend projects based on mission/goal
        
        Args:
            goal: User's goal (learn, code, docs, gsoc, research, devsecops)
            contribution_type: Type of contribution (code, documentation, design, research)
        
        Returns:
            List of recommended projects
        """
        recommendations = []
        
        # Mission-based keywords
        goal_keywords = {
            'learn': ['juice', 'webgoat', 'shepherd', 'vulnerable', 'training', 'workshop'],
            'code': ['zap', 'dependency', 'amass', 'scanner'],
            'docs': ['top', 'guide', 'standard', 'cheat', 'best-practice'],
            'gsoc': ['zap', 'juice', 'dependency-check', 'webgoat'],
            'research': ['threat', 'model', 'risk', 'analysis'],
            'devsecops': ['devsecops', 'cicd', 'pipeline', 'integration']
        }
        
        search_keywords = goal_keywords.get(goal, [])
        
        for project_key, project_info in self.projects.items():
            project_name = project_key.lower()
            description = project_info[0].lower() if len(project_info) > 0 else ""
            url = project_info[1] if len(project_info) > 1 else ""
            
            matches = False
            for keyword in search_keywords:
                if keyword in project_name or keyword in description:
                    matches = True
                    break
            
            if matches:
                recommendations.append({
                    'name': self._format_project_name(project_key),
                    'description': project_info[0] if len(project_info) > 0 else "OWASP Project",
                    'url': url,
                    'key': project_key
                })
        
        # Rank by mission relevance
        ranked = self._rank_projects(recommendations, goal, None, contribution_type)
        
        return ranked[:3]
    
    def _rank_projects(
        self,
        projects: List[Dict[str, str]],
        primary_criteria: str,
        secondary_criteria: Optional[str],
        tertiary_criteria: str
    ) -> List[Dict[str, str]]:
        """Rank projects by relevance"""
        # Simple ranking based on well-known projects
        priority_projects = [
            'juice-shop', 'zap', 'webgoat', 'dependency-check', 
            'security-shepherd', 'amass', 'top-ten', 'cheat-sheet'
        ]
        
        def get_score(project):
            score = 0
            key = project['key'].lower()
            
            # Higher score for well-known projects
            for i, priority in enumerate(priority_projects):
                if priority in key:
                    score += (len(priority_projects) - i) * 10
            
            # Boost score for criteria match
            if primary_criteria and primary_criteria in key:
                score += 20
            if secondary_criteria and secondary_criteria in key:
                score += 10
            if tertiary_criteria and tertiary_criteria in key:
                score += 5
                
            return score
        
        # Sort by score descending
        return sorted(projects, key=get_score, reverse=True)
    
    def _format_project_name(self, project_key: str) -> str:
        """Format project key into readable name"""
        # Remove 'www-project-' prefix
        name = project_key.replace('www-project-', '')
        # Replace hyphens with spaces and title case
        name = name.replace('-', ' ').title()
        return f"OWASP {name}"


def format_recommendations_message(
    recommendations: List[Dict[str, str]],
    user_choices: Dict[str, str]
) -> dict:
    """Format recommendations into Slack message blocks"""
    
    if not recommendations:
        return {
            "text": "No projects found",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "😕 *No matching projects found*\n\nTry different criteria or browse all OWASP projects at https://owasp.org/projects/"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🔄 Start Over"},
                            "value": "restart",
                            "action_id": "restart_conversation"
                        }
                    ]
                }
            ]
        }
    
    # Build message
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🎉 *Here are your recommended OWASP projects:*"
            }
        }
    ]
    
    # Add each recommendation
    for i, project in enumerate(recommendations, 1):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i}. {project['name']}*\n{project['description']}\n🔗 <{project['url']}|View Project>"
            }
        })
        blocks.append({"type": "divider"})
    
    # Add follow-up actions
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "💡 *Want to get started contributing?*\nCheck out the contributing guidelines or ask me anything else!"
        }
    })
    
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔄 Find More Projects"},
                "value": "restart",
                "action_id": "restart_conversation"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Done"},
                "value": "done",
                "action_id": "end_conversation"
            }
        ]
    })
    
    return {
        "text": "Here are your recommended projects",
        "blocks": blocks
    }
