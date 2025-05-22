"""
Configuration package for the application.
"""
# Only import what's absolutely necessary to avoid circular imports
from .lifespan import lifespan

# Don't import components here - import it directly where needed
__all__ = ["lifespan"]