"""Format raw tool outputs into LLM-friendly structured dicts.

Transforms provider / vector / search results (Pydantic objects or plain
dicts) into compact, semantically meaningful dictionaries optimized for
prompt injection. Keeps responsibilities narrow: no network calls, no
post-processing beyond safe truncation and score transformation.

Public API
    format_query_results_for_llm
    format_search_results_for_llm
    format_generic_results_for_llm

Principles
    - Tools fetch raw data; formatters adapt it for model consumption
    - Remove irrelevant identifiers while preserving useful metadata
    - Convert distances to relevance (higher better) without hiding raw values
    - Truncate only when genuinely excessive (> max_content_length)
    - Always return dict structures (never free-form strings)
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def format_query_results_for_llm(
    rag_results,  # QueryResult Pydantic object from VectorStore
    query: str,
    brand: str,
    max_content_length: int = 2000,
) -> Dict[str, Any]:
    """Format similarity search results for LLM use.

    Args:
        rag_results: ``QueryResult`` instance from vector store.
        query: Original query string.
        brand: Brand identifier used for summary text.
        max_content_length: Maximum characters retained per document.
    """
    try:
        formatted_results = []
        
        # Iterate through parallel lists from QueryResult
        for i, (doc_id, text, distance, metadata) in enumerate(
            zip(
                rag_results.ids,
                rag_results.texts,
                rag_results.distances,
                rag_results.metadatas
            ),
            1  # Start rank at 1
        ):
            # Truncate only if genuinely excessive
            content = text
            if len(text) > max_content_length:
                content = text[:max_content_length] + "... [truncated]"
                logger.debug(f"Truncated result {i} from {len(text)} to {max_content_length} chars")
            
            formatted_results.append({
                "rank": i,
                "content": content,
                "relevance_score": round(1.0 - distance, 3),  # Distance to similarity (0.2 distance = 0.8 relevance)
                "metadata": metadata  # Keep all metadata (might be useful for generation)
            })
        
        # Build summary
        if not formatted_results:
            summary = f"No {brand} content found for: {query}"
        else:
            summary = f"Found {len(formatted_results)} relevant {brand} content examples"
        
        return {
            "query": query,
            "brand": brand,
            "summary": summary,
            "results": formatted_results,
            "result_count": len(formatted_results)
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to format query results: {error_msg}", exc_info=True)
        
        # Return error structure (don't raise exception)
        return {
            "query": query,
            "brand": brand,
            "summary": f"Formatting failed: {error_msg[:100]}",
            "results": [],
            "result_count": 0,
            "error": error_msg
        }


def format_search_results_for_llm(
    search_results: List[Dict],  # Raw Tavily search results
    query: str,
    optimized_query: str = None,
    max_content_length: int = 2000,
) -> Dict[str, Any]:
    """Format web search results into ranked source list.

    Args:
        search_results: List of result dicts (content, url, score expected).
        query: Original user query.
        optimized_query: Optional compressed/rewritten query for context.
        max_content_length: Maximum characters retained per source content.
    """
    try:
        if not search_results:
            result = {
                "query": query,
                "summary": "No results found",
                "sources": [],
                "source_count": 0
            }
            if optimized_query:
                result["optimized_query"] = optimized_query
            return result
        
        # Format sources
        sources = []
        for i, result in enumerate(search_results, 1):
            # Truncate only if genuinely excessive
            content = result.get("content", "")
            if len(content) > max_content_length:
                content = content[:max_content_length] + "... [truncated]"
                logger.debug(f"Truncated source {i} from {len(result.get('content', ''))} to {max_content_length} chars")
            
            sources.append({
                "rank": i,
                "content": content,  # Full content (Tavily already optimized)
                "url": result.get("url", ""),
                "score": result.get("score", 0.0)
            })
        
        # Build summary from first result
        summary = search_results[0].get("content", "")
        if len(summary) > 500:  # Summarize the summary if very long
            summary = summary[:500] + "..."
        
        result = {
            "query": query,
            "summary": summary,
            "sources": sources,
            "source_count": len(sources)
        }
        
        # Add optimized query if provided
        if optimized_query:
            result["optimized_query"] = optimized_query
        
        return result
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to format search results: {error_msg}", exc_info=True)
        
        result = {
            "query": query,
            "summary": f"Formatting failed: {error_msg[:100]}",
            "sources": [],
            "source_count": 0,
            "error": error_msg
        }
        
        if optimized_query:
            result["optimized_query"] = optimized_query
        
        return result


def format_generic_results_for_llm(
    results: List[Dict],
    query: str,
    result_type: str = "results",
    content_key: str = "content",
    score_key: str = "score",
    max_content_length: int = 2000,
) -> Dict[str, Any]:
    """Generic adapter for arbitrary result lists.

    Args:
        results: List of dicts containing at least a content field.
        query: Original query string.
        result_type: Output key name (e.g. "sources", "documents").
        content_key: Field name for content in input dicts.
        score_key: Field name for score in input dicts.
        max_content_length: Max characters retained per item.
    """
    try:
        if not results:
            return {
                "query": query,
                "summary": "No results found",
                result_type: [],
                f"{result_type}_count": 0
            }
        
        formatted = []
        for i, result in enumerate(results, 1):
            content = result.get(content_key, "")
            if len(content) > max_content_length:
                content = content[:max_content_length] + "... [truncated]"
            
            formatted.append({
                "rank": i,
                "content": content,
                "score": result.get(score_key, 0.0),
                **{k: v for k, v in result.items() if k not in [content_key, score_key]}  # Include other fields
            })
        
        summary = f"Found {len(formatted)} {result_type}"
        
        return {
            "query": query,
            "summary": summary,
            result_type: formatted,
            f"{result_type}_count": len(formatted)
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to format generic results: {error_msg}", exc_info=True)
        
        return {
            "query": query,
            "summary": f"Formatting failed: {error_msg[:100]}",
            result_type: [],
            f"{result_type}_count": 0,
            "error": error_msg
        }