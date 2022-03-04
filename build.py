from typing import Any

from mypyc.build import mypycify


def build(setup_kwargs: dict[str, Any]) -> None:
    setup_kwargs["ext_modules"] = mypycify([
        "pycooldown/fixed_mapping.py",
        "pycooldown/flexible_mapping.py",
        "pycooldown/sliding_window.py",
    ])
