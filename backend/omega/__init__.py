"""Omega Framework — multi-agent PRD → product pipeline."""

__version__ = "1.0.0"

from .config import OmegaConfig
from .pipeline import OmegaPipeline
from . import health

__all__ = ["OmegaConfig", "OmegaPipeline", "health", "__version__"]
