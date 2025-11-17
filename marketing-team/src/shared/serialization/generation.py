from typing import Any, Dict, Optional

def generation_to_payload(result: Dict[str, Any], *, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    content = result.get("content", "")
    metadata = (result.get("metadata", {}) or {})
    if correlation_id:
        metadata["correlation_id"] = correlation_id
    return {"content": content, "metadata": metadata}