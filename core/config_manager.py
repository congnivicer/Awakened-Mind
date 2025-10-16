#!/usr/bin/env python3
"""
Configuration Management System for Awakened Mind Knowledge Harvesting System

This module provides centralized configuration management with:
- Environment variable support
- Configuration file loading
- Runtime configuration overrides
- Validation and type conversion
- Nested configuration access with dot notation
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from datetime import datetime

try:
    from .exceptions import ConfigurationError, PathConfigurationError
except ImportError:
    # Running as standalone script
    from exceptions import ConfigurationError, PathConfigurationError


@dataclass
class ChromaConfig:
    """ChromaDB-specific configuration"""
    timeout: int = 30
    max_connections: int = 10
    max_connections_per_host: int = 5
    persist_directory: str = "/Volumes/Knowledge/chroma"
    collection_prefix: str = "nhb_"
    embedding_model: str = "all-MiniLM-L6-v2"
    anonymized_telemetry: bool = False


@dataclass
class GitHubConfig:
    """GitHub API configuration"""
    api_timeout: int = 30
    rate_limit_per_minute: int = 60
    max_retries: int = 3
    max_concurrent_requests: int = 5
    token_validation: bool = True
    user_agent: str = "NHB-Knowledge-Infrastructure/1.0"


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file_path: str = "/Volumes/Active_Mind/logs/orchestrator_activity.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class VolumeConfig:
    """Volume path configuration"""
    knowledge: str = "/Volumes/Knowledge"
    active_mind: str = "/Volumes/Active_Mind"
    memories: str = "/Volumes/Memories"
    archive: str = "/Volumes/Archive"
    little_brain: str = "/Volumes/Little_Brain"


@dataclass
class SystemConfig:
    """Main system configuration container"""
    chromadb: ChromaConfig = field(default_factory=ChromaConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    volumes: VolumeConfig = field(default_factory=VolumeConfig)

    # Additional system settings
    workspace_root: str = ""
    max_pipeline_operations: int = 100
    cleanup_interval_minutes: int = 60
    health_check_interval_seconds: int = 300


class ConfigManager:
    """
    Centralized configuration management system

    Supports multiple configuration sources in order of precedence:
    1. Runtime overrides (highest priority)
    2. Environment variables
    3. Configuration files
    4. Default values (lowest priority)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config: SystemConfig = SystemConfig()
        self._runtime_overrides: Dict[str, Any] = {}
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from all sources"""
        try:
            # Start with defaults
            self._config = SystemConfig()

            # Override with environment variables
            self._load_environment_config()

            # Override with file-based configuration
            self._load_file_config()

            # Apply runtime overrides
            self._apply_runtime_overrides()

            # Validate configuration
            self._validate_configuration()

            # Set workspace root if not configured
            if not self._config.workspace_root:
                self._config.workspace_root = str(Path(__file__).parent.parent)

            self.logger.info("✅ Configuration loaded successfully")

        except Exception as e:
            self.logger.error(f"❌ Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")

    def _load_environment_config(self):
        """Load configuration from environment variables"""
        try:
            # ChromaDB configuration
            if os.getenv('CHROMADB_TIMEOUT'):
                self._config.chromadb.timeout = int(os.getenv('CHROMADB_TIMEOUT', '30'))
            if os.getenv('CHROMADB_MAX_CONNECTIONS'):
                self._config.chromadb.max_connections = int(os.getenv('CHROMADB_MAX_CONNECTIONS', '10'))
            if os.getenv('CHROMADB_PERSIST_DIR'):
                self._config.chromadb.persist_directory = os.getenv('CHROMADB_PERSIST_DIR', '/Volumes/Knowledge/chroma')
            if os.getenv('CHROMADB_EMBEDDING_MODEL'):
                self._config.chromadb.embedding_model = os.getenv('CHROMADB_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

            # GitHub configuration
            if os.getenv('GITHUB_API_TIMEOUT'):
                self._config.github.api_timeout = int(os.getenv('GITHUB_API_TIMEOUT', '30'))
            if os.getenv('GITHUB_RATE_LIMIT'):
                self._config.github.rate_limit_per_minute = int(os.getenv('GITHUB_RATE_LIMIT', '60'))
            if os.getenv('GITHUB_MAX_RETRIES'):
                self._config.github.max_retries = int(os.getenv('GITHUB_MAX_RETRIES', '3'))
            if os.getenv('GITHUB_TOKEN'):
                self._config.github.token_validation = True

            # Logging configuration
            if os.getenv('LOG_LEVEL'):
                self._config.logging.level = os.getenv('LOG_LEVEL', 'INFO').upper()
            if os.getenv('LOG_FILE'):
                self._config.logging.file_path = os.getenv('LOG_FILE', '/Volumes/Active_Mind/logs/orchestrator_activity.log')

            # Volume configuration
            if os.getenv('VOLUME_KNOWLEDGE'):
                self._config.volumes.knowledge = os.getenv('VOLUME_KNOWLEDGE', '/Volumes/Knowledge')
            if os.getenv('VOLUME_ACTIVE_MIND'):
                self._config.volumes.active_mind = os.getenv('VOLUME_ACTIVE_MIND', '/Volumes/Active_Mind')
            if os.getenv('VOLUME_MEMORIES'):
                self._config.volumes.memories = os.getenv('VOLUME_MEMORIES', '/Volumes/Memories')
            if os.getenv('VOLUME_ARCHIVE'):
                self._config.volumes.archive = os.getenv('VOLUME_ARCHIVE', '/Volumes/Archive')
            if os.getenv('VOLUME_LITTLE_BRAIN'):
                self._config.volumes.little_brain = os.getenv('VOLUME_LITTLE_BRAIN', '/Volumes/Little_Brain')

            # System configuration
            if os.getenv('WORKSPACE_ROOT'):
                self._config.workspace_root = os.getenv('WORKSPACE_ROOT', '')
            if os.getenv('MAX_PIPELINE_OPERATIONS'):
                self._config.max_pipeline_operations = int(os.getenv('MAX_PIPELINE_OPERATIONS', '100'))

        except Exception as e:
            self.logger.warning(f"Error loading environment configuration: {e}")

    def _load_file_config(self):
        """Load configuration from JSON files"""
        config_files = [
            Path(self._config.workspace_root) / 'configs' / 'system_config.json',
            Path(self._config.workspace_root) / 'system_config.json',
            Path.cwd() / 'system_config.json'
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        file_config = json.load(f)

                    self._merge_config_from_dict(file_config)
                    self.logger.info(f"✅ Loaded configuration from {config_file}")
                    break

                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON in config file {config_file}: {e}")
                except Exception as e:
                    self.logger.warning(f"Error loading config file {config_file}: {e}")

    def _merge_config_from_dict(self, config_dict: Dict[str, Any]):
        """Merge configuration from dictionary"""
        try:
            # ChromaDB settings
            if 'chromadb' in config_dict:
                chromadb_config = config_dict['chromadb']
                if 'timeout' in chromadb_config:
                    self._config.chromadb.timeout = chromadb_config['timeout']
                if 'max_connections' in chromadb_config:
                    self._config.chromadb.max_connections = chromadb_config['max_connections']
                if 'persist_directory' in chromadb_config:
                    self._config.chromadb.persist_directory = chromadb_config['persist_directory']
                if 'embedding_model' in chromadb_config:
                    self._config.chromadb.embedding_model = chromadb_config['embedding_model']

            # GitHub settings
            if 'github' in config_dict:
                github_config = config_dict['github']
                if 'api_timeout' in github_config:
                    self._config.github.api_timeout = github_config['api_timeout']
                if 'rate_limit_per_minute' in github_config:
                    self._config.github.rate_limit_per_minute = github_config['rate_limit_per_minute']
                if 'max_retries' in github_config:
                    self._config.github.max_retries = github_config['max_retries']

            # Logging settings
            if 'logging' in config_dict:
                logging_config = config_dict['logging']
                if 'level' in logging_config:
                    self._config.logging.level = logging_config['level'].upper()
                if 'file_path' in logging_config:
                    self._config.logging.file_path = logging_config['file_path']

            # Volume settings
            if 'volumes' in config_dict:
                volumes_config = config_dict['volumes']
                for volume_name in ['knowledge', 'active_mind', 'memories', 'archive', 'little_brain']:
                    if volume_name in volumes_config:
                        setattr(self._config.volumes, volume_name, volumes_config[volume_name])

            # System settings
            if 'workspace_root' in config_dict:
                self._config.workspace_root = config_dict['workspace_root']
            if 'max_pipeline_operations' in config_dict:
                self._config.max_pipeline_operations = config_dict['max_pipeline_operations']

        except Exception as e:
            self.logger.warning(f"Error merging configuration from dict: {e}")

    def _apply_runtime_overrides(self):
        """Apply any runtime configuration overrides"""
        for key, value in self._runtime_overrides.items():
            self._set_nested_value(self._config, key, value)

    def _validate_configuration(self):
        """Validate the loaded configuration"""
        try:
            # Validate ChromaDB settings
            if self._config.chromadb.timeout <= 0:
                raise ConfigurationError("ChromaDB timeout must be positive", "chromadb.timeout")
            if self._config.chromadb.max_connections <= 0:
                raise ConfigurationError("ChromaDB max connections must be positive", "chromadb.max_connections")

            # Validate GitHub settings
            if self._config.github.api_timeout <= 0:
                raise ConfigurationError("GitHub API timeout must be positive", "github.api_timeout")
            if self._config.github.rate_limit_per_minute <= 0:
                raise ConfigurationError("GitHub rate limit must be positive", "github.rate_limit_per_minute")

            # Validate volume paths
            for volume_name in ['knowledge', 'active_mind', 'memories', 'archive', 'little_brain']:
                volume_path = getattr(self._config.volumes, volume_name)
                if not volume_path:
                    raise PathConfigurationError(f"Volume path cannot be empty: {volume_name}", volume_name)

                # Check if path exists or can be created
                path_obj = Path(volume_path)
                if not path_obj.exists():
                    try:
                        path_obj.mkdir(parents=True, exist_ok=True)
                        self.logger.info(f"✅ Created volume directory: {volume_path}")
                    except Exception as e:
                        self.logger.warning(f"Cannot create volume directory {volume_path}: {e}")

            # Validate logging configuration
            if self._config.logging.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                raise ConfigurationError(f"Invalid log level: {self._config.logging.level}", "logging.level")

        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            else:
                raise ConfigurationError(f"Configuration validation failed: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., 'chromadb.timeout', 'github.api_timeout')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._get_nested_value(self._config, key, default)

    def set(self, key: str, value: Any):
        """
        Set runtime configuration override

        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        self._runtime_overrides[key] = value
        self._set_nested_value(self._config, key, value)

    def _get_nested_value(self, config_obj: Any, key: str, default: Any) -> Any:
        """Get nested value using dot notation"""
        keys = key.split('.')
        current = config_obj

        try:
            for k in keys:
                if hasattr(current, k):
                    current = getattr(current, k)
                elif isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            return current
        except Exception:
            return default

    def _set_nested_value(self, config_obj: Any, key: str, value: Any):
        """Set nested value using dot notation"""
        keys = key.split('.')
        current = config_obj

        # Navigate to the parent object
        for k in keys[:-1]:
            if hasattr(current, k):
                current = getattr(current, k)
            elif isinstance(current, dict):
                if k not in current:
                    current[k] = {}
                current = current[k]
            else:
                return  # Cannot set nested value

        # Set the final value
        final_key = keys[-1]
        if hasattr(current, final_key):
            setattr(current, final_key, value)
        elif isinstance(current, dict):
            current[final_key] = value

    def get_chromadb_config(self) -> ChromaConfig:
        """Get ChromaDB-specific configuration"""
        return self._config.chromadb

    def get_github_config(self) -> GitHubConfig:
        """Get GitHub API configuration"""
        return self._config.github

    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        return self._config.logging

    def get_volume_paths(self) -> Dict[str, str]:
        """Get all volume paths as dictionary"""
        return {
            'knowledge': self._config.volumes.knowledge,
            'active_mind': self._config.volumes.active_mind,
            'memories': self._config.volumes.memories,
            'archive': self._config.volumes.archive,
            'little_brain': self._config.volumes.little_brain
        }

    def get_volume_path(self, volume_name: str) -> Path:
        """Get specific volume path"""
        if volume_name not in ['knowledge', 'active_mind', 'memories', 'archive', 'little_brain']:
            raise ConfigurationError(f"Invalid volume name: {volume_name}", "volume_name")

        volume_path = getattr(self._config.volumes, volume_name)
        return Path(volume_path)

    def get_chroma_path(self) -> Path:
        """Get ChromaDB data directory path"""
        return Path(self._config.chromadb.persist_directory)

    def get_collections_config_path(self) -> Path:
        """Get collections configuration file path"""
        return Path(self._config.workspace_root) / 'configs' / 'collections_config.json'

    def get_system_config_path(self) -> Path:
        """Get system configuration file path"""
        return Path(self._config.workspace_root) / 'configs' / 'system_config.json'

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            'chromadb': {
                'timeout': self._config.chromadb.timeout,
                'max_connections': self._config.chromadb.max_connections,
                'persist_directory': self._config.chromadb.persist_directory,
                'embedding_model': self._config.chromadb.embedding_model
            },
            'github': {
                'api_timeout': self._config.github.api_timeout,
                'rate_limit_per_minute': self._config.github.rate_limit_per_minute,
                'max_retries': self._config.github.max_retries
            },
            'logging': {
                'level': self._config.logging.level,
                'file_path': self._config.logging.file_path
            },
            'volumes': self.get_volume_paths(),
            'system': {
                'workspace_root': self._config.workspace_root,
                'max_pipeline_operations': self._config.max_pipeline_operations
            }
        }

    def save_to_file(self, file_path: Optional[Union[str, Path]] = None) -> bool:
        """Save current configuration to file"""
        try:
            if file_path is None:
                file_path = self.get_system_config_path()

            # Convert to string if Path object
            file_path_str = str(file_path)

            Path(file_path_str).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path_str, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)

            self.logger.info(f"✅ Configuration saved to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to save configuration: {e}")
            return False


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get or create the global configuration manager instance

    Returns:
        ConfigManager: Global configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reset_config_manager():
    """Reset the global configuration manager (mainly for testing)"""
    global _config_manager
    _config_manager = None


# Convenience functions for common configuration access
def get_chromadb_timeout() -> int:
    """Get ChromaDB timeout setting"""
    return get_config_manager().get('chromadb.timeout', 30)


def get_github_api_timeout() -> int:
    """Get GitHub API timeout setting"""
    return get_config_manager().get('github.api_timeout', 30)


def get_workspace_root() -> str:
    """Get workspace root directory"""
    return get_config_manager()._config.workspace_root


def get_volume_path(volume_name: str) -> Path:
    """Get volume path by name"""
    return get_config_manager().get_volume_path(volume_name)