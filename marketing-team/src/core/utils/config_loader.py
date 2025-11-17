"""Centralized brand configuration loading and validation.

Single source of truth for config structure requirements.
Fail-fast validation prevents runtime errors in nodes/classes.
"""
from typing import Dict, Any
import yaml
import logging
from src.core.utils.paths import CONFIG_DIR

logger = logging.getLogger(__name__)


class BrandConfigError(Exception):
    """Raised when brand configuration is missing or invalid."""
    pass


def load_brand_config(brand: str) -> Dict[str, Any]:
    """
    Load and validate brand configuration YAML.
    
    Args:
        brand: Brand identifier (e.g., "itconsulting", "cosmetics")
    
    Returns:
        Validated brand configuration dict
    
    Raises:
        BrandConfigError: If config file missing or validation fails
    
    Example:
        >>> config = load_brand_config("itconsulting")
        >>> model = config['models']['generation']['model']
    """   
   
    # Load YAML
    config_path = CONFIG_DIR / f"{brand}.yaml"
    
    if not config_path.exists():
        raise BrandConfigError(
            f"Brand config not found: {config_path}\n"
            f"Available brands: {list_available_brands()}"
        )
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise BrandConfigError(f"Invalid YAML in {config_path}: {e}")
    
    # Validate structure
    _validate_brand_config(config, brand)
    
    logger.info(f"Loaded and validated config for brand: {brand}")
    
    return config


def _validate_brand_config(config: Dict[str, Any], brand: str) -> None:
    """
    Validate brand configuration structure.
    
    Raises:
        BrandConfigError: If required fields missing or invalid
    """
    
    # Required top-level sections
    required_sections = ['name', 'positioning', 'models', 'voice', 'formatting_rules', 'retrieval']
    
    for section in required_sections:
        if section not in config:
            raise BrandConfigError(
                f"Missing required section '{section}' in {brand}.yaml\n"
                f"Required sections: {required_sections}"
            )
    
    # Validate models section
    _validate_models_config(config.get('models', {}), brand)
    
    # Validate retrieval section
    _validate_retrieval_config(config.get('retrieval', {}), brand)
    
    # Validate voice section
    _validate_voice_config(config.get('voice', {}), brand)
    
    # Validate formatting_rules
    _validate_formatting_config(config.get('formatting_rules', {}), brand)


def _validate_models_config(models: Dict[str, Any], brand: str) -> None:
    """Validate models configuration section."""
    
    required_models = [
        'content_planning',
        'content_generation',
        'content_evaluation',
        'content_optimization',
        'search_optimization',
        'vectorization'
    ]
    
    required_fields = {
        'content_planning': ['model', 'temperature', 'max_tokens', 'system_message'],
        'content_generation': ['model', 'temperature', 'max_tokens', 'system_message'],
        'content_evaluation': ['model', 'temperature', 'max_tokens', 'pattern', 'system_message'],
        'content_optimization': ['model', 'temperature', 'max_tokens', 'system_message'],
        'search_optimization': ['model', 'temperature', 'max_tokens'],
        'vectorization': ['model', 'chunk_size', 'chunk_overlap', 'chunk_threshold']
    }
    
    for model_type in required_models:
        if model_type not in models:
            raise BrandConfigError(
                f"Missing 'models.{model_type}' in {brand}.yaml\n"
                f"Required models: {required_models}"
            )
        
        model_config = models[model_type]
        
        for field in required_fields[model_type]:
            if field not in model_config:
                raise BrandConfigError(
                    f"Missing required field 'models.{model_type}.{field}' in {brand}.yaml\n"
                    f"Required fields for {model_type}: {required_fields[model_type]}"
                )
    
    # Validate evaluation pattern value
    eval_pattern = models['content_evaluation'].get('pattern')
    valid_patterns = ['reflection', 'evaluator_optimizer']
    if eval_pattern not in valid_patterns:
        raise BrandConfigError(
            f"Invalid evaluation pattern '{eval_pattern}' in {brand}.yaml\n"
            f"Valid patterns: {valid_patterns}"
        )


def _validate_retrieval_config(retrieval: Dict[str, Any], brand: str) -> None:
    """Validate retrieval configuration section."""
    
    required_subsections = ['rag', 'search']
    
    for subsection in required_subsections:
        if subsection not in retrieval:
            raise BrandConfigError(
                f"Missing 'retrieval.{subsection}' in {brand}.yaml\n"
                f"Required subsections: {required_subsections}"
            )
    
    # Validate RAG config
    rag_fields = ['max_results', 'max_distance']
    for field in rag_fields:
        if field not in retrieval['rag']:
            raise BrandConfigError(
                f"Missing 'retrieval.rag.{field}' in {brand}.yaml\n"
                f"Required fields: {rag_fields}"
            )
    
    # Validate search config
    search_fields = ['max_results', 'search_depth', 'search_type']
    for field in search_fields:
        if field not in retrieval['search']:
            raise BrandConfigError(
                f"Missing 'retrieval.search.{field}' in {brand}.yaml\n"
                f"Required fields: {search_fields}"
            )


def _validate_voice_config(voice: Dict[str, Any], brand: str) -> None:
    """Validate voice configuration section."""
    
    required_fields = ['tone', 'style_guidelines', 'banned_terms', 'values']
    
    for field in required_fields:
        if field not in voice:
            raise BrandConfigError(
                f"Missing 'voice.{field}' in {brand}.yaml\n"
                f"Required fields: {required_fields}"
            )
    
    # Validate banned_terms is a list
    if not isinstance(voice['banned_terms'], list):
        raise BrandConfigError(
            f"'voice.banned_terms' must be a list in {brand}.yaml"
        )


def _validate_formatting_config(formatting: Dict[str, Any], brand: str) -> None:
    """Validate formatting_rules configuration section."""
    
    required_fields = [
        'post_requirements',
        'long_post_requirements',
        'blog_post_requirements',
        'newsletter_requirements'
    ]
    
    for field in required_fields:
        if field not in formatting:
            raise BrandConfigError(
                f"Missing 'formatting_rules.{field}' in {brand}.yaml\n"
                f"Required fields: {required_fields}"
            )

def list_available_brands() -> list[str]:
    """List available brand configuration files.

    Returns:
        Sorted list of brand names derived from YAML filenames.
    """
    if not CONFIG_DIR.exists():
        return []
    return sorted([f.stem for f in CONFIG_DIR.glob("*.yaml")])
