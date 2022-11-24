from mypyc.build import mypycify

mypyc_paths = [
    "pycooldown/__init__.py",
    "pycooldown/fixed_mapping.py",
    "pycooldown/flexible_mapping.py",
    "pycooldown/sliding_window.py",
]


def build(setup_kwargs):
    setup_kwargs["ext_modules"] = mypycify(mypyc_paths)
