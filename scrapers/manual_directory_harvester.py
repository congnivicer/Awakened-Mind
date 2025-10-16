#!/usr/bin/env python3
"""
Manual Directory Knowledge Harvester
Allows users to manually specify directories to harvest knowledge from
"""

import asyncio
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging
from dataclasses import dataclass
import mimetypes

@dataclass
class DirectoryHarvestConfig:
    """Configuration for directory harvesting"""
    source_path: str
    recursive: bool = True
    max_depth: int = 10
    file_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    min_file_size: int = 100  # bytes
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    def __post_init__(self):
        if self.file_patterns is None:
            self.file_patterns = [
                '*.md', '*.txt', '*.rst', '*.py', '*.js', '*.ts', '*.java',
                '*.cpp', '*.c', '*.h', '*.go', '*.rs', '*.php', '*.rb',
                '*.yaml', '*.yml', '*.json', '*.xml', '*.html', '*.css'
            ]
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                'node_modules/**', '.git/**', '__pycache__/**', '*.pyc',
                '.DS_Store', 'dist/**', 'build/**', 'target/**', '*.min.js',
                '*.min.css', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'
            ]

@dataclass
class HarvestedDocument:
    """Represents a harvested document"""
    id: str
    source_path: str
    relative_path: str
    title: str
    content: str
    file_type: str
    size: int
    last_modified: datetime
    metadata: Dict

