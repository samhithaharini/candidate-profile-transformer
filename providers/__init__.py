from __future__ import annotations

from providers.linkedin_provider import LinkedInProvider
from providers.github_provider import GitHubProvider

class ValidationError(ValueError):
    """Raised when URL validation fails."""
    pass

__all__ = ["LinkedInProvider", "GitHubProvider", "ValidationError"]
