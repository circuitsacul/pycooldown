from __future__ import annotations

from typing import Any

from mypyc.build import mypycify  # type: ignore

mypyc_paths = [
    "pycooldown/__init__.py",
    "pycooldown/fixed_mapping.py",
    "pycooldown/flexible_mapping.py",
    "pycooldown/sliding_window.py",
]


def build(setup_kwargs: dict[str, Any]) -> None:
    setup_kwargs["ext_modules"] = mypycify(mypyc_paths)
