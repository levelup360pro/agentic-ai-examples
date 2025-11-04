"""
Prompt templates for LinkedIn and Facebook content generation.
Simple template system with variable substitution.
"""

from typing import List, Dict

# module-level registry
TEMPLATES: Dict[str, "PromptTemplate"] = {}

def register_module_templates(module_globals: dict) -> None:
    """Set .name on PromptTemplate instances declared in the module and populate TEMPLATES."""
    for var_name, value in list(module_globals.items()):
        if isinstance(value, PromptTemplate):
            # only set if not explicitly provided
            if not getattr(value, "name", None):
                value.name = var_name
            TEMPLATES[value.name] = value


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

LINKEDIN_LONG_POST_ZERO_SHOT = PromptTemplate(
    template_string=
    """Generate a long-form LinkedIn post about the following topic for {brand_name}.
       - Don't make the post a list of bullet points, add brand personality to it and make it flow.
       - Ensure you follow ALL brand guidelines and style below. 

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
{requirements}

======================================================================

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "requirements"],
    optional_variables=["rag_context", "search_context", "examples"]
)

LINKEDIN_LONG_POST_FEW_SHOT = PromptTemplate(
    template_string=
    """Generate a long-form LinkedIn post about the following topic for {brand_name}.
       - Don't make the post a list of bullet points, add brand personality to it and make it flow.
       - Ensure you follow ALL brand guidelines and style below. 

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
REFERENCE POSTS:
======================================================================
{examples}


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
{requirements}

======================================================================
- Don't make the post a list of bullet points, add brand personality to it and make it flow.
- Ensure you follow ALL brand guidelines and style below. 

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "examples", "requirements"],
    optional_variables=["rag_context", "search_context"]
)

LINKEDIN_POST_ZERO_SHOT = PromptTemplate(
    template_string=
    """Generate a LinkedIn post about the following topic for {brand_name}.
        - Don't make the post a list of bullet points, add brand personality to it and make it flow.
        - Ensure you follow ALL brand guidelines and style below. 

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
{requirements}

======================================================================

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "requirements"],
    optional_variables=["rag_context", "search_context", "examples"])

LINKEDIN_POST_FEW_SHOT = PromptTemplate(
    template_string=
    """Generate a LinkedIn post about the following topic for {brand_name}.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
REFERENCE POSTS:
======================================================================
{examples}

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
{requirements}

======================================================================

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "examples", "requirements"],
    optional_variables=["rag_context", "search_context"])


# Post & Newsletter Templates

BLOG_POST = PromptTemplate(
    template_string=
    """Generate a blog post about the following topic for {brand_name}.
       - Follow ALL brand guidelines below.
       - Output in Markdown format with proper heading hierarchy.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
REFERENCE POSTS:
======================================================================
{examples}

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
{requirements}

======================================================================

Article:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "requirements"],
    optional_variables=["rag_context", "search_context", "examples"])

NEWSLETTER = PromptTemplate(
    template_string=
    """Generate a Newsletter issue about the following topic for {brand_name}.

This will be sent to subscribers and published on LinkedIn profile.

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
{requirements}

======================================================================

Generate a newsletter issue following ALL brand guidelines above.

Newsletter:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "requirements"],
    optional_variables=["rag_context", "search_context", "examples"]
)


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
{requirements}

======================================================================

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "requirements"],
    optional_variables=["rag_context", "search_context", "examples"])

FACEBOOK_POST_FEW_SHOT = PromptTemplate(
    template_string="""Generate a Facebook post about the following topic for {brand_name}.

======================================================================
TOPIC:
======================================================================
{topic}

======================================================================
REFERENCE POSTS:
======================================================================
{examples}

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
{requirements}

======================================================================

Post:""",
    required_variables=["topic", "brand_name", "brand_guidelines", "examples", "requirements"],
    optional_variables=["rag_context", "search_context"]
)

register_module_templates(globals())