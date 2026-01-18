#!/usr/bin/env python3
"""
Fetch all OWASP-BLT repositories and add them to projects.json
"""
import json
import urllib.request
from pathlib import Path

GITHUB_API_URL = "https://api.github.com/orgs/OWASP-BLT/repos?per_page=100"
PROJECTS_FILE = Path(__file__).parent.parent / "data" / "projects.json"


def fetch_blt_repos():
    """Fetch all OWASP-BLT repositories from GitHub API"""
    all_repos = []
    url = GITHUB_API_URL
    
    while url:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'OWASP-BLT-Lettuce/1.0')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            all_repos.extend(data)
            
            # Check for pagination (Link header)
            link_header = response.headers.get('Link', '')
            url = None
            if 'rel="next"' in link_header:
                # Parse next URL from Link header
                for link in link_header.split(','):
                    if 'rel="next"' in link:
                        url = link.split(';')[0].strip('<> ')
                        break
    
    return all_repos


def load_existing_projects():
    """Load existing projects from projects.json"""
    if PROJECTS_FILE.exists():
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_projects(projects):
    """Save projects to projects.json"""
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, indent=2)


def main():
    print(f"Fetching OWASP-BLT repositories from GitHub...")
    repos = fetch_blt_repos()
    
    print(f"Found {len(repos)} repositories")
    
    # Load existing projects
    projects = load_existing_projects()
    print(f"Existing projects: {len(projects)}")
    
    # Add BLT repos to projects
    added_count = 0
    for repo in repos:
        repo_name = repo['name']
        description = repo['description'] or f"OWASP BLT - {repo_name}"
        url = repo['html_url']
        
        # Use consistent naming format
        project_key = f"blt-{repo_name.lower()}"
        
        if project_key not in projects:
            projects[project_key] = [description, url]
            added_count += 1
            print(f"  Added: {project_key}")
    
    # Save updated projects
    save_projects(projects)
    print(f"\nAdded {added_count} new BLT projects")
    print(f"Total projects: {len(projects)}")
    print(f"Saved to {PROJECTS_FILE}")


if __name__ == "__main__":
    main()
