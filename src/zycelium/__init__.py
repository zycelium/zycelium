"""Zycelium: Personal Communication and Automation Network"""

from .agent import Agent
from .logging import get_logger

__version__ = "2025.0.2"


__all__ = [
    "__version__",
    "Agent",
    "get_logger",
]
