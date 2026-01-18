#!/usr/bin/env python3
"""
Fetch BLT and relevant OWASP projects for the recommendation system
Combines OWASP-BLT organization repos with filtered OWASP-metadata projects
"""
import json
import urllib.request
from pathlib import Path

# OWASP-metadata repository - contains all OWASP projects with weekly updates
METADATA_URL = "https://raw.githubusercontent.com/OWASP-BLT/OWASP-metadata/main/data/metadata.json"
# GitHub API for OWASP-BLT organization
BLT_API_URL = "https://api.github.com/orgs/OWASP-BLT/repos?per_page=100"
PROJECTS_FILE = Path(__file__).parent.parent / "data" / "projects.json"

# Keywords to filter relevant OWASP projects for security recommendations
RELEVANT_KEYWORDS = [
    'blt', 'bug', 'security', 'vulnerability', 'pentest', 'testing', 'scanner',
    'tool', 'zap', 'juice', 'webgoat', 'top', 'cheat', 'guide', 'asvs', 'samm',
    'masvs', 'nettacker', 'dependency', 'defectdojo', 'threat', 'ctf', 'training'
]


def fetch_blt_repos():
    """Fetch OWASP-BLT organization repositories from GitHub API"""
    print("Fetching OWASP-BLT repositories...")
    all_repos = []
    url = BLT_API_URL
    
    try:
        while url:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'OWASP-BLT-Lettuce/1.0')
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                all_repos.extend(data)
                
                # Check for pagination
                link_header = response.headers.get('Link', '')
                url = None
                if 'rel="next"' in link_header:
                    for link in link_header.split(','):
                        if 'rel="next"' in link:
                            url = link.split(';')[0].strip('<> ')
                            break
        
        print(f"Fetched {len(all_repos)} OWASP-BLT repositories")
        return all_repos
    except Exception as e:
        print(f"Warning: Could not fetch BLT repos from GitHub API: {e}")
        print("Continuing with metadata only...")
        return []


def fetch_owasp_metadata():
    """Fetch OWASP projects metadata from centralized repository"""
    print("Fetching OWASP project metadata...")
    
    req = urllib.request.Request(METADATA_URL)
    req.add_header('User-Agent', 'OWASP-BLT-Lettuce/1.0')
    
    with urllib.request.urlopen(req) as response:
        metadata = json.loads(response.read().decode())
        print(f"Fetched {len(metadata)} OWASP repositories from metadata")
        return metadata


def load_existing_projects():
    """Load existing projects from projects.json"""
    if PROJECTS_FILE.exists():
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_projects(projects):
    """Save projects to projects.json"""
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)


def is_relevant_project(item):
    """Check if a project is relevant for security recommendations"""
    # Get searchable text from project
    title = (item.get('title', '') or '').lower() if isinstance(item.get('title'), str) else ''
    pitch = (item.get('pitch', '') or '').lower() if isinstance(item.get('pitch'), str) else ''
    tags = item.get('tags', '')
    # Handle tags as list or string
    if isinstance(tags, list):
        tags = ' '.join(str(t) for t in tags).lower()
    elif isinstance(tags, str):
        tags = tags.lower()
    else:
        tags = ''
    
    repo = (item.get('repo', '') or '').lower() if isinstance(item.get('repo'), str) else ''
    project_type = (item.get('type', '') or '').lower() if isinstance(item.get('type'), str) else ''
    
    searchable = f"{title} {pitch} {tags} {repo} {project_type}"
    
    # Check if any relevant keyword is present
    return any(keyword in searchable for keyword in RELEVANT_KEYWORDS)


def transform_blt_repos_to_projects(repos):
    """Transform OWASP-BLT GitHub repos into projects.json format"""
    projects = {}
    
    for repo in repos:
        # Skip archived repositories
        if repo.get('archived', False):
            continue
        
        repo_name = repo['name']
        description = repo.get('description') or f"OWASP BLT - {repo_name}"
        url = repo['html_url']
        
        # Use consistent naming format
        project_key = repo_name.lower()
        projects[project_key] = [description, url]
    
    return projects


def transform_metadata_to_projects(metadata):
    """Transform OWASP metadata into projects.json format (filtered for relevance)"""
    projects = {}
    
    for item in metadata:
        # Skip archived repositories
        if item.get('archived', True):
            continue
        
        # Filter for relevant projects only
        if not is_relevant_project(item):
            continue
        
        repo = item.get('repo', '')
        if not repo:
            continue
        
        # Extract project name from repo (format: OWASP/project-name)
        if '/' in repo:
            org, project_name = repo.split('/', 1)
        else:
            project_name = repo
        
        # Get project title (prefer title from metadata over repo name)
        title = item.get('title', '')
        if not title:
            # Fallback: format repo name nicely
            title = f"OWASP {project_name.replace('-', ' ').replace('_', ' ').title()}"
        
        # Get description from pitch or tags
        pitch = item.get('pitch', '')
        tags = item.get('tags', '')
        
        if pitch:
            description = pitch
        elif tags:
            description = f"{title} - {tags}"
        else:
            description = title
        
        # Construct GitHub URL
        url = f"https://github.com/{repo}"
        
        # Use project name as key (lowercase, clean up prefixes)
        project_key = project_name.lower().replace('www-project-', '').replace('www-chapter-', '')
        
        # Avoid duplicates - skip if key already exists
        if project_key not in projects:
            projects[project_key] = [description, url]
    
    return projects


def main():
    """Main function to fetch and update projects"""
    print("OWASP BLT Project Fetcher")
    print("=" * 50)
    
    all_projects = {}
    
    # Step 1: Fetch OWASP-BLT organization repos
    blt_repos = fetch_blt_repos()
    if blt_repos:
        blt_projects = transform_blt_repos_to_projects(blt_repos)
        all_projects.update(blt_projects)
        print(f"Added {len(blt_projects)} OWASP-BLT projects")
    
    # Step 2: Fetch and filter OWASP metadata for relevant projects
    try:
        metadata = fetch_owasp_metadata()
        owasp_projects = transform_metadata_to_projects(metadata)
        
        # Merge, preferring BLT projects for duplicates
        for key, value in owasp_projects.items():
            if key not in all_projects:
                all_projects[key] = value
        
        print(f"Added {len(owasp_projects)} relevant OWASP projects")
    except Exception as e:
        print(f"Error fetching OWASP metadata: {e}")
        if not all_projects:
            print("No projects fetched. Exiting.")
            return
    
    # Save combined projects
    save_projects(all_projects)
    print(f"\nSuccessfully updated {PROJECTS_FILE}")
    print(f"Total projects: {len(all_projects)}")
    
    # Show some statistics
    blt_count = len([k for k in all_projects.keys() if k in [r['name'].lower() for r in blt_repos]])
    print(f"  - BLT organization projects: {blt_count}")
    print(f"  - Filtered OWASP projects: {len(all_projects) - blt_count}")
    
    # Show sample projects
    print("\nSample BLT projects:")
    blt_samples = [(k, v) for k, v in list(all_projects.items())[:15] if 'blt' in k.lower() or 'blt' in v[0].lower()]
    for key, value in blt_samples[:5]:
        print(f"  {key}: {value[0][:80]}...")
    
    print("\nSample OWASP projects:")
    owasp_samples = [(k, v) for k, v in list(all_projects.items())[:20] if 'blt' not in k.lower()]
    for key, value in owasp_samples[:5]:
        print(f"  {key}: {value[0][:80]}...")


if __name__ == "__main__":
    main()
