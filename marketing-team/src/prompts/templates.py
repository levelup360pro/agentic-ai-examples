"""
Prompt templates for LinkedIn and Facebook content generation.
Simple template system with variable substitution.
"""

from typing import List


class PromptTemplate:
    """Prompt template with variable substitution"""

    def __init__(self, template_string: str, required_variables: List[str], optional_variables: List[str] = []):
        self.template = template_string
        self.required_variables = required_variables
        self.optional_variables = optional_variables

    def render(self, **kwargs) -> str:
        """
        Fill template with values
        
        Args:
            **kwargs: Variable values to substitute
            
        Returns:
            Rendered template string
            
        Raises:
            ValueError: If required variables are missing
        """
        missing = set(self.required_variables) - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing variables: {missing}")

        # Fill optional variables with empty string if not provided
        for var in self.optional_variables:
            if var not in kwargs:
                kwargs[var] = ""

        return self.template.format(**kwargs)


# LinkedIn Templates

LINKEDIN_POST_ZERO_SHOT = PromptTemplate(
    template_string="""Generate a LinkedIn post about the following topic for {brand_name}.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
BRAND GUIDELINES:
======================================================================
{brand_guidelines}

======================================================================
CONTEXT:
======================================================================
{rag_context}
{search_context}

======================================================================
REQUIREMENTS:
======================================================================
- Length: 120-180 words
- Structure: Hook (1-2 lines) → Insight/Evidence → Pattern/Takeaway → Closing
- Include specific data or examples where relevant
- Closing: Choose what fits naturally - engagement question, clear offer, or key takeaway
- No emojis (will be added separately if needed)
- Follow brand guidelines for voice, banned terms, and content generation rules
- CRITICAL: Do not use any phrases from the banned_terms list

======================================================================

Generate a post following ALL brand guidelines above.
Pay special attention to: structure examples, style_guidelines, banned_terms.

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines"],
    optional_variables=["rag_context", "search_context"])

LINKEDIN_POST_FEW_SHOT = PromptTemplate(
    template_string=
    """Generate a LinkedIn post about the following topic for {brand_name}.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
BRAND GUIDELINES:
======================================================================
{brand_guidelines}

======================================================================
CONTEXT:
======================================================================
{rag_context}
{search_context}

======================================================================
EXAMPLES OF GOOD POSTS:
======================================================================
{examples}

======================================================================
REQUIREMENTS:
======================================================================
- Length: 120-180 words
- Structure: Hook → Insight/Evidence → Pattern/Takeaway → Closing
- Match the tone and style of the examples
- Include specific data or examples where relevant
- Closing: Engagement question, clear offer, or key takeaway (match to post purpose)
- Follow brand guidelines for voice, banned terms, and content generation rules
- CRITICAL: Do not use any phrases from the banned_terms list

======================================================================

Generate a post following ALL brand guidelines above.
Pay special attention to: structure examples, style_guidelines, banned_terms.

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "examples"],
    optional_variables=["rag_context", "search_context"])

LINKEDIN_ARTICLE = PromptTemplate(
    template_string=
    """Generate a LinkedIn article about the following topic for {brand_name}.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
BRAND GUIDELINES:
======================================================================
{brand_guidelines}

======================================================================
CONTEXT:
======================================================================
{rag_context}
{search_context}

======================================================================
REQUIREMENTS:
======================================================================
- Length: 1500-2000 words
- Structure:
  1. Hook/Problem (2-3 paragraphs)
  2. Context/Background (2-3 paragraphs)
  3. Main Content (5-7 paragraphs with subheadings)
  4. Key Takeaways (bullet list)
  5. Conclusion + Closing
- Include specific examples, data, or case studies
- Use subheadings for readability
- Closing: End with key takeaways summary, engagement question, or clear next step (match to article purpose)
- Follow brand guidelines for voice, banned terms, and content generation rules
- CRITICAL: Do not use any phrases from the banned_terms list

======================================================================

Generate an article following ALL brand guidelines above.
Pay special attention to: structure examples, style_guidelines, banned_terms.

Article:""",
    required_variables=["topic", "brand_name", "brand_guidelines"],
    optional_variables=["rag_context", "search_context"])


# Facebook Templates

FACEBOOK_POST_ZERO_SHOT = PromptTemplate(
    template_string=
    """Generate a Facebook post about the following topic for {brand_name}.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
BRAND GUIDELINES:
======================================================================
{brand_guidelines}

======================================================================
CONTEXT:
======================================================================
{rag_context}
{search_context}

======================================================================
REQUIREMENTS:
======================================================================
- Length: 100-150 words
- Structure: Hook (1 line) → Value/Story → Closing
- Conversational and engaging tone
- Closing: Question, offer, or key point (match to post purpose)
- No emojis (will be added separately if needed)
- Follow brand guidelines for voice and content generation rules
- CRITICAL: Do not use any phrases from the banned_terms list

======================================================================

Generate a post following ALL brand guidelines above.
Pay special attention to: structure examples, style_guidelines, banned_terms.

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines"],
    optional_variables=["rag_context", "search_context"])

FACEBOOK_POST_FEW_SHOT = PromptTemplate(
    template_string="""Generate a Facebook post about the following topic for {brand_name}.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
BRAND GUIDELINES:
======================================================================
{brand_guidelines}

======================================================================
CONTEXT:
======================================================================
{rag_context}
{search_context}

======================================================================
EXAMPLES OF GOOD POSTS:
======================================================================
{examples}

======================================================================
REQUIREMENTS:
======================================================================
- Length: 100-150 words
- Structure: Hook → Value/Story → Closing
- Match the tone and style of the examples
- Conversational and engaging
- Closing: Question, offer, or key point (match to post purpose)
- Follow brand guidelines for voice and content generation rules
- CRITICAL: Do not use any phrases from the banned_terms list

======================================================================

Generate a post following ALL brand guidelines above.
Pay special attention to: structure examples, style_guidelines, banned_terms.

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "examples"],
    optional_variables=["rag_context", "search_context"]
)

