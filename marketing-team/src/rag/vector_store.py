import chromadb
from chromadb import Settings
from chromadb.errors import ChromaError
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
import logging
import datetime


class CollectionMetadata(BaseModel):
    """Collection metadata"""
    model_config = ConfigDict(frozen=True)
    
    description: str = Field(default=None, description="Collection description")
    distance_metric: str = Field(default="cosine", description="Distance metric for similarity search (cosine, l2, or ip)")
    created: str = Field(default=str(datetime.datetime.now()), description="Collection creation timestamp")


class Document(BaseModel):
    """Document batch for adding to vector store"""
    model_config = ConfigDict(frozen=True)
    
    id: str = Field(..., description="Unique document ID")
    text: str = Field(..., description="Document text")
    embeddings: List[float] = Field(..., description="List of document embeddings")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Document metadata dict")


class QueryResult(BaseModel):
    """Result from vector similarity search"""
    model_config = ConfigDict(frozen=True)
    
    ids: List[str] = Field(..., description="List of matched document IDs")
    texts: List[str] = Field(..., description="List of matched document texts")
    distances: List[float] = Field(..., description="List of distances/similarities to the query")
    metadatas: List[Dict[str, Any]] = Field(..., description="List of matched document metadata")


class VectorStore:
    """
    Production-ready vector store wrapper for ChromaDB.
    Provides persistent storage for document embeddings with similarity search capabilities.
    """
    
    def __init__(
        self, 
        persist_directory: str, 
        settings: Optional[Settings] = None
    ):
        """
        Initialize vector store with persistent storage.
        
        Args:
            persist_directory: Directory path for persisting the vector store
            settings: Optional ChromaDB settings (defaults to anonymized_telemetry=False)
        
        Raises:
            ValueError: If persist_directory is empty or invalid
            ChromaError: If ChromaDB client initialization fails
        """
        if not persist_directory or not isinstance(persist_directory, str):
            raise ValueError("persist_directory must be a non-empty string")
        
        self.persist_directory = persist_directory
        self.settings = settings or Settings(anonymized_telemetry=False)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory, 
                settings=self.settings
            )
            self.logger.info(f"Vector store initialized at: {persist_directory}")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise ChromaError(f"ChromaDB initialization failed: {e}") from e

    def get_collection(self, collection_name: str):
        """
        Get an existing collection.
        
        Args:
            collection_name: Name of the collection
        
        Returns:
            ChromaDB collection object
        
        Raises:
            ValueError: If collection_name is empty or invalid
            ChromaError: If collection doesn't exist
        """
        if not collection_name or not isinstance(collection_name, str):
            raise ValueError("collection_name must be a non-empty string")
        
        try:
            collection = self.client.get_collection(name=collection_name)
            self.logger.debug(f"Retrieved collection: {collection_name}")
            return collection
        except Exception as e:
            self.logger.error(f"Collection '{collection_name}' not found: {e}")
            raise ChromaError(f"Collection '{collection_name}' does not exist") from e

    def create_collection(
        self, 
        collection_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Create a new collection with optional metadata.
        
        Args:
            collection_name: Name of the collection
            metadata: Optional collection metadata dict (e.g., {"hnsw:space": "cosine"})
        
        Returns:
            ChromaDB collection object
        
        Raises:
            ValueError: If collection_name is empty or metadata is invalid
            ChromaError: If collection already exists or creation fails
        """
        if not collection_name or not isinstance(collection_name, str):
            raise ValueError("collection_name must be a non-empty string")
        
        # Validate distance metric if provided in metadata
        if metadata and "hnsw:space" in metadata:
            distance_metric = metadata["hnsw:space"]
            if distance_metric not in ["cosine", "l2", "ip"]:
                raise ValueError(f"Invalid distance_metric '{distance_metric}'. Must be: cosine, l2, or ip")
        
        try:
            collection = self.client.create_collection(
                name=collection_name, 
                metadata=metadata or {}
            )
            self.logger.info(f"Created new collection: {collection_name}")
            return collection
        except Exception as e:
            self.logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise ChromaError(f"Failed to create collection (may already exist): {e}") from e

    def get_or_create_collection(
        self, 
        collection_name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Get existing collection or create new one if it doesn't exist.
        Convenience method that combines get_collection() and create_collection().
        
        Args:
            collection_name: Name of the collection
            metadata: Optional metadata for new collection (e.g., {"hnsw:space": "cosine"})
        
        Returns:
            ChromaDB collection object
        
        Raises:
            ValueError: If collection_name is empty or invalid
            ChromaError: If collection operations fail
        """
        try:
            # Try to get existing collection first
            return self.get_collection(collection_name)
        except ChromaError:
            # Collection doesn't exist, create it
            self.logger.info(f"Collection '{collection_name}' not found, creating new one")
            return self.create_collection(collection_name, metadata)   

    def add_documents(
        self, 
        collection_name: str, 
        documents: List[Document]
    ) -> int:
        """
        Add documents with embeddings to the specified collection.
        
        Args:
            collection_name: Name of the target collection
            documents: List of Document objects, each containing id, text, embedding, and metadata
        
        Returns:
            Number of documents successfully added
        
        Raises:
            ValueError: If documents list is invalid or empty
            ChromaError: If adding documents fails
        """
        if not documents or len(documents) == 0:
            raise ValueError("Documents must contain at least one document")
        
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # Extract data from Document objects
            ids = [doc.id for doc in documents]
            texts = [doc.text for doc in documents]
            embeddings = [doc.embeddings for doc in documents]
            # Extract and sanitize metadata for ChromaDB
            def _sanitize_value(val):
                """Return a Chroma-friendly value or None to indicate omission.

                Allowed scalar types: bool, int, float, str.
                For dict/list, recursively sanitize and drop empty results.
                For any other type, convert to str as a fallback.
                """
                try:
                    if val is None:
                        return None
                    if isinstance(val, (bool, int, float, str)):
                        return val
                    if isinstance(val, dict):
                        cleaned = {}
                        for k, v in val.items():
                            sv = _sanitize_value(v)
                            if sv is not None:
                                cleaned[str(k)] = sv
                        return cleaned if cleaned else None
                    if isinstance(val, (list, tuple)):
                        cleaned_list = []
                        for item in val:
                            sv = _sanitize_value(item)
                            if sv is not None:
                                cleaned_list.append(sv)
                        return cleaned_list if cleaned_list else None
                    # Fallback: convert to str
                    return str(val)
                except Exception:
                    # If sanitization fails for any item, skip it
                    return None

            sanitized_metadatas = []
            for doc in documents:
                meta = doc.metadata if getattr(doc, "metadata", None) else {}
                if not isinstance(meta, dict):
                    # Ensure metadata is a dict for consistency
                    meta = {"value": meta}

                cleaned = {}
                for k, v in meta.items():
                    sv = _sanitize_value(v)
                    if sv is not None:
                        cleaned[str(k)] = sv

                # Ensure we always append a dict (possibly empty) for each document
                sanitized_metadatas.append(cleaned)

            # Prepare the data for ChromaDB
            add_kwargs = {
                "ids": ids,
                "documents": texts,
                "embeddings": embeddings,
                "metadatas": sanitized_metadatas,
            }
            
            collection.add(**add_kwargs)
            
            doc_count = len(documents)
            self.logger.info(f"Added {doc_count} documents to collection '{collection_name}'")
            return doc_count
            
        except ValueError as ve:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Failed to add documents to '{collection_name}': {e}")
            raise ChromaError(f"Failed to add documents: {e}") from e

    def query(
        self, 
        collection_name: str, 
        query_embeddings: List[float], 
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        max_distance: Optional[float] = None
    ) -> QueryResult:
        """
        Query the vector store for similar documents using embedding similarity.
        
        Args:
            collection_name: Name of the collection to query
            query_embeddings: Pre-computed embedding vector for the query
            n_results: Maximum number of results to return (default: 5)
            where: Optional metadata filter (e.g., {"brand": "levelup360"})
            where_document: Optional document text filter (e.g., {"$contains": "marketing"})
        
        Filter Examples:
            Metadata filters (where):
                {"brand": "levelup360"}  # Exact match
                {"brand": {"$eq": "levelup360"}}  # Explicit equality
                {"brand": {"$ne": "competitor"}}  # Not equal
                {"brand": {"$in": ["levelup360", "ossienaturals"]}}  # In list
                
            Document text filters (where_document):
                {"$contains": "marketing"}  # Contains text
                {"$not_contains": "competitor"}  # Doesn't contain
                
            Combined filters:
                Both where and where_document can be used together for complex queries
        
        Returns:
            QueryResult containing matched documents, distances, and metadata
        
        Raises:
            ValueError: If query_embeddings is empty or n_results is invalid
            ChromaError: If collection doesn't exist or query operation fails
        """
        if not query_embeddings or not isinstance(query_embeddings, list):
            raise ValueError("query_embeddings must be a non-empty list of floats")
        
        if n_results < 1:
            raise ValueError(f"n_results must be at least 1, got {n_results}")
        
        try:
            collection = self.get_collection(collection_name)
        except ChromaError:
            # Re-raise with more context
            raise
        
        try:
            query_kwargs = {
                "query_embeddings": [query_embeddings],
                "n_results": n_results
            }
            
            # Add metadata filter if provided
            if where is not None:
                query_kwargs["where"] = where
            
            # Add document text filter if provided
            if where_document is not None:
                query_kwargs["where_document"] = where_document

            results = collection.query(**query_kwargs)

            # Normalize ChromaDB nested list results to flat lists (first result batch)
            ids_list = results.get('ids', [[]])[0]
            docs_list = results.get('documents', [[]])[0]
            dists_list = results.get('distances', [[]])[0]
            metas_list = results.get('metadatas', [[]])[0]

            # Handle empty results
            if not ids_list or len(ids_list) == 0:
                filter_info = []
                if where:
                    filter_info.append(f"where={where}")
                if where_document:
                    filter_info.append(f"where_document={where_document}")
                filter_str = f" with filters: {', '.join(filter_info)}" if filter_info else ""

                self.logger.warning(f"No results found for query in collection '{collection_name}'{filter_str}")
                return QueryResult(ids=[], texts=[], distances=[], metadatas=[])

            # Optional distance-based filtering
            if max_distance is not None:
                filtered = []
                for _id, doc, dist, meta in zip(ids_list, docs_list, dists_list, metas_list):
                    try:
                        if dist is None:
                            continue
                        # Chroma distances may be similarity or distance depending on metric; assume lower is better
                        if float(dist) <= float(max_distance):
                            filtered.append((_id, doc, dist, meta))
                    except Exception:
                        # Skip malformed distance entries
                        continue

                if not filtered:
                    self.logger.info(f"No matches within max_distance={max_distance} for collection '{collection_name}'")
                    return QueryResult(ids=[], texts=[], distances=[], metadatas=[])

                ids_list, docs_list, dists_list, metas_list = zip(*filtered)
                ids_list = list(ids_list)
                docs_list = list(docs_list)
                dists_list = list(dists_list)
                metas_list = list(metas_list)

            self.logger.debug(f"Query returned {len(ids_list)} results from '{collection_name}'")

            return QueryResult(
                ids=ids_list,
                texts=docs_list,
                distances=dists_list,
                metadatas=metas_list
            )
            
        except Exception as e:
            self.logger.error(f"Query failed on collection '{collection_name}': {e}")
            raise ChromaError(f"Query operation failed: {e}") from e

    def get_document_count(self, collection_name: str) -> int:
        """
        Get the total number of documents in the collection.
        
        Args:
            collection_name: Name of the collection
        
        Returns:
            Total number of documents in the collection
        
        Raises:
            ChromaError: If collection doesn't exist or count operation fails
        """
        try:
            collection = self.get_collection(collection_name)
            count = collection.count()
            self.logger.debug(f"Collection '{collection_name}' contains {count} documents")
            return count
            
        except ChromaError:
            # Re-raise
            raise
        except Exception as e:
            self.logger.error(f"Failed to get document count for '{collection_name}': {e}")
            raise ChromaError(f"Failed to get document count: {e}") from e

    def clear_collection(
        self, 
        collection_name: str
    ) -> None:
        """
        Delete and recreate a collection, preserving its metadata.
        This effectively clears all documents while keeping the collection configuration.
        
        Args:
            collection_name: Name of the collection to clear
        
        Raises:
            ValueError: If collection_name is empty
            ChromaError: If collection doesn't exist or clear operation fails
        """
        if not collection_name or not isinstance(collection_name, str):
            raise ValueError("collection_name must be a non-empty string")

        try:
            # First, try to get the collection to preserve metadata
            collection = self.get_collection(collection_name)
            metadata = collection.metadata
            self.logger.info(f"Retrieved metadata from collection '{collection_name}': {metadata}")
            
            # Delete the collection
            self.client.delete_collection(name=collection_name)
            self.logger.info(f"Deleted collection: {collection_name}")
            
            # Recreate it with the same metadata
            metadata["created"] = str(datetime.datetime.now())
            self.create_collection(collection_name, metadata)
            self.logger.info(f"Recreated empty collection '{collection_name}' with preserved metadata")
            
        except ValueError:
            # Re-raise validation errors
            raise
        except ChromaError as ce:
            # Collection doesn't exist
            self.logger.error(f"Cannot clear non-existent collection '{collection_name}'")
            raise
        except Exception as e:
            self.logger.error(f"Failed to clear collection '{collection_name}': {e}")
            raise ChromaError(f"Failed to clear collection: {e}") from e
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Permanently delete a collection and all its documents.
        
        Args:
            collection_name: Name of the collection to delete
        
        Raises:
            ValueError: If collection_name is empty
            ChromaError: If delete operation fails
        """
        if not collection_name or not isinstance(collection_name, str):
            raise ValueError("collection_name must be a non-empty string")
        
        try:
            self.client.delete_collection(name=collection_name)
            self.logger.info(f"Permanently deleted collection: {collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete collection '{collection_name}': {e}")
            raise ChromaError(f"Failed to delete collection: {e}") from e
    
    def list_collections(self) -> List[str]:
        """
        List all collection names in the vector store.
        
        Returns:
            List of collection names
        
        Raises:
            ChromaError: If list operation fails
        """
        try:
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]
            self.logger.debug(f"Found {len(collection_names)} collections")
            return collection_names
            
        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            raise ChromaError(f"Failed to list collections: {e}") from e


        
        