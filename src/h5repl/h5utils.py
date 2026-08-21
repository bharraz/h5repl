"""
h5utils.py
Contains all functions for opening hdf5 files and accessing data.
"""

import re
import h5py
import os
from pathlib import Path
from rich.tree import Tree
from rich.console import Console
from .globals import OPEN_FILES, CFG


def h5open(ID, nickname=None, verbose=True):
    """
    Open an HDF5 file by ID, searching all directories in config.toml.
    Stores it in OPEN_FILES under nickname (defaults to ID).

    Returns the opened h5py.File on success, None on failure.
    """
    ID = str(ID)
    for _, filepath in CFG['file_directories'].items():
        for root, _, files in os.walk(filepath):
            for name in files:
                if ID in name:
                    full_fp = root + "/" + name
                    if verbose:
                        print(f"Opening {full_fp}")
                    key = ID if nickname is None else nickname
                    OPEN_FILES[key] = h5py.File(full_fp, 'r')
                    return OPEN_FILES[key]
    print(f"File with ID {ID} not found.")
    return None


def browse(nickname=None):
    """
    Open a file-browser dialog to select an HDF5 file, then open it.
    The file is stored in OPEN_FILES under nickname, or under the leading
    digits of the filename if present, or the filename stem otherwise.

        f = browse()
        f = browse(nickname='ref')
    """
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    path = filedialog.askopenfilename(
        parent=root,
        title='Open HDF5 file',
        filetypes=[('HDF5 files', '*.h5 *.hdf5'), ('All files', '*.*')],
    )
    root.destroy()

    if not path:
        print('No file selected.')
        return None

    stem = Path(path).stem
    m = re.match(r'^(\d+)', stem)
    key = nickname if nickname else (m.group(1) if m else stem)

    print(f"Opening {path}")
    f = h5py.File(path, 'r')
    OPEN_FILES[key] = f
    return f


def h5close(filename):
    """Close one open HDF5 file and remove it from OPEN_FILES."""
    if isinstance(filename, h5py.File):  # accept file object directly
        file_obj = filename
        key = next((k for k, v in OPEN_FILES.items() if v is file_obj), None)
        try:
            file_obj.close()
        except Exception as e:
            print(f"Error closing file: {e}")
            return False
        if key is not None:
            OPEN_FILES.pop(key, None)
        return True

    filename = str(filename)
    if filename not in OPEN_FILES:
        print(f"No open file named {filename}.")
        return False
    file_obj = OPEN_FILES.pop(filename)
    try:
        file_obj.close()
        return True
    except Exception as e:
        print(f"Error closing {filename}: {e}")
        return False


def h5close_all():
    """Close all open HDF5 files tracked in OPEN_FILES."""
    for key, file_obj in list(OPEN_FILES.items()):
        try:
            file_obj.close()
        except Exception as e:
            print(f"Error closing {key}: {e}")
    OPEN_FILES.clear()


def _get_file(filename):
    """Return an open file by nickname/ID, opening it first if needed."""
    if isinstance(filename, h5py.File):
        return filename
    filename = str(filename)
    if filename not in OPEN_FILES:
        print(f"'{filename}' not open - attempting to open:")
        if not h5open(filename):
            return None
    return OPEN_FILES[filename]


def _get_dataset_helper(h5obj, name):
    """Recursively find all items named `name` under h5obj."""
    if name in h5obj:
        return [h5obj[name]]
    found = []
    for _, item in h5obj.items():
        if isinstance(item, h5py.Group):
            found.extend(_get_dataset_helper(item, name))  # recurse into groups
    return found


def get_dataset(filename, name):
    """
    Find and return a dataset by name from an open file.
    Searches recursively; returns numpy array, float, or group.
    """
    file = _get_file(filename)
    if file is None:
        return None
    matches = _get_dataset_helper(file, name)
    if not matches:
        return None
    if len(matches) > 1:
        print(f"Warning: multiple matches for '{name}', using last.")
        print(f"  Matches: {matches}")
    obj = matches[-1]
    if isinstance(obj, h5py.Dataset):
        arr = obj[()]
        try:
            return float(arr) if hasattr(arr, 'shape') and arr.shape == () else arr
        except Exception:
            return arr
    return obj  # group


def h5print(filename, skip_roots=None, start_root=None):
    """
    Pretty-print the HDF5 file structure using rich.
    skip_roots: list of top-level keys to omit.
    start_root: print only the subtree rooted here.
    """
    file = _get_file(filename)
    skip_roots = skip_roots or []

    def add_to_tree(h5obj, tree):
        for key, item in h5obj.items():
            if key in skip_roots:
                continue
            if isinstance(item, h5py.Dataset):
                shape, dtype = item.shape, item.dtype
                if shape == () or shape == (1,):
                    value = item[()] if shape == () else item[0]
                    label = f"[bold]{key}[/] [dim]({dtype}, value={value})[/]"
                else:
                    label = f"[bold]{key}[/] [dim](shape={shape}, dtype={dtype})[/]"
                tree.add(label)
            elif isinstance(item, h5py.Group):
                add_to_tree(item, tree.add(f"[bold]{key}[/] (Group)"))
            else:
                tree.add(f"[bold]{key}[/] ({type(item).__name__})")

    console = Console(highlight=False, no_color=True)
    if start_root:
        root_obj = get_dataset(filename, start_root)
        if root_obj is None:
            console.print("[red]start root not found[/red]")
            return
        kind = 'Group' if isinstance(root_obj, h5py.Group) else 'Dataset'
        tree = Tree(f"[bold]{getattr(root_obj, 'name', start_root)}[/] ({kind})")
        if isinstance(root_obj, h5py.Group):
            add_to_tree(root_obj, tree)
        else:
            shape, dtype = root_obj.shape, root_obj.dtype
            if shape in ((), (1,)):
                value = root_obj[()] if shape == () else root_obj[0]
                tree.add(f"[dim]({dtype}, value={value})[/]")
            else:
                tree.add(f"[dim](shape={shape}, dtype={dtype})[/]")
    else:
        tree = Tree(f"[bold]{getattr(file, 'filename', filename)}[/] (HDF5 File)")
        add_to_tree(file, tree)
    console.print(tree)
