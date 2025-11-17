"""
RAG Helper Utilities

Provides helper functions for preparing documents for RAG (Retrieval Augmented Generation).
Handles chunking, embedding generation, and Document object creation.
Keeps embedding logic separate from vector store for flexibility and testability.

Works seamlessly with DocumentLoader to create a complete document processing pipeline:
    DocumentLoader → RawDocument → RAGHelper → Document → VectorStore
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import tiktoken
import yaml
from rich import print as rprint
from src.core.rag.vector_store import Document
from src.infrastructure.llm.llm_client import LLMClient

# Avoid circular import
if TYPE_CHECKING:
    from rag.document_loader import RawDocument


class RAGHelper:
    """
    Helper class for preparing documents for vector storage.
    Handles chunking and embedding generation, keeping these concerns
    separate from the vector store implementation.
    """
    
    def __init__(
        self, 
        embedding_client: LLMClient,
        embedding_model: str = "text-embedding-3-small",
        chunk_size: int = 150,
        chunk_overlap: int = 30,
        chunk_threshold: int = 150
    ):
        """
        Initialize RAG helper with embedding client and chunking parameters.
        
        Args:
            embedding_client: LLM client configured for embeddings
            embedding_model: Model to use for embeddings
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
            chunk_threshold: Token threshold above which documents are chunked
        """
        self.embedding_client = embedding_client
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_threshold = chunk_threshold
        
        # Initialize tokenizer for the embedding model
        self.encoding = tiktoken.encoding_for_model(embedding_model)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors (one per input text)
        
        Example:
            >>> helper = RAGHelper(embedding_client)
            >>> embeddings = helper.embed_batch(["text 1", "text 2"])
            >>> len(embeddings)  # 2
            >>> len(embeddings[0])  # 1536 (for text-embedding-3-small)
        """
        embeddings = []
        for text in texts:
            result = self.embedding_client.get_embedding(model=self.embedding_model, text=text)
            embeddings.append(result.embedding)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Generate an embedding for a single query/text string.

        This is a convenience wrapper around `embed_batch` / the underlying
        embedding client that avoids creating a temporary list at call sites.

        Args:
            text: Single text string to embed

        Returns:
            Embedding vector for the provided text

        Example:
            >>> helper = RAGHelper(embedding_client)
            >>> vec = helper.embed_query("skin")
        """
        result = self.embedding_client.get_embedding(model=self.embedding_model, text=text)
        return result.embedding
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into overlapping segments based on token count.
        
        Args:
            text: The text to chunk
        
        Returns:
            List of text chunks
        """
        tokens = self.encoding.encode(text)
        token_count = len(tokens)
        
        # Don't chunk if below threshold
        if token_count <= self.chunk_threshold:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunks.append(self.encoding.decode(chunk_tokens))
            start += self.chunk_size - self.chunk_overlap
        
        return chunks
    
    def prepare_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ) -> List[Document]:
        """
        Prepare a single document for vector storage.
        Handles chunking and embedding generation.
        
        Args:
            doc_id: Base identifier for the document
            content: Document text content
            metadata: Optional metadata to attach to document chunks
            verbose: Whether to print progress information
        
        Returns:
            List of Document objects ready for vector storage
        """
        # Count tokens
        token_count = len(self.encoding.encode(content))
        
        if verbose:
            rprint(f"  Processing '{doc_id}' ({len(content):,} chars, {token_count:,} tokens)")
        
        # Chunk the content
        chunks = self.chunk_text(content)
        
        if verbose and len(chunks) > 1:
            rprint(f"    Split into {len(chunks)} chunks")
        
        # Process each chunk
        documents = []
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding_result = self.embedding_client.get_embedding(
                model=self.embedding_model,
                text=chunk,
            )
            
            # Create unique ID for chunk
            chunk_id = f"{doc_id}_chunk_{i}" if len(chunks) > 1 else doc_id
            
            # Prepare metadata
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_index": i if len(chunks) > 1 else 0,
                "total_chunks": len(chunks),
                "token_count": len(self.encoding.encode(chunk))
            })
            
            # Create Document object
            doc = Document(
                id=chunk_id,
                text=chunk,
                embeddings=embedding_result.embedding,
                metadata=chunk_metadata
            )
            documents.append(doc)
        
        return documents
    
    def prepare_raw_document(
        self,
        raw_doc: 'RawDocument',
        doc_id: Optional[str] = None,
        verbose: bool = False
    ) -> List[Document]:
        """
        Prepare a RawDocument (from DocumentLoader) for vector storage.
        Handles chunking and embedding generation.
        
        Args:
            raw_doc: RawDocument object from DocumentLoader
            doc_id: Optional custom doc_id (uses raw_doc metadata if not provided)
            verbose: Whether to print progress information
        
        Returns:
            List of Document objects ready for vector storage
        
        Example:
            >>> from rag.document_loader import DocumentLoader
            >>> 
            >>> loader = DocumentLoader()
            >>> raw_doc = loader.load_markdown_file(Path("brand_guide.md"))
            >>> 
            >>> helper = RAGHelper(embedding_client)
            >>> documents = helper.prepare_raw_document(raw_doc)
        """
        # Generate doc_id if not provided
        if doc_id is None:
            doc_id = raw_doc.metadata.get('filename', 'document')
            if '.' in doc_id:
                doc_id = doc_id.rsplit('.', 1)[0]  # Remove extension
        
        return self.prepare_document(
            doc_id=doc_id,
            content=raw_doc.content,
            metadata=raw_doc.metadata,
            verbose=verbose
        )
    
    def prepare_raw_documents(
        self,
        raw_docs: List['RawDocument'],
        verbose: bool = True
    ) -> List[Document]:
        """
        Prepare multiple RawDocuments (from DocumentLoader) for vector storage.
        
        Args:
            raw_docs: List of RawDocument objects from DocumentLoader
            verbose: Whether to print progress information
        
        Returns:
            List of all Document objects ready for vector storage
        
        Example:
            >>> from rag.document_loader import DocumentLoader
            >>> 
            >>> loader = DocumentLoader()
            >>> raw_docs = loader.load_markdown_files(Path("data/brand_docs/"))
            >>> 
            >>> helper = RAGHelper(embedding_client)
            >>> documents = helper.prepare_raw_documents(raw_docs)
        """
        if verbose:
            rprint(f"\nProcessing {len(raw_docs)} documents...")
        
        all_documents = []
        
        for raw_doc in raw_docs:
            docs = self.prepare_raw_document(raw_doc, verbose=verbose)
            all_documents.extend(docs)
        
        if verbose:
            rprint(f"\nPrepared {len(all_documents)} document chunks total")
        
        return all_documents
    
    def prepare_documents_from_files(
        self,
        file_paths: List[Path],
        metadata_extractor: Optional[callable] = None,
        verbose: bool = True
    ) -> List[Document]:
        """
        Prepare multiple documents from files for vector storage.
        
        Args:
            file_paths: List of file paths to process
            metadata_extractor: Optional function to extract metadata from file path
                                Signature: (Path) -> Dict[str, Any]
            verbose: Whether to print progress information
        
        Returns:
            List of all Document objects ready for vector storage
        
        Example:
            >>> def extract_brand(file_path: Path) -> Dict[str, Any]:
            ...     brand_name = file_path.stem.split('_')[0]
            ...     return {"brand": brand_name, "source_file": file_path.name}
            >>> 
            >>> helper = RAGHelper(embedding_client)
            >>> documents = helper.prepare_documents_from_files(
            ...     file_paths=[Path("levelup360_guide.md")],
            ...     metadata_extractor=extract_brand
            ... )
        """
        if verbose:
            rprint(f"\nProcessing {len(file_paths)} files...")
        
        all_documents = []
        
        for file_path in file_paths:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata if function provided
            metadata = metadata_extractor(file_path) if metadata_extractor else {}
            
            # Prepare documents from this file
            docs = self.prepare_document(
                doc_id=file_path.stem,
                content=content,
                metadata=metadata,
                verbose=verbose
            )
            
            all_documents.extend(docs)
        
        if verbose:
            rprint(f"\nPrepared {len(all_documents)} document chunks total")
        
        return all_documents
    
    def prepare_past_posts(
        self,
        raw_posts: List['RawDocument'],
        verbose: bool = False
    ) -> List[Document]:
        """
        Prepare past LinkedIn/Facebook posts from RawDocuments with YAML frontmatter.
        Extracts clean post content and engagement metadata for vector storage.
        
        Expected RawDocument.content structure:
            ---
            brand: xxx
            post_type: i.e. linkedin_post
            published_date: 2025-09-09
            topic: xxxx
            platform: linkedin
            url: https://...
            engagement_known: true
            likes: 3
            comments: 0
            shares: 1
            impressions: 188
            engagement_rate: 2.12
            ---
            
            <!-- Comments ignored -->
            
            # Post Content
            
            Actual post text here...
            
            ---
        
        Args:
            raw_posts: List of RawDocument objects (loaded via DocumentLoader)
            verbose: Whether to print progress information
        
        Returns:
            List of Document objects ready for vector storage (with embeddings)
        
        Example:
            >>> from rag.document_loader import DocumentLoader
            >>> 
            >>> loader = DocumentLoader()
            >>> raw_posts = loader.load_markdown_files(Path("data/past_posts/levelup360"))
            >>> 
            >>> helper = RAGHelper(llm_client)
            >>> posts = helper.prepare_past_posts(raw_posts, verbose=True)
            >>> vector_store.add_documents("marketing_content", posts)
        """
        if verbose:
            rprint(f"\n[cyan]Processing {len(raw_posts)} past posts...[/cyan]")
        
        all_documents = []
        processed_count = 0
        
        for raw_post in raw_posts:
            try:
                raw_content = raw_post.content
                
                # Parse YAML frontmatter
                frontmatter = {}
                content = raw_content
                
                if raw_content.startswith('---'):
                    parts = raw_content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                        content = parts[2].strip()
                
                # Extract post content (after "# Post Content" marker)
                if "# Post Content" in content:
                    post_content = content.split("# Post Content", 1)[1].strip()
                else:
                    post_content = content
                
                # Remove footer (everything after final ---)
                if "\n---" in post_content:
                    post_content = post_content.split("\n---")[0].strip()
                
                # Skip if no actual content
                if not post_content or len(post_content.strip()) < 10:
                    if verbose:
                        filename = raw_post.metadata.get('filename', 'unknown')
                        rprint(f"  [yellow]Skipping {filename} - no content[/yellow]")
                    continue
                
                # Build metadata from frontmatter + original metadata
                metadata = {
                    "brand": frontmatter.get('brand', 'unknown'),
                    "topic": frontmatter.get('topic', 'unknown'),
                    "post_type": frontmatter.get('post_type', 'unknown'),
                    "platform": frontmatter.get('platform', 'unknown'),
                    "published_date": str(frontmatter.get('published_date', 'unknown')),
                    "engagement_rate": float(frontmatter.get('engagement_rate', 0.0)),
                    "likes": int(frontmatter.get('likes', 0)),
                    "comments": int(frontmatter.get('comments', 0)),
                    "shares": int(frontmatter.get('shares', 0)),
                    "impressions": int(frontmatter.get('impressions', 0)),
                    "url": frontmatter.get('url', ''),
                    "doc_type": "past_post",
                    "source": raw_post.metadata.get('source', raw_post.metadata.get('filename', 'unknown'))
                }
                
                # Generate doc_id from filename
                filename = raw_post.metadata.get('filename', f'post_{processed_count}')
                doc_id = filename.rsplit('.', 1)[0] if '.' in filename else filename
                
                # Use the standard prepare_document method to handle chunking and embeddings
                documents = self.prepare_document(
                    doc_id=doc_id,
                    content=post_content,
                    metadata=metadata,
                    verbose=verbose
                )
                
                all_documents.extend(documents)
                processed_count += 1
                
            except Exception as e:
                filename = raw_post.metadata.get('filename', 'unknown')
                rprint(f"[red]Error processing {filename}: {e}[/red]")
                continue
        
        if verbose:
            rprint(f"\n[green]Prepared {len(all_documents)} document chunks from {processed_count} posts[/green]")
        
        return all_documents


# Convenience function for simple use cases
def prepare_text_for_rag(
    text: str,
    embedding_client: LLMClient,
    doc_id: str = "document",
    metadata: Optional[Dict[str, Any]] = None,
    embedding_model: str = "text-embedding-3-small"
) -> List[Document]:
    """
    Convenience function to quickly prepare text for RAG.
    
    Args:
        text: Text content to prepare
        embedding_client: LLM client for generating embeddings
        doc_id: Identifier for the document
        metadata: Optional metadata dict
        embedding_model: Embedding model to use
    
    Returns:
        List of Document objects ready for vector storage
    
    Example:
        >>> client = LLMClient()
        >>> client.get_client("azure")
        >>> docs = prepare_text_for_rag(
        ...     "This is my document content...",
        ...     client,
        ...     doc_id="my_doc",
        ...     metadata={"source": "manual"}
        ... )
    """
    helper = RAGHelper(embedding_client, embedding_model)
    return helper.prepare_document(doc_id=doc_id, content=text, metadata=metadata)
