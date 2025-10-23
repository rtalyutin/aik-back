"""Custom exceptions raised by service integrations."""

from __future__ import annotations


class ServiceError(RuntimeError):
    """Base class for recoverable service errors."""


class ProviderNotAvailable(ServiceError):
    """Raised when requested provider is disabled via feature flags."""
