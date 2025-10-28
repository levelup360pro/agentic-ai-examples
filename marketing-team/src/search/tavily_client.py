"""
Tavily AI-first search API wrapper.
Simple, clean implementation with no unnecessary complexity.
"""

import os
from tavily import TavilyClient as Tavily
from typing import List, Dict, Optional


class TavilySearchClient:
    """Tavily AI-first search API wrapper"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.client = Tavily(api_key=self.api_key)

    def search(self,
               query: str,
               max_results: int = 5,
               search_depth: str = "basic",
               search_type: str = 'general') -> List[Dict]:
        """
        Execute Tavily search
        
        Args:
            query: Search query
            max_results: Number of results (default 5)
            search_depth: 'basic' or 'advanced'
            search_type: 'technical', 'industry', 'news', 'documentation'

        Returns:
            List of dicts with keys: url, content, score
        """

        # Define allowed domains per search type
        domain_filters = {
            'technical': [
                'github.com', 'arxiv.org', 'openai.com', 'anthropic.com',
                'microsoft.com/research', 'google.com/research', 'huggingface.co',
                'deepmind.google', 'ai.meta.com'
            ],
            'industry': [
                'gartner.com', 'forrester.com', 'mckinsey.com',
                'idc.com', 'statista.com', 'deloitte.com', 'pwc.com',
                'accenture.com', 'bcg.com'
            ],
            'news': [
                'techcrunch.com', 'theverge.com', 'wired.com',
                'reuters.com', 'bloomberg.com', 'ft.com', 'wsj.com',
                'arstechnica.com', 'venturebeat.com'
            ],
            'documentation': [
                'azure.microsoft.com', 'docs.python.org', 'docs.aws.amazon.com',
                'langchain.com', 'crewai.com', 'cloud.google.com',
                'kubernetes.io', 'docker.com'
            ],
            'general': None  # Explicitly set to None (no domain filtering)
        }

        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_raw_content=False,  # Get LLM-optimized content
                include_domains=domain_filters.get(search_type, []),  # Allowlist or all domains if no match
                exclude_domains=[
                    'linkedin.com/posts', 'linkedin.com/pulse',
                    'medium.com', 'facebook.com', 'twitter.com', 'x.com',
                    'reddit.com/r/', 'quora.com', 'pinterest.com'
                ]  # Denylist
            )

            return response.get('results', [])

        except Exception as e:
            print(f"Tavily search error: {e}")
            return []

    def format_search_context(self, results: List[Dict]) -> str:
        """
        Format Tavily results as context string for LLM injection
        
        Args:
            results: List of search results from self.search()
        
        Returns:
            Formatted string for prompt injection
        """
        if not results:
            return ""

        context = []
        context.append("\n" + "|" + "-" * 70)
        context.append("  RELEVANT SEARCH CONTENT:")
        context.append("|" + "-" * 70)

        for i, result in enumerate(results, 1):
            context.append(f"{i}. {result['content']}")
            context.append(f"   Source: {result['url']}\n")

        return "\n".join(context)
