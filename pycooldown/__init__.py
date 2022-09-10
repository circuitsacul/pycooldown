from __future__ import annotations

from importlib.metadata import version

from .fixed_mapping import FixedCooldown
from .flexible_mapping import FlexibleCooldown
from .sliding_window import SlidingWindow

__version__ = version(__name__)

__all__ = ("__version__", "FixedCooldown", "SlidingWindow", "FlexibleCooldown")
