"""ASGI entry point for deployment platforms that expect ``backend.main:app``."""

from .app import app

__all__ = ["app"]
