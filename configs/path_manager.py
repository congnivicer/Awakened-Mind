"""
Centralized Path Management for Awakened Mind Knowledge Harvesting System

This module provides centralized path resolution for internal, external, and cloud 
vector locations using environment variables and configuration files.

Supports both development (build workspace) and production (volume-based) deployments.
"""

import os
import json
from pathlib import Path
from typing import Dict, Union, Optional, Any
from enum import Enum


class PathType(Enum):
    """Types of paths managed by the system"""
    INTERNAL_VECTORS = "internal_vectors"
    EXTERNAL_VECTORS = "external_vectors" 
    CLOUD_CONFIG = "cloud_config"
    SYSTEM_CONFIG = "system_config"
    LOGS = "logs"
    TEMP = "temp"
    CHROMA_DB = "chroma_db"


class PathManager:
    """Centralized path management for the Awakened Mind system"""
    
    def __init__(self, workspace_root: Optional[Union[str, Path]] = None):
        """
        Initialize path manager
        
        Args:
            workspace_root: Root of the workspace (auto-detected if None)
        """
        self.workspace_root = self._detect_workspace_root(workspace_root)
        self.is_development = self._is_development_environment()
        self._load_configuration()
    
    def _detect_workspace_root(self, workspace_root: Optional[Union[str, Path]]) -> Path:
        """Auto-detect or validate workspace root"""
        if workspace_root:
            return Path(workspace_root).resolve()
            
        # Try to detect from current file location
        current_file = Path(__file__).resolve()
        potential_root = current_file.parent.parent  # configs/../
        
        # Check if this looks like our workspace
        if (potential_root / "core" / "mcp_orchestrator.py").exists():
            return potential_root
            
        # Fallback to environment variable
        env_root = os.getenv("AWAKENED_MIND_ROOT")
        if env_root:
            return Path(env_root).resolve()
            
        # Default to build workspace location
        return Path("/Volumes/NHB_Workspace/awakened_mind").resolve()
    
    def _is_development_environment(self) -> bool:
        """Determine if we're in development/build environment"""
        # Check if we're in the build workspace
        if "NHB_Workspace" in str(self.workspace_root):
            return True
            
        # Check environment variable
        return os.getenv("AWAKENED_MIND_ENV", "production").lower() == "development"
    
    def _load_configuration(self):
        """Load path configuration from config files"""
        self.config = {}
        
        # Load system config
        system_config_path = self.workspace_root / "configs" / "system_config.json"
        if system_config_path.exists():
            with open(system_config_path, 'r') as f:
                self.config.update(json.load(f))
    
    def get_volume_path(self, volume_name: str) -> Path:
        """Get path to a specific volume"""
        if self.is_development:
            # In development, use symlinks
            link_path = self.workspace_root / "links_to_vectors" / volume_name
            if link_path.exists() and link_path.is_symlink():
                return link_path.resolve()
                
        # Production paths (direct volume access)
        volume_paths = {
            "knowledge": Path("/Volumes/Knowledge"),
            "active_mind": Path("/Volumes/Active_Mind"), 
            "memories": Path("/Volumes/Memories"),
            "archive": Path("/Volumes/Archive"),
            "little_brain": Path("/Volumes/Little_Brain")
        }
        
        return volume_paths.get(volume_name, Path(f"/Volumes/{volume_name}"))
    
    def get_chroma_path(self) -> Path:
        """Get ChromaDB storage path"""
        return self.get_volume_path("knowledge") / "chroma"
    
    def get_logs_path(self) -> Path:
        """Get logs directory path"""
        if self.is_development:
            # Development logs go in workspace
            logs_path = self.workspace_root / "logs"
            logs_path.mkdir(exist_ok=True)
            return logs_path
        else:
            # Production logs go to Active_Mind volume
            return self.get_volume_path("active_mind") / "logs"
    
    def get_temp_path(self) -> Path:
        """Get temporary files path"""
        if self.is_development:
            temp_path = self.workspace_root / "temp"
            temp_path.mkdir(exist_ok=True)
            return temp_path
        else:
            return self.get_volume_path("active_mind") / "temp"
    
    def get_config_path(self, config_name: str) -> Path:
        """Get path to a configuration file"""
        if self.is_development:
            # Development configs are in workspace
            return self.workspace_root / "configs" / config_name
        else:
            # Production configs depend on type
            if config_name in ["system_config.json", "collections_config.json"]:
                return self.get_volume_path("little_brain") / config_name
            else:
                return self.workspace_root / "configs" / config_name
    
    def get_signals_path(self) -> Path:
        """Get signals directory path"""
        return self.get_volume_path("active_mind") / "signals"
    
    def get_ingestion_queue_path(self) -> Path:
        """Get ingestion queue path"""
        return self.get_volume_path("active_mind") / "ingestion_queue"
    
    def get_cloud_config_path(self) -> Path:
        """Get cloud accounts configuration path"""
        return self.get_config_path("cloud_accounts.json")
    
    def get_collections_config_path(self) -> Path:
        """Get ChromaDB collections configuration path"""
        return self.get_config_path("collections_config.json")
    
    def ensure_path_exists(self, path: Union[str, Path], is_file: bool = False) -> Path:
        """Ensure a path exists, creating directories as needed"""
        path_obj = Path(path)
        
        if is_file:
            # Create parent directories for file
            path_obj.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Create directory
            path_obj.mkdir(parents=True, exist_ok=True)
            
        return path_obj
    
    def get_runtime_info(self) -> Dict[str, Any]:
        """Get runtime environment information"""
        return {
            "workspace_root": str(self.workspace_root),
            "is_development": self.is_development,
            "environment": os.getenv("AWAKENED_MIND_ENV", "production"),
            "volumes_accessible": self._check_volume_accessibility(),
            "chroma_path": str(self.get_chroma_path()),
            "logs_path": str(self.get_logs_path())
        }
    
    def _check_volume_accessibility(self) -> Dict[str, bool]:
        """Check which volumes are accessible"""
        volumes = ["knowledge", "active_mind", "memories", "archive", "little_brain"]
        accessibility = {}
        
        for volume in volumes:
            try:
                volume_path = self.get_volume_path(volume)
                accessibility[volume] = volume_path.exists() and volume_path.is_dir()
            except Exception:
                accessibility[volume] = False
                
        return accessibility


