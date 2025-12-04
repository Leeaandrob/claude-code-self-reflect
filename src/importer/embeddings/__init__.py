"""Cloud embedding providers for text vectorization."""

from .base import EmbeddingProvider
from .validator import EmbeddingValidator

# Conditional imports for cloud providers
__all__ = [
    "EmbeddingProvider",
    "EmbeddingValidator"
]

try:
    from .voyage_provider import VoyageEmbeddingProvider
    __all__.append("VoyageEmbeddingProvider")
except ImportError:
    pass

try:
    from .qwen_provider import QwenEmbeddingProvider
    __all__.append("QwenEmbeddingProvider")
except ImportError:
    pass
