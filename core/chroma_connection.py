#!/usr/bin/env python3
"""
ChromaDB Connection Layer for Awakened Mind Knowledge Harvesting System

This module provides the connection interface between the MCP Orchestrator
and the existing ChromaDB collections stored in the volume-based architecture.
"""

import asyncio
import importlib
from typing import Any
# Attempt to load chromadb at runtime to avoid static unresolved-import diagnostics
chromadb: Any = None
try:
    chromadb = importlib.import_module("chromadb")
except ModuleNotFoundError:
    # Graceful fallback stub for environments where chromadb is not installed.
    # This allows static analysis and importing the module without hard failure.
    class _ChromaStub:
        class Settings:
            def __init__(self, *args, **kwargs):
                # settings stub; real chromadb.Settings may accept different args
                pass
        class PersistentClient:
            def __init__(self, *args, **kwargs):
                # Prevent accidental runtime usage when chromadb isn't installed.
                raise RuntimeError("chromadb is not installed; install the 'chromadb' package to use NHBKnowledgeBase")
    chromadb = _ChromaStub()
import json
import logging
import sys
import weakref
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from contextlib import asynccontextmanager

# Add parent directory to path to import configs
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from .exceptions import (
        ChromaConnectionError, ChromaOperationError, KnowledgeStorageError,
        MetadataFormatError, ConfigurationError, PathConfigurationError
    )
except ImportError:
    # Running as standalone script
    from exceptions import (
        ChromaConnectionError, ChromaOperationError, KnowledgeStorageError,
        MetadataFormatError, ConfigurationError, PathConfigurationError
    )

try:
    from .config_manager import get_config_manager
except ImportError:
    # Running as standalone script
    from config_manager import get_config_manager

try:
    from .performance import get_metadata_cache, get_performance_monitor, monitor_performance, cache_metadata
except ImportError:
    # Running as standalone script
    from performance import get_metadata_cache, get_performance_monitor, monitor_performance, cache_metadata

from configs.path_manager import get_path_manager
import uuid