# Global instance for easy importing
path_manager = PathManager()


def get_path_manager() -> PathManager:
    """Get the global path manager instance"""
    return path_manager


# Convenience functions for common paths
def get_chroma_path() -> Path:
    """Get ChromaDB storage path"""
    return path_manager.get_chroma_path()


def get_logs_path() -> Path:
    """Get logs directory path"""  
    return path_manager.get_logs_path()


def get_config_path(config_name: str) -> Path:
    """Get configuration file path"""
    return path_manager.get_config_path(config_name)


def get_volume_path(volume_name: str) -> Path:
    """Get volume path"""
    return path_manager.get_volume_path(volume_name)


# Environment configuration
def configure_for_development():
    """Configure paths for development environment"""
    os.environ["AWAKENED_MIND_ENV"] = "development"


def configure_for_production():  
    """Configure paths for production environment"""
    os.environ["AWAKENED_MIND_ENV"] = "production"


if __name__ == "__main__":
    # Test the path manager
    pm = PathManager()
    
    print("=== Awakened Mind Path Manager ===")
    print(f"Environment: {'Development' if pm.is_development else 'Production'}")
    print(f"Workspace Root: {pm.workspace_root}")
    print()
    
    print("=== Key Paths ===")
    print(f"ChromaDB: {pm.get_chroma_path()}")
    print(f"Logs: {pm.get_logs_path()}")
    print(f"Temp: {pm.get_temp_path()}")
    print(f"Signals: {pm.get_signals_path()}")
    print()
    
    print("=== Volume Accessibility ===")
    for volume, accessible in pm._check_volume_accessibility().items():
        status = "✓" if accessible else "✗"
        print(f"{status} {volume}: {pm.get_volume_path(volume)}")
    print()
    
    print("=== Runtime Info ===")
    import pprint
    pprint.pprint(pm.get_runtime_info())