class ManualDirectoryHarvester:
    """
    Harvests knowledge from manually specified directories
    Supports various file types and content extraction
    """

    def __init__(self, kb_instance=None):
        self.kb = kb_instance
        self.extraction_stats = {
            'files_processed': 0,
            'documents_created': 0,
            'bytes_processed': 0,
            'errors': 0
        }

        # Setup logging
        self.logger = self._setup_logging()

        # File type handlers
        self.content_extractors = {
            'text': self._extract_text_content,
            'markdown': self._extract_markdown_content,
            'code': self._extract_code_content,
            'json': self._extract_json_content,
            'yaml': self._extract_yaml_content,
            'xml': self._extract_xml_content,
            'html': self._extract_html_content
        }

    def _setup_logging(self):
        """Setup logging for the harvester"""
        logger = logging.getLogger('ManualDirectoryHarvester')
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not logger.handlers:
            log_path = Path('/Volumes/Active_Mind/logs/manual_harvest.log')
            log_path.parent.mkdir(parents=True, exist_ok=True)

            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # Also log to console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    async def harvest_directory(self, config: DirectoryHarvestConfig) -> List[HarvestedDocument]:
        """
        Harvest knowledge from a specified directory

        Args:
            config: DirectoryHarvestConfig with harvesting parameters

        Returns:
            List of harvested documents
        """
        self.logger.info(f"Starting manual harvest of directory: {config.source_path}")
        self._reset_stats()

        source_path = Path(config.source_path)
        if not source_path.exists():
            raise ValueError(f"Directory does not exist: {config.source_path}")

        documents = []

        try:
            # Walk through directory
            for root, dirs, files in os.walk(source_path):
                root_path = Path(root)
                current_depth = len(root_path.relative_to(source_path).parts)

                # Check depth limit
                if current_depth > config.max_depth:
                    dirs.clear()  # Don't recurse deeper
                    continue

                # Filter directories
                if not config.recursive and root != source_path:
                    dirs.clear()
                    continue

                # Process files in current directory
                for file_path in files:
                    full_path = root_path / file_path

                    # Check if file should be processed
                    if self._should_process_file(full_path, config):
                        try:
                            document = await self._process_file(full_path, source_path)
                            if document:
                                documents.append(document)
                                self.extraction_stats['documents_created'] += 1

                        except Exception as e:
                            self.logger.error(f"Error processing {full_path}: {e}")
                            self.extraction_stats['errors'] += 1

                    self.extraction_stats['files_processed'] += 1

                # Remove excluded directories
                dirs_to_remove = []
                for d in dirs:
                    dir_path = root_path / d
                    if config.exclude_patterns is not None:
                        if any(Path(dir_path).match(pattern) for pattern in config.exclude_patterns):
                            dirs_to_remove.append(d)

                for d in dirs_to_remove:
                    dirs.remove(d)

        except Exception as e:
            self.logger.error(f"Error during directory harvest: {e}")
            raise

        self.logger.info(f"Harvest completed. Processed {self.extraction_stats['files_processed']} files, "
                        f"created {self.extraction_stats['documents_created']} documents, "
                        f"{self.extraction_stats['errors']} errors")

        return documents

    def _should_process_file(self, file_path: Path, config: DirectoryHarvestConfig) -> bool:
        """Check if a file should be processed based on configuration"""

        # Check file size
        try:
            size = file_path.stat().st_size
            if size < config.min_file_size or size > config.max_file_size:
                return False
        except OSError:
            return False

        # Check file patterns
        file_name = file_path.name
        if config.file_patterns is not None:
            if not any(self._matches_pattern(file_name, pattern) for pattern in config.file_patterns):
                return False

        # Check exclude patterns
        relative_path = str(file_path.relative_to(Path(config.source_path)))
        if config.exclude_patterns is not None:
            if any(self._matches_pattern(relative_path, pattern) for pattern in config.exclude_patterns):
                return False

        return True

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a filename matches a pattern (supports wildcards)"""
        import fnmatch
        return fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(name, pattern.replace('**', '*'))

    async def _process_file(self, file_path: Path, source_path: Path) -> Optional[HarvestedDocument]:
        """Process a single file and extract its content"""

        try:
            # Get file metadata
            stat = file_path.stat()
            relative_path = file_path.relative_to(source_path)

            # Determine file type
            file_type = self._determine_file_type(file_path)

            # Extract content based on file type
            content = await self._extract_content(file_path, file_type)

            if not content or len(content.strip()) < 50:  # Skip very short content
                return None

            # Create document
            document = HarvestedDocument(
                id=self._generate_document_id(file_path, stat.st_mtime),
                source_path=str(file_path),
                relative_path=str(relative_path),
                title=self._generate_title(file_path, relative_path),
                content=content,
                file_type=file_type,
                size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                metadata={
                    'file_extension': file_path.suffix,
                    'mime_type': mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream',
                    'harvest_timestamp': datetime.now().isoformat(),
                    'source_type': 'manual_directory_harvest'
                }
            )

            self.extraction_stats['bytes_processed'] += stat.st_size
            return document

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return None

    def _determine_file_type(self, file_path: Path) -> str:
        """Determine the type of file for content extraction"""
        extension = file_path.suffix.lower()

        if extension in ['.md', '.markdown']:
            return 'markdown'
        elif extension in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.php', '.rb']:
            return 'code'
        elif extension in ['.json']:
            return 'json'
        elif extension in ['.yaml', '.yml']:
            return 'yaml'
        elif extension in ['.xml', '.html', '.htm']:
            return 'xml'
        elif extension in ['.txt', '.rst']:
            return 'text'
        else:
            return 'text'  # Default to text extraction

    async def _extract_content(self, file_path: Path, file_type: str) -> str:
        """Extract content from file based on its type"""
        try:
            extractor = self.content_extractors.get(file_type, self.content_extractors['text'])
            return await extractor(file_path)
        except Exception as e:
            self.logger.error(f"Error extracting content from {file_path}: {e}")
            return ""

    async def _extract_text_content(self, file_path: Path) -> str:
        """Extract plain text content"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except:
                return ""

    async def _extract_markdown_content(self, file_path: Path) -> str:
        """Extract markdown content (same as text for now)"""
        return await self._extract_text_content(file_path)

    async def _extract_code_content(self, file_path: Path) -> str:
        """Extract code content with basic structure"""
        content = await self._extract_text_content(file_path)

        # Add basic code structure information
        extension = file_path.suffix.lower()
        if extension == '.py':
            # Extract function and class definitions
            lines = content.split('\n')
            structured_lines = []

            for line in lines:
                stripped = line.strip()
                if (stripped.startswith('def ') or
                    stripped.startswith('class ') or
                    stripped.startswith('async def ') or
                    (stripped.startswith('@') and len(stripped) > 1)):  # Decorators
                    structured_lines.append(f"📝 {line}")
                else:
                    structured_lines.append(line)

            return '\n'.join(structured_lines)
        else:
            return content

    async def _extract_json_content(self, file_path: Path) -> str:
        """Extract JSON content with structure"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert to structured text
            return json.dumps(data, indent=2)
        except:
            return await self._extract_text_content(file_path)

    async def _extract_yaml_content(self, file_path: Path) -> str:
        """Extract YAML content"""
        return await self._extract_text_content(file_path)

    async def _extract_xml_content(self, file_path: Path) -> str:
        """Extract XML/HTML content"""
        return await self._extract_text_content(file_path)

    async def _extract_html_content(self, file_path: Path) -> str:
        """Extract HTML content (basic text extraction)"""
        content = await self._extract_text_content(file_path)

        # Basic HTML tag removal (simple regex-based cleaning)
        import re
        # Remove script and style elements
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        content = re.sub(r'<[^>]+>', ' ', content)

        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content)

        return content.strip()

    def _generate_document_id(self, file_path: Path, modified_time: float) -> str:
        """Generate a unique ID for the document"""
        content = f"{file_path}:{modified_time}"
        return hashlib.md5(content.encode()).hexdigest()

    def _generate_title(self, file_path: Path, relative_path: Path) -> str:
        """Generate a human-readable title for the document"""
        # Use filename without extension as title
        title = file_path.stem

        # If it's in a subdirectory, include path context
        if relative_path.parent != Path('.'):
            title = f"{relative_path.parent}/{title}"

        return title

    def _reset_stats(self):
        """Reset extraction statistics"""
        self.extraction_stats = {
            'files_processed': 0,
            'documents_created': 0,
            'bytes_processed': 0,
            'errors': 0
        }

    def get_stats(self) -> Dict:
        """Get current extraction statistics"""
        return self.extraction_stats.copy()

# Integration function for MCP Orchestrator
async def harvest_directory_for_orchestrator(orchestrator, directory_path: str, **kwargs) -> Dict:
    """
    Convenience function to harvest a directory using the MCP Orchestrator

    Args:
        orchestrator: MCPKnowledgeOrchestrator instance
        directory_path: Path to directory to harvest
        **kwargs: Additional arguments for DirectoryHarvestConfig

    Returns:
        Dict with harvest results and statistics
    """
    harvester = ManualDirectoryHarvester(orchestrator.knowledge_system)

    config = DirectoryHarvestConfig(source_path=directory_path, **kwargs)
    documents = await harvester.harvest_directory(config)

    # Store documents in knowledge base
    stored_count = 0
    for doc in documents:
        try:
            # Convert to knowledge base format
            kb_document = {
                'id': doc.id,
                'source': 'manual_directory',
                'url': f"file://{doc.source_path}",
                'title': doc.title,
                'content': doc.content,
                'metadata': doc.metadata
            }

            # Store in appropriate collection
            collection_name = 'manual_harvest'
            if orchestrator.knowledge_system is not None:
                success = await asyncio.get_event_loop().run_in_executor(
                    None, orchestrator.knowledge_system.add_documents, collection_name, [kb_document]
                )
                if success:
                    stored_count += 1

        except Exception as e:
            print(f"Error storing document {doc.id}: {e}")

    return {
        'status': 'completed',
        'documents_harvested': len(documents),
        'documents_stored': stored_count,
        'stats': harvester.get_stats(),
        'timestamp': datetime.now().isoformat()
    }

# Test function
async def test_manual_harvester():
    """Test the manual directory harvester"""
    print("🧪 Testing Manual Directory Harvester...")

    # Test with the awakened_mind directory itself
    test_config = DirectoryHarvestConfig(
        source_path="/Volumes/NHB_Workspace/awakened_mind",
        recursive=True,
        max_depth=3,
        file_patterns=['*.md', '*.py', '*.txt'],
        min_file_size=50
    )

    harvester = ManualDirectoryHarvester()
    documents = await harvester.harvest_directory(test_config)

    print(f"✅ Harvested {len(documents)} documents")
    print(f"📊 Stats: {harvester.get_stats()}")

    # Show sample documents
    for doc in documents[:3]:
        print(f"📄 {doc.title} ({doc.file_type}, {doc.size} bytes)")

    return documents

if __name__ == "__main__":
    # Run test
    documents = asyncio.run(test_manual_harvester())
