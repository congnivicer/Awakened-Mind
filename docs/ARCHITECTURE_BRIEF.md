# Awakened Mind - Architecture Brief

Based on PROJECT_RULES.md and conversation history analysis.

## Project Status
- **Current State**: 95% complete, ready for testing
- **Missing**: ChromaDB connection layer, coordination fixes
- **Known Issue**: MCP Orchestrator double-init bug (line 156)

## Three-Tier Vector Storage Strategy

### 1. Internal Vectors (Local/Cache)
- **Location**: `/Volumes/Little_Brain/` 
- **Purpose**: Lightweight local cache
- **Status**: Available, needs connection layer

### 2. External Vectors (Multi-Volume)
- **Locations**: 
  - `/Volumes/Knowledge/chroma/` - Main knowledge storage (6 collections)
  - `/Volumes/Active_Mind/` - Processing and scrapers
  - `/Volumes/Memories/` - Persistent memory storage
  - `/Volumes/Archive/` - Historical data storage
- **Status**: All mounted and accessible

### 3. Cloud Vectors (Multi-Service Free Tier)
- **Zilliz**: 3M vectors free (3 accounts × 1M each)
- **Supabase**: 150k vectors free (3 accounts × 50k each) 
- **Total Capacity**: 6.45M free vectors
- **Navigation**: SQLite database tracking vector locations
- **Status**: Strategy defined, implementation needed

## Core Component Locations

### Authoritative Sources (DO NOT MOVE)
- `/Volumes/Knowledge/chroma/` - ChromaDB collections (6 specialized)
- `/Volumes/Active_Mind/scrapers/universal_github_integration.py`
- `/Volumes/Active_Mind/scheduler/nightly_harvester.py`
- `/Volumes/Little_Brain/mcp_orchestrator.py` (needs bug fix)
- `/Volumes/Little_Brain/check_status.py`
- `/Volumes/Little_Brain/requirements.txt`

### Development/Experimental Files (COPY ONLY)
- `/Users/cognivicer/Desktop/warp/knowledge-harvesting-system/`
- `/Users/cognivicer/Desktop/warp/chroma-zone-gui-workspace/`

## Critical Bug Fix Required
```python
# File: /Volumes/Little_Brain/mcp_orchestrator.py line 156
# Change from:
if not await self.initialize_components():

# To:
if self.knowledge_system is None or self.github_discoverer is None:
    if not await self.initialize_components():
```

## ChromaDB Collections Structure
1. `github_projects` - Repository information
2. `technical_docs` - Documentation
3. `nhb_interactions` - Conversation logs  
4. `current_events` - News and updates
5. `code_patterns` - Programming patterns
6. `collective_wisdom` - Accumulated insights

## Dependencies Status
✅ All required Python packages installed:
- aiohttp>=3.8.0
- schedule>=1.2.0  
- chromadb>=0.4.15
- requests>=2.28.0
- python-dateutil>=2.8.2
- rich>=13.0.0
- PyGithub>=1.58.0

## Build Strategy
This directory (`/Volumes/NHB_Workspace/awakened_mind/`) serves as a **BUILD-ONLY workspace** for:
- Code consolidation and testing
- Configuration management
- Deployment preparation

**IMPORTANT**: Heavy vector data remains in authoritative volumes and is accessed via symlinks/references only.