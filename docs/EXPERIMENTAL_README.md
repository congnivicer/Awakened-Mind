# NHB Knowledge Infrastructure - Cloud-First Architecture

## Overview
A sophisticated knowledge harvesting system with lightweight local caching and cloud-based heavy lifting. Built for seamless integration between local development and distributed cloud resources.

## System Architecture

### Local Components (Lightweight)
```
/knowledge-harvesting-system/
├── core/
│   ├── mcp_orchestrator.py          # Fixed coordination layer
│   ├── cloud_sync.py                # Multi-cloud integration
│   └── knowledge_navigator.py       # GPS for knowledge location
├── config/
│   ├── system_config.json           # Main system settings
│   ├── cloud_accounts.json          # Multi-account strategy
│   └── collections_config.json     # ChromaDB collections
├── cache/
│   ├── local_vectors/              # Lightweight local cache
│   └── knowledge_map.db            # Navigation database
└── integrations/
    ├── gemini_pro.py               # Google Gemini Pro integration
    ├── github_harvester.py         # Repository knowledge extraction
    └── chroma_manager.py           # ChromaDB interface
```

### Cloud Resources
- **Zilliz**: 3M vectors across 3 accounts (primary storage)
- **Supabase**: 150k vectors across 3 accounts (specialized collections)
- **Google Gemini Pro**: AI processing and embeddings
- **Gmail Account**: vetpalnpo@gmail.com (primary integration)

### ChromaDB Collections
1. `github_projects` - Repository knowledge and code patterns
2. `technical_docs` - Documentation and technical resources
3. `nhb_interactions` - Conversation history and learning
4. `current_events` - Real-time information and updates
5. `code_patterns` - Reusable code templates and solutions
6. `collective_wisdom` - Aggregated insights and knowledge

## Quick Start

1. **Initialize System**:
   ```bash
   python3 core/mcp_orchestrator.py --init
   ```

2. **Configure Cloud Accounts**:
   ```bash
   python3 core/cloud_sync.py --setup-accounts
   ```

3. **Start Knowledge Harvesting**:
   ```bash
   python3 core/mcp_orchestrator.py --harvest
   ```

## Key Features

- ✅ **Fixed MCP Orchestrator**: Resolved double-init bug from line 156
- ✅ **Multi-Cloud Strategy**: 6.45M free vectors across services
- ✅ **Knowledge GPS**: Intelligent routing to optimal storage location
- ✅ **Email-Based Scaling**: Each email account = new free tier
- ✅ **Real-time Sync**: Bidirectional synchronization between local/cloud
- ✅ **Gemini Pro Integration**: Advanced AI processing capabilities

## Based on Conversations
This implementation incorporates insights from 8 development conversations:
- MCP Orchestrator discovery and testing
- Bug identification and system architecture
- Cloud strategy and multi-account approach
- ChromaDB configuration and navigation systems

## Status: Ready for Implementation
All components designed and ready for deployment. The foundation is solid - just needs coordination layer activation.