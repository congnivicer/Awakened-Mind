#!/usr/bin/env python3
"""
NHB Knowledge Infrastructure - Master Control Program Orchestrator
The coordination layer that ties harvest → process → store together

CRITICAL FIX: Addresses the double-initialization bug from line 156
Original problematic code:
    if not await self.initialize_components():

Fixed code checks for None components first:
    if self.knowledge_system is None or self.github_discoverer is None:
        if not await self.initialize_components():
"""

from __future__ import annotations

import asyncio
import logging
import json
import sys
import base64
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

if TYPE_CHECKING:
    import aiohttp  # type: ignore

# Import GitHub integration - will be handled in __init__
UniversalGitHubDiscoverer = None
RepoIntelligence = None

# Import config manager at module level for use in __init__
_get_config_manager = None
try:
    from .config_manager import get_config_manager as _get_config_manager
except ImportError:
    try:
        from config_manager import get_config_manager as _get_config_manager
    except ImportError:
        # Fallback if config_manager doesn't exist yet
        _get_config_manager = None

try:
    from .security import get_token_manager, get_input_validator, get_rate_limiter, get_security_monitor
except ImportError:
    # Fallback if security module doesn't exist yet
    get_token_manager = None
    get_input_validator = None
    get_rate_limiter = None
    get_security_monitor = None

try:
    from .performance import get_performance_monitor, get_memory_optimizer, monitor_performance
except ImportError:
    # Fallback if performance module doesn't exist yet
    get_performance_monitor = None
    get_memory_optimizer = None
    monitor_performance = None

# Import chroma_connection module (works both as module and standalone script)
try:
    from .chroma_connection import NHBKnowledgeBase, BasicKnowledgeInterface, ProcessingPipeline
    try:
        from .exceptions import (
            GitHubAPIError, GitHubRateLimitError, GitHubTokenError,
            DocumentProcessingError, PipelineExecutionError, InitializationError
        )
    except ImportError:
        # Running as standalone script
        from exceptions import (
            GitHubAPIError, GitHubRateLimitError, GitHubTokenError,
            DocumentProcessingError, PipelineExecutionError, InitializationError
        )
except ImportError:
    # Running as standalone script
    from chroma_connection import NHBKnowledgeBase, BasicKnowledgeInterface, ProcessingPipeline

@dataclass
class SystemStatus:
    """System status tracking"""
    initialized: bool = False
    components_ready: Dict[str, bool] = field(default_factory=lambda: {
        'knowledge_system': False,
        'github_discoverer': False,
        'processing_pipeline': False
    })
    last_health_check: Optional[datetime] = None
    active_operations: int = 0

