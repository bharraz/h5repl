"""
globals.py
Holds all global variables used in the repl such as config options or open files
"""

# Broken down TODO:
# 2. Make hutils contain:
#   diff -- difference between two files, root dataset involved
#   browse -- opens file explorer
#   print_file -- pretty prints the file 
#   get_dataset - finds dataset using regexp 
#   plot --- makes a plot with a best guess, optionally takes
# 3. Make Series work with one file
#   set operation and make default operation just get_dataset
#   set dataset 
# 4. Add plotting utils
#   print current series -prints all series with their associated files
# 5. Expand operations to include fitting

# Add global variables -- list of series, maybe at plt to it
#   See if you can do an update_plot call from anywhere

# TODO:
# Make gold system specific version:
# Make open "flatten" expid
# Make it pull the latest from brassboard_artiq fitting functions
# Make it have its config file tracked

import tomllib
from pathlib import Path

# Dict of open files of format {'nickname' : h5py.File}
# 'nickname' is by default just the RID of the experiment
OPEN_FILES = dict() 

# Dictionary of config options found in the config.toml file
CFG = dict()

# Import config options
PKG_ROOT = Path(__file__).resolve().parent.parent.parent
toml_path = PKG_ROOT / "config.toml"
with open(toml_path, "rb") as f:
	CFG = tomllib.load(f)