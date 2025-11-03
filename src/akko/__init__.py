"""AKKO (Access Key Keep Ownership) - A secure password and credential manager.

This package provides a simple, secure, and serverless password manager designed
to keep your data under your control.
"""

from akko.logging import configure_logger, get_logger

# Configure package-wide logging immediately on import and expose a shared logger.
configure_logger()
logger = get_logger("akko")

__all__ = ["logger"]
