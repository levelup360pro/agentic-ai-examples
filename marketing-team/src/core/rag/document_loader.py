"""Lightweight document loading utilities for the RAG pipeline.

Focus: file I/O + basic text extraction ONLY. No chunking, embedding, vector
storage, or metadata inference. Pairs with ``RAGHelper`` and ``VectorStore``
for the full preparation flow.

Public API
    RawDocument, DocumentLoader, create_metadata_extractor, combine_metadata_extractors

Notes
    - Keeps responsibilities narrow and explicit (Separation of Concerns)
    - Metadata is caller-provided (Explicit over implicit)
    - Convenience helpers compose small extractor functions
"""
import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
import logging


@dataclass
class RawDocument:
    """In-memory representation of a source file prior to processing.

    Contains raw text plus user-supplied (and minimal auto) metadata. Not
    chunked or embedded yet.
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    
    def __post_init__(self):
        """Validate document has content."""
        if not self.content or not isinstance(self.content, str):
            raise ValueError("Document content must be a non-empty string")


class DocumentLoader:
    """Load raw files (text/markdown/YAML/JSON) with optional metadata.

    Responsibilities
        - File reading and basic content extraction
        - Directory globbing (with optional recursion)
        - Optional per-file metadata enrichment via user functions

    Exclusions
        - No structural inference or filename parsing heuristics
        - No chunking (``RAGHelper`` handles this)
        - No embedding or vector persistence
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize loader with optional base directory."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def load_text_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        encoding: str = 'utf-8',
    ) -> RawDocument:
        """Load a plain text/markdown file.

        Args:
            file_path: Target file path.
            metadata: Optional metadata dict.
            encoding: File encoding (default UTF-8).
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Build metadata
            doc_metadata = metadata.copy() if metadata else {}
            
            # Add automatic file info (can be overridden by user metadata)
            auto_metadata = {
                "filename": file_path.name,
                "file_extension": file_path.suffix,
                "file_size_bytes": file_path.stat().st_size
            }
            # User metadata takes precedence
            doc_metadata = {**auto_metadata, **doc_metadata}
            
            self.logger.debug(f"Loaded file: {file_path.name} ({len(content)} chars)")
            
            return RawDocument(
                content=content,
                metadata=doc_metadata,
                source=str(file_path)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load file '{file_path}': {e}")
            raise
    
    def load_markdown_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RawDocument:
        """Load a markdown file (delegates to ``load_text_file``)."""
        return self.load_text_file(file_path, metadata=metadata)
    
    def load_yaml_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        return_as_text: bool = False,
    ) -> Union[RawDocument, Dict[str, Any]]:
        """Load YAML returning parsed dict or raw text document.

        Args:
            file_path: Path to YAML file.
            metadata: Optional metadata for text mode.
            return_as_text: True to wrap as ``RawDocument``; False for parsed dict.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()
                parsed_data = yaml.safe_load(yaml_content)
            
            if return_as_text:
                doc_metadata = metadata.copy() if metadata else {}
                doc_metadata.update({
                    "filename": file_path.name,
                    "file_extension": ".yaml",
                    "content_type": "yaml"
                })
                
                return RawDocument(
                    content=yaml_content,
                    metadata=doc_metadata,
                    source=str(file_path)
                )
            else:
                return parsed_data
            
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in '{file_path}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load YAML file '{file_path}': {e}")
            raise
    
    def load_json_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        return_as_text: bool = False,
    ) -> Union[RawDocument, Dict[str, Any]]:
        """Load JSON returning parsed dict or raw text document.

        Args:
            file_path: Path to JSON file.
            metadata: Optional metadata for text mode.
            return_as_text: True to wrap as ``RawDocument``; False for parsed dict.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
                parsed_data = json.loads(json_content)
            
            if return_as_text:
                doc_metadata = metadata.copy() if metadata else {}
                doc_metadata.update({
                    "filename": file_path.name,
                    "file_extension": ".json",
                    "content_type": "json"
                })
                
                return RawDocument(
                    content=json_content,
                    metadata=doc_metadata,
                    source=str(file_path)
                )
            else:
                return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in '{file_path}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load JSON file '{file_path}': {e}")
            raise
    
    def load_files(
        self,
        directory: Union[str, Path],
        pattern: str = "*.md",
        metadata: Optional[Dict[str, Any]] = None,
        metadata_fn: Optional[Callable[[Path], Dict[str, Any]]] = None,
        recursive: bool = False,
        file_loader: Optional[Callable[[Path, Optional[Dict]], RawDocument]] = None,
    ) -> List[RawDocument]:
        """Load many files via glob with optional per-file metadata.

        Args:
            directory: Directory to scan.
            pattern: Glob pattern (default *.md).
            metadata: Base metadata applied to every file.
            metadata_fn: Function producing per-file metadata (merged after base).
            recursive: Whether to search subdirectories.
            file_loader: Alternate single-file loader (defaults to ``load_text_file``).
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")
        
        # Find files
        if recursive:
            file_paths = list(directory.rglob(pattern))
        else:
            file_paths = list(directory.glob(pattern))
        
        self.logger.info(f"Found {len(file_paths)} files matching '{pattern}' in {directory}")
        
        # Use custom loader or default
        loader_fn = file_loader if file_loader else self.load_text_file
        
        documents = []
        for file_path in file_paths:
            # Build metadata for this file
            file_metadata = metadata.copy() if metadata else {}
            
            # Apply per-file metadata function if provided
            if metadata_fn:
                per_file_meta = metadata_fn(file_path)
                file_metadata.update(per_file_meta)
            
            try:
                doc = loader_fn(file_path, file_metadata)
                documents.append(doc)
            except Exception as e:
                self.logger.warning(f"Skipping file '{file_path}': {e}")
                continue
        
        self.logger.info(f"Successfully loaded {len(documents)} documents")
        return documents
    
    # Convenience methods for common patterns
    def load_markdown_files(
        self,
        directory: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        metadata_fn: Optional[Callable[[Path], Dict[str, Any]]] = None,
        pattern: str = "*.md",
        recursive: bool = False,
    ) -> List[RawDocument]:
        """Convenience wrapper restricting ``load_files`` to markdown."""
        return self.load_files(
            directory=directory,
            pattern=pattern,
            metadata=metadata,
            metadata_fn=metadata_fn,
            recursive=recursive,
            file_loader=self.load_markdown_file
        )
    
    @staticmethod
    def clean_text(text: str, preserve_newlines: bool = True) -> str:
        """Small utility to normalize whitespace in content."""
        if preserve_newlines:
            # Remove excessive whitespace but preserve single newlines
            lines = [line.strip() for line in text.split('\n')]
            text = '\n'.join(line for line in lines if line)
        else:
            # Collapse all whitespace to single spaces
            text = ' '.join(text.split())
        
        return text


# Convenience functions for common use cases
def create_metadata_extractor(
    extract_fn: Callable[[Path], Any],
    key: str,
) -> Callable[[Path], Dict[str, Any]]:
    """Wrap a single-value extraction function into metadata dict producer."""
    def extractor(path: Path) -> Dict[str, Any]:
        return {key: extract_fn(path)}
    
    return extractor


def combine_metadata_extractors(
    *extractors: Callable[[Path], Dict[str, Any]]
) -> Callable[[Path], Dict[str, Any]]:
    """Compose multiple metadata extractor functions into one."""
    def combined_extractor(path: Path) -> Dict[str, Any]:
        result = {}
        for extractor in extractors:
            result.update(extractor(path))
        return result
    
    return combined_extractor
