"""
Document Loader for RAG System

General-purpose document loader that handles various file types.
Flexible and unopinionated - doesn't assume document structure or naming patterns.
Focuses only on loading and basic text extraction - does NOT handle chunking or embeddings.
Use with RAGHelper for complete document preparation pipeline.
"""

import os
import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
import logging


@dataclass
class RawDocument:
    """
    Raw document loaded from source before processing.
    Not yet chunked or embedded.
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    
    def __post_init__(self):
        """Validate document has content."""
        if not self.content or not isinstance(self.content, str):
            raise ValueError("Document content must be a non-empty string")


class DocumentLoader:
    """
    General-purpose document loader for RAG pipeline.
    
    Philosophy:
        - Flexible: Works with any file structure
        - Unopinionated: Doesn't assume naming patterns
        - Explicit: Metadata passed by caller, not inferred
        - Simple: Each method does one thing well
    
    Responsibilities:
        - Load files (text, markdown, yaml, json)
        - Extract content
        - Directory scanning with filters
    
    Does NOT:
        - Assume document structure
        - Infer metadata from filenames
        - Chunk text (see RAGHelper)
        - Generate embeddings (see RAGHelper)
        - Store vectors (see VectorStore)
    
    Usage:
        >>> loader = DocumentLoader()
        >>> 
        >>> # Load single file with custom metadata
        >>> doc = loader.load_text_file(
        ...     Path("guide.md"),
        ...     metadata={"brand": "levelup360", "doc_type": "guideline"}
        ... )
        >>> 
        >>> # Load directory with metadata function
        >>> docs = loader.load_files(
        ...     Path("data/docs/"),
        ...     pattern="*.md",
        ...     metadata_fn=lambda p: {"doc_type": "guideline"}
        ... )
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize document loader.
        
        Args:
            base_path: Optional base directory for relative paths
        """
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
        encoding: str = 'utf-8'
    ) -> RawDocument:
        """
        Load a single text file.
        
        Args:
            file_path: Path to text file
            metadata: Optional metadata dict to attach (e.g., {"brand": "x", "doc_type": "y"})
            encoding: File encoding (default: utf-8)
        
        Returns:
            RawDocument with file content and metadata
        
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If encoding is incorrect
        
        Example:
            >>> loader = DocumentLoader()
            >>> doc = loader.load_text_file(
            ...     "guide.md",
            ...     metadata={"brand": "levelup360", "doc_type": "guideline"}
            ... )
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """
        Load a markdown file.
        Convenience method that adds 'markdown' to file_extension.
        
        Args:
            file_path: Path to markdown file
            metadata: Optional metadata dict
        
        Returns:
            RawDocument with markdown content
        
        Example:
            >>> doc = loader.load_markdown_file(
            ...     "brand_guide.md",
            ...     metadata={"brand": "levelup360", "doc_type": "guideline"}
            ... )
        """
        return self.load_text_file(file_path, metadata=metadata)
    
    def load_yaml_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        return_as_text: bool = False
    ) -> Union[RawDocument, Dict[str, Any]]:
        """
        Load a YAML file.
        
        Args:
            file_path: Path to YAML file
            metadata: Optional metadata dict
            return_as_text: If True, return YAML as text in RawDocument
                           If False, return parsed dict directly
        
        Returns:
            RawDocument (if return_as_text=True) or Dict (if return_as_text=False)
        
        Raises:
            yaml.YAMLError: If YAML is invalid
        
        Example:
            >>> # Get parsed YAML dict
            >>> config = loader.load_yaml_file("config.yaml")
            >>> 
            >>> # Get YAML as text document
            >>> doc = loader.load_yaml_file("config.yaml", return_as_text=True)
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
        return_as_text: bool = False
    ) -> Union[RawDocument, Dict[str, Any]]:
        """
        Load a JSON file.
        
        Args:
            file_path: Path to JSON file
            metadata: Optional metadata dict
            return_as_text: If True, return JSON as text in RawDocument
                           If False, return parsed dict directly
        
        Returns:
            RawDocument (if return_as_text=True) or Dict (if return_as_text=False)
        
        Raises:
            json.JSONDecodeError: If JSON is invalid
        
        Example:
            >>> # Get parsed JSON dict
            >>> data = loader.load_json_file("data.json")
            >>> 
            >>> # Get JSON as text document
            >>> doc = loader.load_json_file("data.json", return_as_text=True)
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
        file_loader: Optional[Callable[[Path, Optional[Dict]], RawDocument]] = None
    ) -> List[RawDocument]:
        """
        Load multiple files from a directory - FLEXIBLE and GENERAL-PURPOSE.
        
        Args:
            directory: Directory path containing files
            pattern: Glob pattern for file matching (default: "*.md")
            metadata: Base metadata dict applied to ALL files
            metadata_fn: Optional function to generate per-file metadata
                        Signature: (Path) -> Dict[str, Any]
                        Result is merged with base metadata
            recursive: Whether to search subdirectories
            file_loader: Optional custom file loader function
                        Signature: (Path, Optional[Dict]) -> RawDocument
                        Default: self.load_text_file
        
        Returns:
            List of RawDocument objects
        
        Examples:
            >>> # Simple: Load all markdown files
            >>> docs = loader.load_files(Path("data/docs/"), pattern="*.md")
            >>> 
            >>> # With base metadata for all files
            >>> docs = loader.load_files(
            ...     Path("data/guidelines/"),
            ...     metadata={"doc_type": "guideline"}
            ... )
            >>> 
            >>> # With per-file metadata function
            >>> def get_metadata(path: Path) -> Dict:
            ...     return {"brand": path.stem.split('_')[0]}
            >>> 
            >>> docs = loader.load_files(
            ...     Path("data/brand_docs/"),
            ...     metadata={"doc_type": "guideline"},
            ...     metadata_fn=get_metadata
            ... )
            >>> 
            >>> # With custom file loader
            >>> docs = loader.load_files(
            ...     Path("configs/"),
            ...     pattern="*.yaml",
            ...     file_loader=lambda p, m: loader.load_yaml_file(p, m, return_as_text=True)
            ... )
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
        recursive: bool = False
    ) -> List[RawDocument]:
        """
        Convenience method: Load markdown files from directory.
        
        Args:
            directory: Directory containing markdown files
            metadata: Base metadata for all files
            metadata_fn: Optional function for per-file metadata
            pattern: Glob pattern (default: "*.md")
            recursive: Search subdirectories
        
        Returns:
            List of RawDocument objects
        
        Example:
            >>> docs = loader.load_markdown_files(
            ...     "data/docs/",
            ...     metadata={"doc_type": "guideline", "brand": "levelup360"}
            ... )
        """
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
        """
        Basic text cleaning for document content.
        
        Args:
            text: Raw text content
            preserve_newlines: If True, preserve single newlines
                              If False, collapse all whitespace
        
        Returns:
            Cleaned text
        
        Example:
            >>> raw = "  Line 1  \\n\\n  Line 2  \\n\\n\\n  Line 3  "
            >>> cleaned = DocumentLoader.clean_text(raw)
            >>> print(cleaned)
            Line 1
            Line 2
            Line 3
        """
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
    key: str
) -> Callable[[Path], Dict[str, Any]]:
    """
    Create a metadata extractor function from a simple extraction function.
    
    Args:
        extract_fn: Function that extracts a value from file path
        key: Metadata key to store the extracted value
    
    Returns:
        Metadata extractor function
    
    Example:
        >>> # Extract brand from filename prefix
        >>> extract_brand = create_metadata_extractor(
        ...     lambda p: p.stem.split('_')[0],
        ...     "brand"
        ... )
        >>> 
        >>> loader = DocumentLoader()
        >>> docs = loader.load_files(
        ...     "data/docs/",
        ...     metadata_fn=extract_brand
        ... )
    """
    def extractor(path: Path) -> Dict[str, Any]:
        return {key: extract_fn(path)}
    
    return extractor


def combine_metadata_extractors(
    *extractors: Callable[[Path], Dict[str, Any]]
) -> Callable[[Path], Dict[str, Any]]:
    """
    Combine multiple metadata extractor functions.
    
    Args:
        *extractors: Variable number of metadata extractor functions
    
    Returns:
        Combined metadata extractor
    
    Example:
        >>> extract_brand = create_metadata_extractor(
        ...     lambda p: p.stem.split('_')[0],
        ...     "brand"
        ... )
        >>> 
        >>> extract_type = create_metadata_extractor(
        ...     lambda p: "guideline" if "guide" in p.name else "post",
        ...     "doc_type"
        ... )
        >>> 
        >>> combined = combine_metadata_extractors(extract_brand, extract_type)
        >>> 
        >>> docs = loader.load_files("data/", metadata_fn=combined)
    """
    def combined_extractor(path: Path) -> Dict[str, Any]:
        result = {}
        for extractor in extractors:
            result.update(extractor(path))
        return result
    
    return combined_extractor