class MCPKnowledgeOrchestrator:
    """
    Master Control Program for NHB Knowledge Infrastructure
    
    CRITICAL FIX APPLIED: Line 156 bug resolved
    - Prevents double-initialization 
    - Checks for None components before initializing
    """
    
    def __init__(self):
        self.status = SystemStatus()

        # Core components (initially None to prevent double-init)
        self.knowledge_system = None
        self.github_discoverer = None
        self.processing_pipeline = None

        # Initialize configuration manager
        if _get_config_manager is not None:
            self.config_manager = _get_config_manager()
        else:
            # Fallback to basic configuration if config manager not available
            from types import SimpleNamespace
            self.config_manager = SimpleNamespace(
                get_volume_path=lambda name: Path(f'/Volumes/{name.replace("_", "_").title()}'),
                get_chroma_path=lambda: Path('/Volumes/Knowledge/chroma'),
                get_logging_config=lambda: SimpleNamespace(level='INFO', file_path='/Volumes/Active_Mind/logs/orchestrator_activity.log'),
                get_github_config=lambda: SimpleNamespace(api_timeout=30)
            )

        # Initialize security manager
        if get_token_manager is not None and callable(get_token_manager):
            self.token_manager = get_token_manager()
            if get_input_validator is not None and callable(get_input_validator):
                self.input_validator = get_input_validator()
            else:
                self.input_validator = None
            if get_rate_limiter is not None and callable(get_rate_limiter):
                self.rate_limiter = get_rate_limiter()
            else:
                self.rate_limiter = None
            if get_security_monitor is not None and callable(get_security_monitor):
                self.security_monitor = get_security_monitor()
            else:
                self.security_monitor = None
        else:
            # Fallback if security module not available
            from types import SimpleNamespace
            self.token_manager = SimpleNamespace(get_token=lambda service: os.getenv('GITHUB_TOKEN'))
            self.input_validator = SimpleNamespace(
                validate_github_url=lambda url: bool(re.match(r'^https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/?$', url)),
                sanitize_content=lambda content, **kwargs: str(content)[:100000] if content else ""
            )
            self.rate_limiter = None
            self.security_monitor = None

        # Initialize performance manager
        if get_performance_monitor is not None and callable(get_performance_monitor):
            self.performance_monitor = get_performance_monitor()
            if get_memory_optimizer is not None and callable(get_memory_optimizer):
                self.memory_optimizer = get_memory_optimizer()
            else:
                self.memory_optimizer = None
        else:
            # Fallback if performance module not available
            self.performance_monitor = None
            self.memory_optimizer = None

        # Get paths from configuration manager
        self.knowledge_volume = self.config_manager.get_volume_path('knowledge')
        self.active_mind_volume = self.config_manager.get_volume_path('active_mind')
        self.memories_volume = self.config_manager.get_volume_path('memories')
        self.archive_volume = self.config_manager.get_volume_path('archive')

        # Get workspace root from configuration
        self.workspace_root = Path(self.config_manager._config.workspace_root or Path(__file__).parent.parent)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Try to import GitHub integration from multiple possible locations
        self._import_github_integration()

        self.logger.info("MCP Orchestrator initialized")
    
    def _setup_logging(self):
        """Configure logging system using configuration manager"""
        logging_config = self.config_manager.get_logging_config()
        log_file = logging_config.file_path

        # Ensure log directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        # Configure logging level
        log_level = getattr(logging, logging_config.level.upper(), logging.INFO)

        logging.basicConfig(
            level=log_level,
            format=logging_config.format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file)
            ]
        )

    def _import_github_integration(self):
        """Import GitHub integration from multiple possible locations"""
        global UniversalGitHubDiscoverer, RepoIntelligence

        # Try to import GitHub integration from multiple possible locations
        github_integration_paths = [
            str(self.active_mind_volume / 'scrapers'),
            str(self.workspace_root / 'scrapers')
        ]

        for path in github_integration_paths:
            if Path(path).exists():
                sys.path.insert(0, path)
                try:
                    # Use dynamic import to avoid static resolution errors and try multiple possible module names
                    import importlib

                    candidate_modules = [
                        'universal_github_integration',
                        'universal_github',
                        'github_integration',
                        'universal_github_integration.main',
                    ]

                    mod = None
                    for mod_name in candidate_modules:
                        try:
                            mod = importlib.import_module(mod_name)
                            if mod:
                                break
                        except Exception:
                            mod = None
                            continue

                    if mod is not None:
                        UniversalGitHubDiscoverer = getattr(mod, 'UniversalGitHubDiscoverer', None)
                        RepoIntelligence = getattr(mod, 'RepoIntelligence', None)
                        if UniversalGitHubDiscoverer is not None or RepoIntelligence is not None:
                            self.logger.info(f"✅ GitHub integration found at: {path} (module={mod.__name__})")
                            return
                        # If module loaded but expected attributes missing, continue searching
                    # otherwise continue to next path
                except Exception:
                    continue

        self.logger.warning("GitHub integration not found in any expected location")
    
    async def initialize_components(self) -> bool:
        """
        Initialize all system components
        
        Returns:
            bool: True if all components initialized successfully
        """
        self.logger.info("Initializing MCP Orchestrator components...")
        
        try:
            # Initialize ChromaDB Knowledge System
            self.logger.info("Loading ChromaDB knowledge system...")
            # Import and initialize the existing ChromaDB system
            sys.path.append(str(self.knowledge_volume / 'chroma'))
            
            try:
                self.knowledge_system = NHBKnowledgeBase()
                success = await asyncio.get_event_loop().run_in_executor(None, self.knowledge_system.initialize)
                if success:
                    self.status.components_ready['knowledge_system'] = True
                    self.logger.info("✅ ChromaDB Knowledge System initialized")
                else:
                    raise Exception("ChromaDB initialization failed")
            except Exception as e:
                self.logger.warning(f"ChromaDB system not available ({e}), creating basic interface...")
                self.knowledge_system = BasicKnowledgeInterface()
                # FIX: Initialize the BasicKnowledgeInterface with a storage path
                storage_path = self.active_mind_volume / 'fallback_knowledge'
                self.knowledge_system.initialize(storage_path=storage_path)
                self.status.components_ready['knowledge_system'] = True
            
            # Initialize GitHub Discoverer
            self.logger.info("Initializing GitHub discovery system...")
            if UniversalGitHubDiscoverer is not None:
                self.github_discoverer = UniversalGitHubDiscoverer(kb_instance=self.knowledge_system)
                self.status.components_ready['github_discoverer'] = True
                self.logger.info("✅ GitHub Discoverer initialized")
            else:
                self.logger.warning("GitHub Discoverer not available")
                self.status.components_ready['github_discoverer'] = False
            
            # Initialize Processing Pipeline
            self.logger.info("Setting up processing pipeline...")
            self.processing_pipeline = ProcessingPipeline()
            self.status.components_ready['processing_pipeline'] = True
            self.logger.info("✅ Processing Pipeline initialized")
            
            self.status.initialized = True
            self.status.last_health_check = datetime.now()
            
            self.logger.info("🚀 All MCP Orchestrator components initialized successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Component initialization failed: {str(e)}")
            raise InitializationError(
                f"MCP Orchestrator component initialization failed: {e}",
                component="mcp_orchestrator"
            )
    
    async def process_pipeline(self) -> dict | bool:
        """
        CRITICAL FIX: This method contained the line 156 bug
        
        Original problematic code:
            if not await self.initialize_components():
        
        Fixed to check for None components first to prevent double initialization:
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Knowledge Pipeline")
        self.logger.info("=" * 60)
        
        # CRITICAL BUG FIX: Check if components are None before initializing
        if self.knowledge_system is None or self.github_discoverer is None:
            self.logger.info("Components not initialized, initializing now...")
            if not await self.initialize_components():
                self.logger.error("Failed to initialize components")
                return False

        # Additional safety check: ensure components are properly initialized
        if not self.status.initialized:
            self.logger.error("Components not properly initialized")
            return False

        # Proceed with the pipeline
        results = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "operations": []
        }

        try:
            self.status.active_operations += 1

            # Step 1: Discover repositories (skip if GitHub discoverer not available)
            if self.github_discoverer is not None:
                self.logger.info("🔍 Step 1: Discovering repositories...")
                discovered_repos = await self.github_discoverer.discover_repositories()
            else:
                self.logger.info("🔍 Step 1: Skipping repository discovery (GitHub discoverer not available)")
                discovered_repos = []
            results["operations"].append({
                "step": "discovery",
                "status": "completed",
                "repositories_found": len(discovered_repos)
            })
            self.logger.info(f"Found {len(discovered_repos)} repositories")
            
            # Step 2: Extract content from top repositories
            self.logger.info("📥 Step 2: Extracting content from repositories...")
            extracted_docs = []
            
            # Process top 10 repositories
            for repo in discovered_repos[:10]:
                try:
                    content = await self.extract_repo_content(repo)
                    if content:
                        extracted_docs.append(content)
                except Exception as e:
                    self.logger.error(f"Failed to extract from {repo.repo_url}: {e}")
                    # Continue with other repositories even if one fails
            
            results["operations"].append({
                "step": "extraction",
                "status": "completed", 
                "documents_extracted": len(extracted_docs)
            })
            self.logger.info(f"Extracted {len(extracted_docs)} documents")
            
            # Step 3: Process and store documents
            self.logger.info("💾 Step 3: Processing and storing documents...")
            stored_count = 0
            
            for doc in extracted_docs:
                try:
                    # Process the document (skip if processing pipeline not available)
                    if self.processing_pipeline is not None:
                        processed_doc = await self.processing_pipeline.process_document(doc)
                    else:
                        processed_doc = doc  # Use original document if no processing available

                    # Store in knowledge system
                    await self.store_knowledge(processed_doc)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(f"Failed to process/store document: {e}")
                    raise DocumentProcessingError(
                        f"Document processing failed: {e}",
                        document_id=doc.get('id'),
                        stage="processing_storage"
                    )
            
            results["operations"].append({
                "step": "storage",
                "status": "completed",
                "documents_stored": stored_count
            })
            
            # Generate summary report
            self.logger.info("📊 Generating pipeline summary...")
            summary = {
                "timestamp": datetime.now().isoformat(),
                "repositories_discovered": len(discovered_repos),
                "documents_extracted": len(extracted_docs),
                "documents_stored": stored_count,
                "total_knowledge_items": await self.get_knowledge_count(),
                "pipeline_duration": "completed"
            }
            
            # Save summary to signals with proper file handle management
            signals_dir = self.active_mind_volume / 'signals'
            signals_dir.mkdir(parents=True, exist_ok=True)

            # Use atomic write to prevent corruption
            summary_file = signals_dir / 'last_harvest_summary.json'
            temp_file = signals_dir / 'last_harvest_summary.json.tmp'

            try:
                # Write to temporary file first
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)

                # Atomic move to final location
                temp_file.replace(summary_file)

                self.logger.info(f"✅ Pipeline summary saved to {summary_file}")

            except Exception as e:
                self.logger.error(f"Failed to save pipeline summary: {e}")
                # Clean up temp file if it exists
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
            
            results["summary"] = summary
            self.logger.info("✅ Knowledge pipeline completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            results["status"] = "error"
            results["error"] = str(e)
            raise PipelineExecutionError(
                f"Knowledge pipeline execution failed: {e}",
                stage="pipeline_execution"
            )
        
        finally:
            self.status.active_operations -= 1
        
        return results
    
    async def extract_repo_content(self, repo: Any) -> Optional[Dict]:
        """
        Extract actual content from GitHub repository with proper resource management
        This implements the missing content extraction mentioned in the briefing
        """
        # Dynamically import aiohttp to avoid static analysis errors when the package
        # is not present in the environment; provide a clear runtime error if missing.
        import importlib
        try:
            aiohttp = importlib.import_module('aiohttp')
        except Exception:
            raise RuntimeError("Missing dependency 'aiohttp'. Please install it: pip install aiohttp")

        # Validate GitHub URL using security validator
        if self.input_validator is not None:
            if not self.input_validator.validate_github_url(repo.repo_url):
                self.logger.warning(f"Invalid GitHub URL: {repo.repo_url}")
                raise GitHubAPIError(f"Invalid GitHub URL format: {repo.repo_url}", url=repo.repo_url)

        # Parse owner/repo from URL
        match = repo.repo_url.replace('https://github.com/', '').split('/')
        if len(match) < 2:
            return None

        owner, repo_name = match[0], match[1]

        # Create aiohttp session with proper configuration for resource management
        github_config = self.config_manager.get_github_config()
        timeout = aiohttp.ClientTimeout(total=github_config.api_timeout)
        connector = aiohttp.TCPConnector(
            limit=10,                    # Max 10 concurrent connections
            limit_per_host=5,           # Max 5 connections per host
            ttl_dns_cache=300,          # DNS cache for 5 minutes
            use_dns_cache=True,
            keepalive_timeout=60        # Keep connections alive for 60 seconds
        )

        try:
            # Check rate limiting before making requests
            if self.rate_limiter is not None:
                if not self.rate_limiter.is_allowed('github', repo.repo_url):
                    self.logger.warning(f"Rate limit exceeded for {repo.repo_url}")
                    raise GitHubRateLimitError(f"Rate limit exceeded for {repo.repo_url}")

            # Use context manager for proper session cleanup
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': 'NHB-Knowledge-Infrastructure/1.0'}
            ) as session:

                # Set up headers with proper token validation
                headers = {'Accept': 'application/vnd.github.v3+json'}

                # Validate and add GitHub API token if available
                github_token = self._get_github_token()
                if github_token:
                    headers['Authorization'] = f'Bearer {github_token}'

                # Get README content with error handling
                readme_content = await self._fetch_readme_content(session, headers, owner, repo_name)

                # Check for suspicious content in README
                if self.security_monitor is not None:
                    if self.security_monitor.detect_suspicious_activity(readme_content, f"github:{owner}/{repo_name}"):
                        self.logger.warning(f"Suspicious content detected in {owner}/{repo_name}")

                # Get repository metadata with error handling
                repo_data = await self._fetch_repo_metadata(session, headers, owner, repo_name)

                # Sanitize content for safe storage
                sanitized_content = readme_content
                if self.input_validator is not None:
                    sanitized_content = self.input_validator.sanitize_content(readme_content)

                # Sanitize metadata
                sanitized_metadata = {
                    'description': repo_data.get('description', ''),
                    'topics': repo_data.get('topics', []),
                    'language': repo_data.get('language', ''),
                    'stars': repo_data.get('stargazers_count', 0),
                    'forks': repo_data.get('forks_count', 0),
                    'updated_at': repo_data.get('updated_at', ''),
                    'license': repo_data.get('license', {}).get('key', 'unknown') if repo_data.get('license') else 'none',
                    'knowledge_score': repo.knowledge_score
                }

                # Validate and sanitize metadata if validator available
                if self.input_validator is not None:
                    sanitized_metadata = self.input_validator.validate_metadata(sanitized_metadata)

                return {
                    'id': f"github_{owner}_{repo_name}",
                    'source': 'github',
                    'url': repo.repo_url,
                    'title': f"{owner}/{repo_name}",
                    'content': sanitized_content,
                    'metadata': sanitized_metadata
                }

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout extracting content from {repo.repo_url}")
            raise GitHubAPIError(
                f"Timeout extracting content from {repo.repo_url}",
                url=repo.repo_url,
                context={'timeout': True}
            )
        except Exception as e:
            self.logger.error(f"Failed to extract content from {repo.repo_url}: {e}")
            raise GitHubAPIError(
                f"Failed to extract content from {repo.repo_url}: {e}",
                url=repo.repo_url
            )

    def _get_github_token(self) -> Optional[str]:
        """Safely get GitHub API token with validation"""
        # First try to get token from secure token manager
        if self.token_manager is not None:
            try:
                token = self.token_manager.get_token('github')
                if token:
                    return token
            except Exception as e:
                self.logger.warning(f"Failed to get token from secure manager: {e}")

        # Fallback to legacy method
        if (self.github_discoverer is not None and
            hasattr(self.github_discoverer, 'api_token') and
            self.github_discoverer.api_token and
            isinstance(self.github_discoverer.api_token, str) and
            self.github_discoverer.api_token.strip()):

            token = self.github_discoverer.api_token.strip()
            # Basic token format validation (GitHub tokens start with ghp_ for personal access tokens)
            if len(token) > 10 and not token.startswith('ghp_'):
                self.logger.warning("GitHub API token format may be invalid")
            return token
    async def _fetch_readme_content(self, session: Any, headers: Dict, owner: str, repo_name: str) -> str:
        """Fetch README content with proper error handling"""
        try:
            readme_url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
            async with session.get(readme_url, headers=headers) as resp:
                if resp.status == 200:
                    readme_data = await resp.json()
                    return base64.b64decode(readme_data['content']).decode('utf-8', errors='ignore')
                elif resp.status == 404:
                    return "No README found"
                else:
                    self.logger.warning(f"Failed to fetch README for {owner}/{repo_name}: HTTP {resp.status}")
                    return "No README found"
        except Exception as e:
            # Single, consolidated exception handler to avoid unreachable except clauses
            self.logger.warning(f"Error fetching README for {owner}/{repo_name}: {e}")
            return "No README found"

    async def _fetch_repo_metadata(self, session: aiohttp.ClientSession, headers: Dict, owner: str, repo_name: str) -> Dict:
        """Fetch repository metadata with proper error handling"""
        try:
            repo_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            async with session.get(repo_url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    self.logger.warning(f"Failed to fetch repo metadata for {owner}/{repo_name}: HTTP {resp.status}")
                    return {}
        except Exception as e:
            self.logger.warning(f"Error fetching repo metadata for {owner}/{repo_name}: {e}")
            return {}
    
    async def store_knowledge(self, document: Dict):
        """Store processed document in the knowledge system"""
        try:
            # Determine appropriate collection based on document type
            doc_type = document.get('document_type', 'technical_documentation')
            collection_name = self._get_collection_for_document_type(doc_type)
            
            # Use the new ChromaDB connection layer
            if self.knowledge_system is not None:
                success = await asyncio.get_event_loop().run_in_executor(
                    None, self.knowledge_system.add_documents, collection_name, [document]
                )
            else:
                self.logger.error("Knowledge system not available")
                success = False
            
            if success:
                self.logger.info(f"Stored document: {document.get('title', document['id'])} in {collection_name}")
            else:
                raise Exception("Failed to add document to knowledge base")
            
        except Exception as e:
            self.logger.error(f"Failed to store document {document['id']}: {e}")
            raise
    
    def _get_collection_for_document_type(self, doc_type: str) -> str:
        """Map document type to appropriate collection"""
        type_mapping = {
            'github_repository': 'github_projects',
            'code_documentation': 'code_patterns',
            'api_documentation': 'technical_docs',
            'technical_documentation': 'technical_docs'
        }
        return type_mapping.get(doc_type, 'technical_docs')
    
    async def get_knowledge_count(self) -> int:
        """Get total count of knowledge items"""
        if self.knowledge_system is None:
            return 0
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self.knowledge_system.get_total_knowledge_count
            )
        except Exception as e:
            self.logger.error(f"Failed to get knowledge count: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
            "metrics": {
                "active_operations": self.status.active_operations,
                "initialized": self.status.initialized,
                "knowledge_items": await self.get_knowledge_count()
            }
        }
        
        # Check each component
        if self.status.components_ready:
            for component_name, is_ready in self.status.components_ready.items():
                health_status["components"][component_name] = {
                    "status": "ready" if is_ready else "not_initialized"
                }
        
        self.status.last_health_check = datetime.now()
        return health_status


# Test function
async def test_orchestrator():
    """Test the orchestrator system"""
    orchestrator = MCPKnowledgeOrchestrator()
    
    print("🧪 Testing MCP Orchestrator...")
    
    # Test initialization
    success = await orchestrator.initialize_components()
    print(f"Initialization: {'✅ Success' if success else '❌ Failed'}")
    
    if success:
        # Test health check
        health = await orchestrator.health_check()
        print(f"Health Check: {health['overall_status']}")
        print(f"Knowledge Items: {health['metrics']['knowledge_items']}")
        
        # Ask if user wants to run a test harvest
        response = input("Run a test harvest? (y/n): ")
        if response.lower() == 'y':
            print("🚀 Running test pipeline...")
            results = await orchestrator.process_pipeline()
            if isinstance(results, dict):
                print(f"Pipeline Result: {results.get('status', 'unknown')}")
                if 'summary' in results and results.get('summary'):
                    print(f"Documents processed: {results['summary'].get('documents_stored', 'N/A')}")
            else:
                print("Pipeline execution failed or returned no results.")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
