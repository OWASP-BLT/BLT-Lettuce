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
        project_type: str,
        limit: int = 3
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
            'python': ['python', 'py', 'flask', 'django', 'blt', 'api'],
            'java': ['java', 'spring', 'maven'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', 'typescript'],
            'mobile': ['mobile', 'android', 'ios', 'swift', 'kotlin', 'dart', 'flutter'],
            'cloud': ['cloud', 'kubernetes', 'docker', 'container', 'cloudflare', 'serverless'],
            'devsecops': ['devsecops', 'cicd', 'pipeline', 'security', 'github-actions']
        }
        
        type_keywords = {
            'tools': ['tool', 'scanner', 'analyzer', 'detector', 'bot', 'extension', 'monitoring'],
            'code': ['library', 'framework', 'api', 'client'],
            'documentation': ['guide', 'standard', 'cheat', 'top', 'documentation', 'blog'],
            'training': ['training', 'workshop', 'learning', 'vulnerable', 'dvwa', 'juice', 'hackathon']
        }
        
        # Well-known projects for each category
        recommended_projects = {
            'python_beginner': ['juice-shop', 'pytm', 'security-shepherd', 'blt', 'blt-netguardian'],
            'python_tools': ['zap', 'dependency-check', 'amass', 'blt', 'blt-api', 'toasty', 'blt-sammich'],
            'java_beginner': ['webgoat', 'security-shepherd'],
            'javascript_beginner': ['juice-shop', 'nodejsscan', 'blt', 'blt-action', 'github-sportscaster'],
            'javascript_tools': ['blt-extension', 'blt-hackathon', 'my-gsoc-tool', 'owasp-blt-lyte'],
            'training': ['juice-shop', 'webgoat', 'security-shepherd', 'dvwa', 'blt-hackathon'],
            'bug_bounty': ['blt', 'blt-extension', 'blt-action', 'blt-sammich', 'blt-netguardian'],
            'mobile': ['fresh', 'selferase'],
            'cloud': ['blt-on-cloudflare', 'blt-api-on-cloudflare'],
            'api': ['blt-api', 'blt-api-on-cloudflare'],
            'security_tools': ['blt', 'blt-netguardian', 'blt-cve', 'owasp-bumper', 'blt-extension'],
            'automation': ['blt-action', 'owasp-blt-website-monitor', 'github-sportscaster'],
            'ai_tools': ['toasty'],
            'privacy': ['selferase', 'fresh'],
            'monitoring': ['owasp-blt-website-monitor', 'blt-netguardian'],
            'documentation': ['blt-documentation', 'blt-blog'],
            'community': ['blt-hackathon', 'my-gsoc-tool']
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
        
        # Return top results based on limit (0 = all)
        if limit == 0:
            return ranked
        else:
            return ranked[:limit]
    
    def recommend_mission_based(
        self,
        goal: str,
        contribution_type: str,
        limit: int = 3
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
        
        # Return top results based on limit (0 = all)
        return ranked if limit == 0 else ranked[:limit]
    
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
                "text": f"🎉 *Here are your recommended OWASP projects ({len(recommendations)} found):*"
            }
        }
    ]
    
    # Slack has a 50 block limit. Each project = 2 blocks (section + divider)
    # Plus ~5 blocks for header/footer = max ~22 projects with individual blocks
    # If more than 20 projects, use compact text format instead
    if len(recommendations) <= 20:
        # Detailed format with individual blocks
        for i, project in enumerate(recommendations, 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {project['name']}*\n{project['description']}\n🔗 <{project['url']}|View Project>"
                }
            })
            blocks.append({"type": "divider"})
    else:
        # Compact text format for many projects
        # Split into chunks to avoid hitting Slack's 3000 char limit per block
        chunk_size = 10  # Reduced from 15 to ensure we stay under limits
        for chunk_start in range(0, len(recommendations), chunk_size):
            chunk = recommendations[chunk_start:chunk_start + chunk_size]
            text = ""
            for i, project in enumerate(chunk, chunk_start + 1):
                # Truncate description to max 150 chars to prevent block overflow
                description = project['description']
                if len(description) > 150:
                    description = description[:147] + "..."
                
                text += f"*{i}. {project['name']}*\n{description}\n🔗 <{project['url']}|View Project>\n\n"
            
            # Double-check text length and truncate if needed
            if len(text) > 2900:
                text = text[:2897] + "..."
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text.strip()
                }
            })
    
    # Add follow-up actions
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "💡 *Want to get started contributing?*\nCheck out the contributing guidelines or ask me anything else!"
        }
    })
    
    # Only show "Show All" button if we haven't shown all yet
    action_buttons = []
    if len(recommendations) <= 3:
        action_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "📋 Show All Projects"},
            "value": "show_all",
            "action_id": "show_all_projects"
        })
    
    action_buttons.extend([
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "🔄 New Search"},
            "value": "restart",
            "action_id": "restart_conversation"
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Done"},
            "value": "done",
            "action_id": "end_conversation"
        }
    ])
    
    blocks.append({
        "type": "actions",
        "elements": action_buttons
    })
    
    return {
        "text": "Here are your recommended projects",
        "blocks": blocks
    }
