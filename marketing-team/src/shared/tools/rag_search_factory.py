"""RAG (internal content) search tool factory for agent flows.

This module exposes a single factory, ``create_rag_search_tool``, which
returns a LangChain-compatible ``@tool`` callable for searching internal
brand content (past posts, brand guidelines, and other indexed materials).
The tool hides vector store details behind a simple, stable output shape.

Public API
    create_rag_search_tool(vector_store, rag_helper, valid_brands, ...) -> Callable

Notes
    - Uses dependency injection so the returned tool is easy to test and reuse.
    - Returned tool yields a small dict with ``query``, ``brand``, ``summary``,
      ``results`` (ranked snippets), ``result_count``, and optional ``error``.
"""
from typing import Dict, Any, Callable, List
from langchain.tools import tool
import logging
from src.core.rag.vector_store import VectorStore
from src.core.rag.rag_helper import RAGHelper
from src.shared.formatters.tool_formatters import format_query_results_for_llm

logger = logging.getLogger(__name__)

def create_rag_search_tool(
    vector_store: VectorStore,
    rag_helper: RAGHelper,
    valid_brands: List[str],
    collection_name: str = "marketing_content",
    max_results: int = 5,
    max_distance: float = 0.50,
    name: str = "rag_search"
) -> Callable:
    """Return a LangChain ``@tool`` for internal RAG lookups.

    Args:
        vector_store: VectorStore instance used to run similarity queries.
        rag_helper: RAGHelper providing embedding helpers and document utils.
        valid_brands: List of allowed brand keys (used to validate input).
        collection_name: Name of the vector collection to query.
        max_results: Number of results to return per query.
        max_distance: Maximum distance threshold (smaller is closer/more similar).
        name: Tool name to expose to the LLM.

    Returns:
        A callable `rag_search(query: str, brand: str) -> Dict[str, Any]`
        decorated with `@tool` that performs an embedding-based search and
        returns a standardized result dictionary.
    """

    @tool
    def rag_search(query: str, brand: str) -> Dict[str, Any]:
        """Run an internal RAG search for brand-specific content.

            Behavior:
            - Validates `brand` is in `valid_brands`.
            - Uses `rag_helper.embed_query` to produce a single embedding for the
                provided `query`.
            - Calls `vector_store.query(...)` and converts returned hits into a
                compact `results` list containing `rank`, `content`,
                `relevance_score` and `metadata`.

            Args:
                    query: Free-text query to search for (e.g., "brand voice examples").
                    brand: Brand key used to filter indexed documents.

            Returns:
                    A dict with the following keys:
                    - `query` (str): original query
                    - `brand` (str): brand used for filtering
                    - `summary` (str): short human-friendly summary
                    - `results` (List[Dict]): list of search hits (may be empty)
                    - `result_count` (int): number of returned hits
                    - `error` (str, optional): present on failure

            Errors are logged and returned in the `error` field to keep agent
            execution robust (do not raise from inside the tool).
        """

        try:
            # Validate brand early to avoid unnecessary work
            if brand not in valid_brands:
                return {
                    "query": query,
                    "brand": brand,
                    "summary": f"Invalid brand. Must be one of: {valid_brands}",
                    "results": [],
                    "error": "Invalid brand parameter"
                }

            # Prepare a simple metadata filter for the vector store
            metadata_filter = {"brand": brand}

            # Generate a single embedding for the free-text query
            query_embeddings = rag_helper.embed_query(text=query)

            if not query_embeddings or len(query_embeddings) == 0:
                return {
                    "query": query,
                    "brand": brand,
                    "summary": "Embedding generation failed",
                    "results": [],
                    "error": "Could not generate query embedding"
                }

            # Perform vector search with collection + brand filter
            rag_results = vector_store.query(
                collection_name=collection_name,
                query_embeddings=query_embeddings,
                n_results=max_results,
                where={"brand": brand},  
                max_distance=max_distance)

            # Convert QueryResult to a compact, LLM-friendly structure
            formatted_results = format_query_results_for_llm(
                rag_results=rag_results,
                query=query,
                brand=brand,
                max_content_length=2000  # Only truncate if excessive
            )    

            return formatted_results

        except Exception as e:
            error_msg = str(e)
            logger.error(f"RAG search failed for brand '{brand}': {error_msg}",
                         exc_info=True)

            return {
                "query": query,
                "brand": brand,
                "summary": f"Search failed: {error_msg[:100]}",
                "results": [],
                "error": error_msg
            }

    # Expose a stable tool name (as seen by the LLM/tool-calling runtime)
    rag_search.name = name
    return rag_search