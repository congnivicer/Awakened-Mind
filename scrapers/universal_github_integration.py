#!/usr/bin/env python3
"""
Universal GitHub Knowledge Discovery System
Designed for NHB autonomous knowledge acquisition from ANY repository
"""

import asyncio
import aiohttp
import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import os
import logging

# Configure logging
GITHUB_LOG_PATH = Path('/Volumes/Active_Mind/logs/github_discovery.log')
GITHUB_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(GITHUB_LOG_PATH),
        logging.StreamHandler()
    ]
)

@dataclass
class RepoIntelligence:
    """Intelligence about a repository's value"""
    repo_url: str
    stars: int
    language: str
    topics: List[str]
    recent_activity: bool
    knowledge_score: float
    interesting_files: List[str]
    has_documentation: bool
    has_examples: bool
    license: str

class UniversalGitHubDiscoverer:
    """
    Discovers and ingests knowledge from ANY GitHub repository
    Uses multiple strategies to find valuable content continuously
    """
    
    def __init__(self, kb_instance=None):
        self.kb = kb_instance
        self.api_token = os.getenv('GITHUB_TOKEN', '')  # Optional, increases rate limit
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'NHB-Knowledge-System'
        }
        if self.api_token:
            self.headers['Authorization'] = f'token {self.api_token}'
        
        self.cache_dir = Path('/Volumes/Active_Mind/ingestion_queue/github_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.discovery_patterns = {
            'ai_ml_patterns': [
                'neural', 'transformer', 'attention', 'bert', 'gpt', 'llm',
                'embedding', 'vector', 'rag', 'agent', 'langchain', 'llamaindex'
            ],
            'valuable_files': [
                'README.md', 'ARCHITECTURE.md', 'DESIGN.md', 'API.md',
                'requirements.txt', 'package.json', 'Cargo.toml', 'go.mod',
                '.github/workflows/*.yml', 'docs/**/*.md'
            ],
            'code_patterns': [
                '*.py', '*.js', '*.ts', '*.go', '*.rs', '*.cpp', '*.java'
            ],
            'config_patterns': [
                '*.yaml', '*.yml', '*.toml', '*.json', '*.conf', '*.ini'
            ]
        }
        
        self.seen_repos = self._load_seen_repos()
        
    def _load_seen_repos(self) -> Set[str]:
        """Load set of already processed repositories"""
        seen_file = self.cache_dir / 'seen_repos.json'
        if seen_file.exists():
            with open(seen_file) as f:
                return set(json.load(f))
        return set()
    
    def _save_seen_repos(self):
        """Persist seen repositories"""
        seen_file = self.cache_dir / 'seen_repos.json'
        with open(seen_file, 'w') as f:
            json.dump(list(self.seen_repos), f)
    
    async def discover_repositories(self) -> List[RepoIntelligence]:
        """
        Multi-strategy repository discovery:
        1. Trending repositories across all languages
        2. Recently updated high-value repos
        3. Topic-based discovery (AI, ML, DevOps, etc.)
        4. Dependency chain following
        5. User/Org exploration from valuable repos
        """
        discovered = []
        
        async with aiohttp.ClientSession() as session:
            # Strategy 1: Search by trending topics
            trending_queries = [
                'stars:>100 pushed:>2024-01-01',
                'language:python machine learning',
                'language:typescript framework',
                'language:rust systems',
                'language:go cloud native',
                'topic:artificial-intelligence',
                'topic:llm',
                'topic:rag',
                'topic:vector-database',
                'topic:agents',
                'topic:opensource stars:>50'
            ]
            
            for query in trending_queries:
                repos = await self._search_repos(session, query)
                for repo in repos:
                    if repo not in self.seen_repos:
                        intelligence = await self._analyze_repo(session, repo)
                        if intelligence and intelligence.knowledge_score > 0.5:
                            discovered.append(intelligence)
                            self.seen_repos.add(repo)
            
            # Strategy 2: Follow interesting organizations
            valuable_orgs = [
                'openai', 'anthropic-ai', 'google-research', 'facebookresearch',
                'microsoft', 'huggingface', 'langchain-ai', 'pinecone-io',
                'weaviate', 'chroma-core', 'qdrant', 'deepmind', 'stability-ai'
            ]
            
            for org in valuable_orgs:
                org_repos = await self._get_org_repos(session, org)
                for repo in org_repos[:10]:  # Top 10 from each org
                    if repo not in self.seen_repos:
                        intelligence = await self._analyze_repo(session, repo)
                        if intelligence:
                            discovered.append(intelligence)
                            self.seen_repos.add(repo)
            
            # Strategy 3: Explore dependencies of known good repos
            # This finds hidden gems that popular projects depend on
            for intel in discovered[:20]:  # Check deps of first 20 discoveries
                deps = await self._discover_dependencies(session, intel.repo_url)
                for dep_repo in deps:
                    if dep_repo not in self.seen_repos:
                        dep_intel = await self._analyze_repo(session, dep_repo)
                        if dep_intel and dep_intel.knowledge_score > 0.4:
                            discovered.append(dep_intel)
                            self.seen_repos.add(dep_repo)
        
        self._save_seen_repos()
        return discovered
    
    async def _search_repos(self, session: aiohttp.ClientSession, query: str, limit: int = 30) -> List[str]:
        """Search GitHub for repositories matching query"""
        url = 'https://api.github.com/search/repositories'
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': limit
        }
        
        try:
            async with session.get(url, headers=self.headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [item['html_url'] for item in data.get('items', [])]
        except Exception as e:
            logging.error(f"Search failed for query '{query}': {e}")
        
        return []
    
    async def _get_org_repos(self, session: aiohttp.ClientSession, org: str) -> List[str]:
        """Get repositories from an organization"""
        url = f'https://api.github.com/orgs/{org}/repos'
        params = {'sort': 'updated', 'per_page': 30}
        
        try:
            async with session.get(url, headers=self.headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [repo['html_url'] for repo in data]
        except Exception as e:
            logging.error(f"Failed to get repos for org '{org}': {e}")
        
        return []
    
    async def _analyze_repo(self, session: aiohttp.ClientSession, repo_url: str) -> Optional[RepoIntelligence]:
        """Analyze a repository to determine its knowledge value"""
        # Extract owner/repo from URL
        match = re.match(r'https://github.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            return None
        
        owner, repo = match.groups()
        
        try:
            # Get repo metadata
            api_url = f'https://api.github.com/repos/{owner}/{repo}'
            async with session.get(api_url, headers=self.headers) as resp:
                if resp.status != 200:
                    return None
                
                repo_data = await resp.json()
                
                # Calculate knowledge score based on multiple factors
                score = 0.0
                
                # Stars indicate community value
                stars = repo_data.get('stargazers_count', 0)
                if stars > 1000:
                    score += 0.3
                elif stars > 100:
                    score += 0.2
                elif stars > 10:
                    score += 0.1
                
                # Recent activity
                updated_at = datetime.fromisoformat(repo_data.get('updated_at', '').replace('Z', '+00:00'))
                days_ago = (datetime.now(updated_at.tzinfo) - updated_at).days
                if days_ago < 30:
                    score += 0.2
                elif days_ago < 90:
                    score += 0.1
                
                # Language relevance
                language = repo_data.get('language', '')
                valuable_languages = ['Python', 'TypeScript', 'JavaScript', 'Go', 'Rust', 'Java', 'C++']
                if language in valuable_languages:
                    score += 0.15
                
                # Topics indicate content type
                topics = repo_data.get('topics', [])
                valuable_topics = {'ai', 'ml', 'llm', 'agent', 'rag', 'embedding', 'vector', 'api', 'framework'}
                if any(topic in valuable_topics for topic in topics):
                    score += 0.25
                
                # Check for documentation
                contents_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
                async with session.get(contents_url, headers=self.headers) as resp:
                    if resp.status == 200:
                        contents = await resp.json()
                        files = [item['name'] for item in contents if item['type'] == 'file']
                        has_readme = 'README.md' in files or 'readme.md' in files
                        has_docs = 'docs' in [item['name'] for item in contents if item['type'] == 'dir']
                        
                        if has_readme:
                            score += 0.1
                        if has_docs:
                            score += 0.15
                        
                        interesting_files = [f for f in files if any(
                            f.endswith(ext) for ext in ['.md', '.py', '.js', '.ts', '.yaml', '.yml']
                        )]
                        
                        return RepoIntelligence(
                            repo_url=repo_url,
                            stars=stars,
                            language=language,
                            topics=topics,
                            recent_activity=days_ago < 90,
                            knowledge_score=min(score, 1.0),
                            interesting_files=interesting_files[:20],
                            has_documentation=has_readme or has_docs,
                            has_examples='examples' in [item['name'] for item in contents if item['type'] == 'dir'],
                            license=repo_data.get('license', {}).get('key', 'unknown') if repo_data.get('license') else 'none'
                        )
                
        except Exception as e:
            logging.error(f"Failed to analyze repo '{repo_url}': {e}")
        
        return None
    
    async def _discover_dependencies(self, session: aiohttp.ClientSession, repo_url: str) -> List[str]:
        """Discover dependencies from package files"""
        dependencies = []
        
        match = re.match(r'https://github.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            return []
        
        owner, repo = match.groups()
        
        # Check for package.json (JavaScript/TypeScript)
        for file in ['package.json', 'requirements.txt', 'go.mod', 'Cargo.toml']:
            url = f'https://api.github.com/repos/{owner}/{repo}/contents/{file}'
            try:
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse content and extract dependency repos
                        # Implementation would parse the base64 content
                        # and extract GitHub URLs from dependencies
            except:
                continue
        
        return dependencies

async def continuous_discovery_loop():
    """Run continuous discovery and ingestion"""
    discoverer = UniversalGitHubDiscoverer()
    
    while True:
        try:
            logging.info("Starting repository discovery cycle...")
            
            # Discover new repositories
            repos = await discoverer.discover_repositories()
            logging.info(f"Discovered {len(repos)} valuable repositories")
            
            # Write discovery report
            report = {
                'timestamp': datetime.now().isoformat(),
                'discovered': len(repos),
                'ingested': min(50, len(repos)),
                'top_repos': [
                    {
                        'url': r.repo_url,
                        'score': r.knowledge_score,
                        'stars': r.stars,
                        'topics': r.topics
                    } for r in repos[:10]
                ]
            }
            
            report_file = Path('/Volumes/Active_Mind/signals/last_discovery.json')
            report_file.parent.mkdir(parents=True, exist_ok=True)
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Wait before next cycle (6 hours)
            await asyncio.sleep(6 * 3600)
            
        except Exception as e:
            logging.error(f"Discovery cycle failed: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour on error

if __name__ == "__main__":
    # Run the continuous discovery
    asyncio.run(continuous_discovery_loop())
