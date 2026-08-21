"""Global state: open files, plot managers, and config."""

import tomllib
from pathlib import Path

OPEN_FILES    = {}
PLOT_MANAGERS = {}
COLOR_CYCLE   = 'Dark2'
CFG           = {}

PKG_ROOT  = Path(__file__).resolve().parent.parent.parent
toml_path = PKG_ROOT / "config.toml"
with open(toml_path, "rb") as f:
    CFG = tomllib.load(f)

# user_dir in config is relative to PKG_ROOT; defaults to ./user
USER_DIR = (PKG_ROOT / CFG.get('user_dir', './user')).resolve()
USER_DIR.mkdir(parents=True, exist_ok=True)
(USER_DIR / 'figures').mkdir(exist_ok=True)
(USER_DIR / 'fits').mkdir(exist_ok=True)
