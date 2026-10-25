"""Module-level cache for trained model objects.

Reflex State cannot store non-serializable objects (model instances, sklearn pipelines, etc.).
This module provides a simple dict-based cache keyed by tag_name. Used by TrainingState
during the start_training -> save_model handoff.

Internal API (underscore prefix preserved for backward compat with existing imports).
"""
from typing import Any, Dict
from datetime import datetime

from reflex.utils import console

_training_cache: Dict[str, Dict[str, Any]] = {}


def _cache_training_result(tag_name: str, result: Dict[str, Any], model):
    """Store training result and model object in module-level cache."""
    global _training_cache
    _training_cache[tag_name] = {
        'result': result,
        'model': model,
        'timestamp': datetime.now(),
    }
    console.info(f"✅ Cached training result for {tag_name}")


def _get_cached_model(tag_name: str):
    """Retrieve cached model object (None if not present)."""
    global _training_cache
    cached = _training_cache.get(tag_name)
    if cached:
        console.info(f"✅ Retrieved cached model for {tag_name}")
        return cached.get('model')
    console.warn(f"⚠️ No cached model found for {tag_name}")
    return None


def _clear_cache(tag_name: str = None):
    """Clear training cache for a specific tag, or all if tag_name is None."""
    global _training_cache
    if tag_name:
        if tag_name in _training_cache:
            del _training_cache[tag_name]
            console.info(f"Cleared cache for {tag_name}")
    else:
        _training_cache.clear()
        console.info("Cleared all training cache")
