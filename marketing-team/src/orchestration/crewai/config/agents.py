from typing import Optional, Literal
import os
from crewai import LLM, Agent

def _make_agent_llm_from_config(
    brand_config: dict,
    section: Literal[
        "content_planning",
        "content_generation",
        "content_evaluation",
        "content_optimization",
    ],
) -> LLM:
    """
    """
    cfg = brand_config["models"][section]
    provider = cfg.get("provider", "openrouter")
    model_name = cfg["model"]
    temperature = cfg.get("temperature", 0.2)
    max_tokens = cfg.get("max_tokens", None)

    if provider == "openrouter":
        # Needs OPENROUTER_API_KEY and OPENROUTER_BASE_URL in env
        return LLM(
            model=f"openrouter/{model_name}",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL"),
        )
    elif provider == "azure":
        # For Azure, model_name is your deployment name
        return LLM(
            azure_deployment=f"azure/{model_name}",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
    else:
        raise ValueError(f"Unsupported provider for section '{section}': {provider}")


def build_content_planner_agent(
    brand_config: dict,
    llm: Optional[LLM] = None,
) -> Agent:
    gen_cfg = brand_config["models"]["content_planning"]

    if llm is None:
        llm = _make_agent_llm_from_config(brand_config, "content_planning")

    # Prefer instructions/system_template to inject constraints
    instructions = gen_cfg.get("system_message", "")

    return Agent(
        role="Content Planner",
        goal="Decide which research tools to use for content creation based on the topic and brand.",
        backstory="Planner optimizing for quality-per-euro.",
        llm=llm,                     
        instructions=instructions,   
        tools=[],
        allow_delegation=False,
        verbose=True,
        memory=False,
        system_template=None,
        max_iter=20,
        max_retry_limit=2,
    )

def build_content_generator_agent(
    brand_config: dict,
    llm: Optional[LLM] = None,  # optional if you use return_direct tools for compose
) -> Agent:
    gen_cfg = brand_config["models"]["content_generation"]
    if llm is None and gen_cfg.get("provider"):
        llm = _make_agent_llm_from_config(brand_config, "content_generation")

    return Agent(
        role="Content Generator",
        goal="Compose a brand‑aligned draft using provided contexts.",
        backstory="Writes crisply in the brand's voice.",
        llm=llm,  # safe to keep None when using StructuredTool(return_direct=True)
        tools=[],
        allow_delegation=False,
        verbose=True,
        memory=False,
        system_template=gen_cfg.get("system_message", None),
        max_iter=20,
        max_retry_limit=2,
    )


def build_content_evaluator_agent(
    brand_config: dict,
    llm: Optional[LLM] = None,  # optional if you use return_direct tools for evaluate
) -> Agent:
    eval_cfg = brand_config["models"]["content_evaluation"]
    if llm is None and eval_cfg.get("provider"):
        llm = _make_agent_llm_from_config(brand_config, "content_evaluation")

    return Agent(
        role="Content Evaluator",
        goal="Evaluate content against the brand rubric and provide score, violations, and action list.",
        backstory="Tough but fair; focuses on accuracy and structure.",
        llm=llm,
        tools=[],
        allow_delegation=False,
        verbose=True,
        memory=False,
        system_template=eval_cfg.get("system_message", None),
        max_iter=20,
        max_retry_limit=2,
    )


def build_content_optimizer_agent(
    brand_config: dict,
    llm: Optional[LLM] = None,  # optional; often unnecessary if you just swap system_message on regen
) -> Agent:
    opt_cfg = brand_config["models"]["content_optimization"]
    if llm is None and opt_cfg.get("provider"):
        llm = _make_agent_llm_from_config(brand_config, "content_optimization")

    return Agent(
        role="Content Writer (Optimization)",
        goal="Refine draft using the optimization system message and prior critique.",
        backstory="Iteratively improves clarity and brand voice with minimal changes.",
        llm=llm,
        tools=[],
        allow_delegation=False,
        verbose=True,
        memory=False,
        system_template=opt_cfg.get("system_message", None),
        max_iter=20,
        max_retry_limit=2,
    )