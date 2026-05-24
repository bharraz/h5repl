# h5repl

A Python REPL wrapper for interactively exploring and plotting data in HDF5 files.

---

## Installation

From your project root, install in editable mode:

```sh
pip install -e .
```

---

## Usage

Start the REPL from any terminal:

```sh
h5repl
```

This launches an interactive Python console with:
- All your HDF5 utility functions (see below)
- `matplotlib` (`plt`) and `numpy` (`np`) pre-imported
- Your config and open file globals available

In order to be able to open files, the config.toml file needs to have its [file_directories] section populated in the format <nickname = directory_string>

---

## Quick Reference

### File Operations
- `h5open(ID, nickname=None, verbose=True)`  
  Open an HDF5 file by a unique ID to find in the title and add to open files.
- `OPEN_FILES`  
  Dictionary of open files (`nickname` → `h5py.File`).
- `h5print(nickname, skip_roots=None, start_root=None)`  
  Pretty-print the structure of an open file.
- `get_dataset(nickname, name)`  
  Get a dataset or group by name from an open file.

### Plotting
- Use `plt` (matplotlib) and `np` (numpy) as usual.
- Plot data from datasets directly, e.g.:
  ```python
  arr = get_dataset('myfile', 'mydataset')
  plt.plot(arr)
  plt.show()
  ```

### Other Utilities
- `CFG`  
  Dictionary of config options loaded from `config.toml`.

---

## Tab Autocomplete

Tab-completion is enabled in the REPL for all available commands, variables, and file/dataset names. Just press `Tab` to explore available options interactively.

---

## Project Structure

- `src/h5repl/cli.py` — Entry point and REPL logic
- `src/h5repl/h5utils.py` — HDF5 file and dataset utilities
- `src/h5repl/globals.py` — Global variables (config, open files)
- `src/h5repl/series.py` — Series/plotting helpers
- `config.toml` — User/project configuration

---

For more, see the docstrings in each function or type `help(function_name)` in the REPL.
