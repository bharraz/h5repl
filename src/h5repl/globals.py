"""
globals.py
Holds all global variables used in the repl such as config options or open files
"""

import sys
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from pathlib import Path

# Dict of open files of format {'nickname' : h5py.File}
# 'nickname' is by default just the RID of the experiment
OPEN_FILES = dict()

# Dict of active PlotManagers of format {'pm1': PlotManager, ...}
PLOT_MANAGERS = dict()

# Default color cycle. Set to any matplotlib colormap name e.g. 'Dark2', 'tab10', 'Set1'.
COLOR_CYCLE = 'Dark2'

# Dictionary of config options found in the config.toml file
CFG = dict()

# Import config options
PKG_ROOT = Path(__file__).resolve().parent.parent.parent
toml_path = PKG_ROOT / "config.toml"
with open(toml_path, "rb") as f:
	CFG = tomllib.load(f)

USER_DIR = PKG_ROOT / "user"
USER_DIR.mkdir(exist_ok=True)
(USER_DIR / "figures").mkdir(exist_ok=True)
(USER_DIR / "fits").mkdir(exist_ok=True)