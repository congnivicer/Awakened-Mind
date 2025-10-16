# Volume & Datastore Mapping

## Authority Mapping Strategy

### 🔒 AUTHORITATIVE SOURCES (Never Move, Always Reference)

#### `/Volumes/Knowledge/` - Main Knowledge Storage
- **Status**: PERMANENT LOCATION
- **Contents**: ChromaDB collections (6 specialized)
- **Access Method**: Symlink only
- **Size**: Large (vector data)
- **Copies to Build**: None (link only)

#### `/Volumes/Active_Mind/` - Processing & Scrapers  
- **Status**: PERMANENT LOCATION
- **Contents**: 
  - `scrapers/universal_github_integration.py` → **COPY to workspace**
  - `scheduler/nightly_harvester.py` → **COPY to workspace**  
  - `logs/`, `signals/` → **LINK ONLY**
- **Access Method**: Mixed (copy code, link data)

#### `/Volumes/Little_Brain/` - Local Cache & Control
- **Status**: PERMANENT LOCATION  
- **Contents**:
  - `mcp_orchestrator.py` → **COPY to workspace**
  - `check_status.py` → **COPY to workspace**
  - `requirements.txt` → **COPY to workspace**
  - `system_config.json` → **COPY to workspace**
  - Configuration files → **COPY to workspace**
- **Access Method**: Copy code, link heavy data

#### `/Volumes/Memories/` - Persistent Memory
- **Status**: PERMANENT LOCATION
- **Contents**: Memory storage
- **Access Method**: Symlink only
- **Copies to Build**: None (link only)

#### `/Volumes/Archive/` - Historical Data
- **Status**: PERMANENT LOCATION
- **Contents**: Historical vector data
- **Access Method**: Symlink only  
- **Copies to Build**: None (link only)

### 📋 DEVELOPMENT/EXPERIMENTAL (Copy Only)

#### `/Users/cognivicer/Desktop/warp/knowledge-harvesting-system/`
- **Status**: EXPERIMENTAL - COPY TO WORKSPACE
- **Contents**: Development code and configs
- **Action**: Copy all, merge with authoritative sources
- **Notes**: Reconcile with volume-based versions

#### `/Users/cognivicer/Desktop/warp/chroma-zone-gui-workspace/`
- **Status**: GUI WORKSPACE - COPY TO WORKSPACE
- **Contents**: React/TypeScript GUI
- **Action**: Copy entire workspace to `gui/`
- **Notes**: Update paths for workspace structure

## Build Workspace Structure

```
/Volumes/NHB_Workspace/awakened_mind/
├── core/                    # Copied from volumes
│   ├── mcp_orchestrator.py  # From /Volumes/Little_Brain/
│   └── check_status.py      # From /Volumes/Little_Brain/
├── scrapers/                # Copied from /Volumes/Active_Mind/scrapers/
├── scheduler/               # Copied from /Volumes/Active_Mind/scheduler/
├── gui/                     # Copied from desktop workspace
├── configs/                 # Consolidated configs
│   ├── system_config.json
│   ├── collections_config.json
│   └── requirements.txt
├── docs/                    # This directory
├── tests/                   # Test scripts
├── scripts/                 # Build and deployment scripts
└── links_to_vectors/        # SYMLINKS ONLY - NO DATA
    ├── knowledge -> /Volumes/Knowledge/
    ├── active_mind -> /Volumes/Active_Mind/
    ├── memories -> /Volumes/Memories/
    ├── archive -> /Volumes/Archive/
    └── little_brain -> /Volumes/Little_Brain/
```

## Cloud Vector Strategy

### Zilliz Cloud (3M vectors free)
- **Account Strategy**: 3 accounts × 1M vectors each
- **Access Method**: API credentials in secure config
- **Data Movement**: Upload only, never download bulk
- **Navigation**: SQLite tracking database

### Supabase Vector (150k vectors free)  
- **Account Strategy**: 3 accounts × 50k vectors each
- **Access Method**: API credentials in secure config
- **Data Movement**: Upload only, never download bulk
- **Navigation**: SQLite tracking database

## Security & Access Rules

### File Permissions
- **Workspace**: Read/Write for development
- **Volume Links**: Read-only access to prevent accidents
- **Cloud Configs**: Restricted access, encrypted storage

### Data Movement Rules
1. **Never move authoritative vector data**
2. **Always copy code files for development**  
3. **Use symlinks for heavy data access**
4. **Maintain audit trail of all operations**

### Backup Strategy
- **Volumes**: Backed up via external systems (not workspace responsibility)
- **Workspace**: Versioned in git (excluding linked data)
- **Cloud**: Service-level backups

## Implementation Notes

- All symlinks use absolute paths
- `.gitignore` prevents vector data from entering version control
- Environment variables control runtime path resolution
- Build scripts validate all links before deployment