class NHBKnowledgeBase:
    """
    Production ChromaDB Knowledge Base Interface with proper resource management
    Connects to existing ChromaDB collections in the volume architecture
    """

    def __init__(self):
        self.path_manager = get_path_manager()
        self.config_manager = get_config_manager()
        self.chroma_path = self.config_manager.get_chroma_path()
        self.collections_config_path = self.config_manager.get_collections_config_path()

        # Performance optimization
        self.metadata_cache = get_metadata_cache()
        self.performance_monitor = get_performance_monitor()

        # Resource management
        self.client = None
        self.collections = {}
        self.config = None
        self._is_initialized = False
        self._cleanup_lock = asyncio.Lock()
        self._connection_pool = None

        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def initialize(self) -> bool:
        """Initialize ChromaDB client and load collections with proper resource management"""
        try:
            self.logger.info(f"Initializing ChromaDB connection to: {self.chroma_path}")

            # Get configuration values
            chroma_config = self.config_manager.get_chromadb_config()

            # Initialize ChromaDB client with connection settings
            self.client = chromadb.PersistentClient(
                path=str(self.chroma_path),
                settings=chromadb.Settings(
                    anonymized_telemetry=chroma_config.anonymized_telemetry,
                    is_persistent=True,
                    persist_directory=str(self.chroma_path)
                )
            )

            # Load collections configuration
            self._load_collections_config()

            # Connect to existing collections
            self._connect_to_collections()

            self._is_initialized = True
            self.logger.info(f"✅ ChromaDB Knowledge Base initialized with {len(self.collections)} collections")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize ChromaDB: {e}")
            raise ChromaConnectionError(
                f"ChromaDB initialization failed: {e}",
                context={'chroma_path': str(self.chroma_path)}
            )

    async def cleanup(self) -> None:
        """Properly close all connections and cleanup resources"""
        async with self._cleanup_lock:
            if not self._is_initialized:
                return

            try:
                self.logger.info("🧹 Starting ChromaDB cleanup...")

                # Close all collection connections
                self.collections.clear()

                # Close ChromaDB client
                if self.client:
                    try:
                        # ChromaDB client doesn't have a close method, but we can cleanup
                        if hasattr(self.client, '_client'):
                            # Close underlying HTTP client if it exists
                            if hasattr(self.client._client, 'close'):
                                await self.client._client.close()
                    except Exception as e:
                        self.logger.warning(f"Error during client cleanup: {e}")

                self.client = None
                self._is_initialized = False

                self.logger.info("✅ ChromaDB cleanup completed")

            except Exception as e:
                self.logger.error(f"❌ Error during ChromaDB cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.cleanup())
            else:
                loop.run_until_complete(self.cleanup())
        except Exception as e:
            self.logger.error(f"Error in context manager cleanup: {e}")

    @asynccontextmanager
    async def managed_connection(self):
        """Async context manager for ChromaDB connections"""
        try:
            if not self._is_initialized:
                self.initialize()
            yield self
        finally:
            await self.cleanup()
    
    def _load_collections_config(self):
        """Load collections configuration from file"""
        try:
            if not self.collections_config_path.exists():
                self.logger.warning(f"Collections config file not found: {self.collections_config_path}")
                self.config = {"collections": {}}
                return

            with open(self.collections_config_path, 'r') as f:
                self.config = json.load(f)
                self.logger.info("Collections configuration loaded")
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in collections config: {e}")
            self.config = {"collections": {}}
        except PermissionError as e:
            self.logger.error(f"Permission denied reading collections config: {e}")
            self.config = {"collections": {}}
        except Exception as e:
            self.logger.error(f"Failed to load collections config: {e}")
            self.config = {"collections": {}}
    
    def _connect_to_collections(self):
        """Connect to existing ChromaDB collections"""
        if not self.config or "collections" not in self.config:
            self.logger.warning("No collections configuration found")
            return
        
        for collection_name, collection_config in self.config["collections"].items():
            try:
                # Try to get existing collection
                if self.client:
                    collection = self.client.get_collection(name=collection_name)
                    self.collections[collection_name] = collection
                    self.logger.info(f"✅ Connected to existing collection: {collection_name}")
                else:
                    raise Exception("Chroma client not initialized")
                
            except Exception:
                # Collection doesn't exist, create it
                try:
                    if self.client:
                        collection = self.client.create_collection(name=collection_name)
                        self.collections[collection_name] = collection
                        self.logger.info(f"✅ Created new collection: {collection_name}")
                    else:
                        raise Exception("Chroma client not initialized")
                except Exception as e:
                    self.logger.error(f"❌ Failed to create collection {collection_name}: {e}")
    
    @monitor_performance("chromadb_add_documents")
    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to a specific collection with performance monitoring"""
        try:
            if collection_name not in self.collections:
                self.logger.error(f"Collection {collection_name} not found")
                return False
            
            collection = self.collections[collection_name]
            
            # Prepare data for ChromaDB
            ids = []
            texts = []
            metadatas = []
            
            for i, doc in enumerate(documents):
                # Generate ID if not provided
                doc_id = doc.get('id', f"{collection_name}_{uuid.uuid4().hex[:8]}_{i}")
                ids.append(doc_id)
                
                # Extract text content
                text_content = doc.get('content', doc.get('text', ''))
                texts.append(text_content)
                
                # Prepare metadata (remove content/text to avoid duplication)
                metadata = {}
                for k, v in doc.items():
                    if k not in ['content', 'text', 'id']:
                        # Use cached metadata processing for performance
                        cache_key = f"metadata_processing:{k}:{type(v).__name__}:{hash(str(v))}"
                        processed_value = self.metadata_cache.get(cache_key)

                        if processed_value is None:
                            # Process metadata value and cache result
                            if isinstance(v, dict):
                                # Convert dict to JSON string
                                processed_value = json.dumps(v)
                            elif isinstance(v, list):
                                # Convert list to comma-separated string
                                processed_value = ', '.join(str(item) for item in v)
                            elif isinstance(v, (str, int, float, bool)) or v is None:
                                # Keep simple types as-is
                                processed_value = v
                            else:
                                # Convert other types to string
                                processed_value = str(v)

                            # Cache the processed value
                            self.metadata_cache.put(cache_key, processed_value)

                        metadata[k] = processed_value
                
                metadata['timestamp'] = datetime.now().isoformat()
                metadatas.append(metadata)
            
            # Add to collection
            collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"✅ Added {len(documents)} documents to {collection_name}")
            return True
            
        except ValueError as e:
            if "metadata" in str(e).lower():
                raise MetadataFormatError(
                    f"Invalid metadata format in {collection_name}: {e}",
                    context={'collection': collection_name}
                )
            else:
                raise ChromaOperationError(
                    f"ChromaDB operation failed in {collection_name}: {e}",
                    operation="add_documents"
                )
        except Exception as e:
            self.logger.error(f"❌ Failed to add documents to {collection_name}: {e}")
            raise KnowledgeStorageError(
                f"Document storage failed in {collection_name}: {e}",
                collection=collection_name
            )
    
    @monitor_performance("chromadb_search")
    def search_documents(self, collection_name: str, query: str, n_results: int = 10) -> List[Dict]:
        """Search documents in a specific collection with performance monitoring"""
        try:
            if collection_name not in self.collections:
                self.logger.error(f"Collection {collection_name} not found")
                return []
            
            collection = self.collections[collection_name]
            
            # Query the collection
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'distance': results['distances'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    }
                    formatted_results.append(result)
            
            self.logger.info(f"Found {len(formatted_results)} results for query in {collection_name}")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"❌ Failed to search in {collection_name}: {e}")
            return []
    
    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict:
        """Get statistics for collections"""
        try:
            stats = {}
            
            if collection_name:
                if collection_name in self.collections:
                    collection = self.collections[collection_name]
                    count = collection.count()
                    stats[collection_name] = {"count": count}
            else:
                # Get stats for all collections
                for name, collection in self.collections.items():
                    count = collection.count()
                    stats[name] = {"count": count}
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get collection stats: {e}")
            return {}
    
    def list_collections(self) -> List[str]:
        """List available collections"""
        return list(self.collections.keys())
    
    def get_total_knowledge_count(self) -> int:
        """Get total knowledge items across all collections"""
        try:
            total = 0
            for collection in self.collections.values():
                total += collection.count()
            return total
        except Exception as e:
            self.logger.error(f"Failed to get total knowledge count: {e}")
            return 0


class BasicKnowledgeInterface:
    """
    Fallback knowledge interface when ChromaDB is not available
    Provides basic functionality for testing and development
    """
    
    def __init__(self):
        # Use centralized path manager to determine safe local storage locations
        try:
            self.path_manager = get_path_manager()
        except Exception:
            # Fallback: attempt to create a minimal path manager-like behavior
            self.path_manager = None

        # storage_path is expected by other parts of the system (logs show
        # AttributeError when missing). Provide a sensible default that
        # points to the Chroma path when available, or to a workspace-local
        # `.nhb_data/chroma` directory as a development-safe fallback.
        try:
            if self.path_manager:
                chroma_path = self.path_manager.get_chroma_path()
            else:
                chroma_path = Path.cwd() / '.nhb_data' / 'chroma'
        except Exception:
            chroma_path = Path.cwd() / '.nhb_data' / 'chroma'

        # Ensure directory exists for fallback storage operations
        try:
            chroma_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best-effort; don't raise here to avoid breaking the fallback
            pass

        self.storage_path = chroma_path
        self.documents = {}
        self.logger = logging.getLogger(__name__)
        
    def initialize(self, storage_path: Optional[Path] = None) -> bool:
        """Initialize basic interface"""
        if storage_path:
            self.storage_path = storage_path
            self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"✅ Basic Knowledge Interface initialized. Storage path: {self.storage_path}")
        return True
    
    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to in-memory storage"""
        if collection_name not in self.documents:
            self.documents[collection_name] = []
        
        self.documents[collection_name].extend(documents)
        self.logger.info(f"Added {len(documents)} documents to {collection_name} (basic interface)")
        return True
    
    def search_documents(self, collection_name: str, query: str, n_results: int = 10) -> List[Dict]:
        """Basic text search"""
        if collection_name not in self.documents:
            return []
        
        # Simple text matching
        results = []
        for doc in self.documents[collection_name]:
            content = doc.get('content', doc.get('text', ''))
            if query.lower() in content.lower():
                results.append(doc)
                if len(results) >= n_results:
                    break
        
        return results
    
    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict:
        """Get basic stats"""
        if collection_name:
            return {collection_name: {"count": len(self.documents.get(collection_name, []))}}
        else:
            return {name: {"count": len(docs)} for name, docs in self.documents.items()}
    
    def list_collections(self) -> List[str]:
        """List collections"""
        return list(self.documents.keys())
    
    def get_total_knowledge_count(self) -> int:
        """Get total document count"""
        return sum(len(docs) for docs in self.documents.values())


class ProcessingPipeline:
    """
    Document processing pipeline for the knowledge harvesting system
    Handles text extraction, chunking, and metadata enrichment
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document through the pipeline
        
        Args:
            document: Raw document data
            
        Returns:
            Processed document ready for storage
        """
        try:
            # Start with the original document
            processed_doc = document.copy()
            
            # Extract and clean text content
            content = self._extract_text_content(document)
            if content:
                processed_doc['content'] = content
                processed_doc['word_count'] = len(content.split())
                processed_doc['char_count'] = len(content)
            
            # Add processing metadata
            processed_doc['processed_at'] = datetime.now().isoformat()
            processed_doc['processor_version'] = '1.0.0'
            
            # Determine document type
            doc_type = self._classify_document_type(document)
            processed_doc['document_type'] = doc_type
            
            # Extract key metadata
            metadata = self._extract_metadata(document)
            processed_doc.update(metadata)
            
            self.logger.debug(f"Processed document: {processed_doc.get('title', 'untitled')}")
            return processed_doc
            
        except Exception as e:
            self.logger.error(f"Failed to process document: {e}")
            # Return original document on error
            return document
    
    def _extract_text_content(self, document: Dict[str, Any]) -> str:
        """Extract clean text content from document"""
        # Try different content fields
        content_fields = ['content', 'text', 'body', 'description', 'readme_content']
        
        for field in content_fields:
            if field in document and document[field]:
                return str(document[field]).strip()
        
        # Fallback to concatenating available text fields
        text_parts = []
        for key, value in document.items():
            if isinstance(value, str) and len(value) > 20:  # Reasonable text length
                text_parts.append(value)
        
        return ' '.join(text_parts) if text_parts else ''
    
    def _classify_document_type(self, document: Dict[str, Any]) -> str:
        """Classify the type of document"""
        # Check for GitHub repository indicators
        if 'repo_url' in document or 'repository_url' in document:
            return 'github_repository'
        
        # Check for code patterns
        content = document.get('content', '')
        if any(lang in content.lower() for lang in ['python', 'javascript', 'def ', 'function', 'class ']):
            return 'code_documentation'
        
        # Check for API documentation
        if 'api' in content.lower() and ('endpoint' in content.lower() or 'request' in content.lower()):
            return 'api_documentation'
        
        # Default to technical documentation
        return 'technical_documentation'
    
    def _extract_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and enrich metadata"""
        metadata = {}
        
        # Extract URL if available
        url_fields = ['url', 'repo_url', 'repository_url', 'source_url']
        for field in url_fields:
            if field in document and document[field]:
                metadata['source_url'] = document[field]
                break
        
        # Extract title
        title_fields = ['title', 'name', 'repo_name']
        for field in title_fields:
            if field in document and document[field]:
                metadata['title'] = document[field]
                break
        
        # Extract language information
        if 'language' in document:
            metadata['primary_language'] = document['language']
        
        # Extract topics/tags
        if 'topics' in document:
            metadata['topics'] = document['topics']
        
        return metadata


# Factory function for getting the appropriate knowledge base
def get_knowledge_base() -> Union[NHBKnowledgeBase, BasicKnowledgeInterface]:
    """
    Factory function to get the appropriate knowledge base implementation
    
    Returns:
        NHBKnowledgeBase if ChromaDB is available, otherwise BasicKnowledgeInterface
    """
    try:
        kb = NHBKnowledgeBase()
        if kb.initialize():
            return kb
    except Exception as e:
        logging.getLogger(__name__).warning(f"ChromaDB not available, using basic interface: {e}")
    
    # Fallback to basic interface
    kb = BasicKnowledgeInterface()
    kb.initialize()
    return kb