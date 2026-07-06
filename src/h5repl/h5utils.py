"""
h5utils.py
Contains all functions for opening hdf5 files and accessing data.
"""

import re
import h5py
import os
import numpy as np
from pathlib import Path
from rich.tree import Tree
from rich.console import Console
from .globals import OPEN_FILES, CFG
from . import goldh5file

_GROUP_TYPES   = (h5py.Group,   goldh5file._VirtualGroup)
_DATASET_TYPES = (h5py.Dataset, goldh5file._VirtualDataset)


def h5open(ID, nickname=None, verbose=True):
    """
    Open an HDF5 file by ID, searching all directories in config.toml.
    Stores it in OPEN_FILES under nickname (defaults to ID).

    Returns the opened GoldH5File on success, None on failure.
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
                    OPEN_FILES[key] = goldh5file.GoldH5File(full_fp, 'r')
                    return OPEN_FILES[key]
    print(f"File with ID {ID} not found.")
    return None


def browse(nickname=None):
    """
    Open a file-browser dialog to select an HDF5 file, then open it.
    The file is stored in OPEN_FILES under its RID (leading digits of the
    filename) or under nickname if provided.

        f = browse()
        f = browse(nickname='ref')
        quickplot(browse())
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
    f = goldh5file.GoldH5File(path, 'r')
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
        if isinstance(item, _GROUP_TYPES):
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
    if isinstance(obj, _DATASET_TYPES):
        arr = obj[()]
        try:
            return float(arr) if hasattr(arr, 'shape') and arr.shape == () else arr
        except Exception:
            return arr
    return obj  # group


def _single_file_or(file_id_or_pmt, pmt):
    """Support (pmt) and (file_id, pmt) calling conventions.
    When called as f(pmt), uses the single open file (errors if 0 or 2+ are open).
    """
    if pmt is None:
        pmt_val = file_id_or_pmt
        if len(OPEN_FILES) == 0:
            raise ValueError("No files open. Call h5open() or browse() first.")
        if len(OPEN_FILES) > 1:
            raise ValueError(
                f"Multiple files open {list(OPEN_FILES)} — pass file_id explicitly."
            )
        return next(iter(OPEN_FILES)), pmt_val
    return str(file_id_or_pmt), pmt


def pops(file_id_or_pmt, pmt=None):
    """
    Return (populations, errors) arrays for a single PMT across all scan points.
    Uses the single open file when called with just a PMT number.

        y, yerr = pops(0)          # PMT 0, single file open
        y, yerr = pops(103550, -1) # PMT -1, explicit file
    """
    file_id, pmt = _single_file_or(file_id_or_pmt, pmt)
    y    = get_dataset(file_id, f'pops_{pmt}')
    yerr = get_dataset(file_id, f'errs_{pmt}')
    if y is None:
        print(f"pops_{pmt} not found in {file_id}.")
        return None, None
    return np.asarray(y), (np.asarray(yerr) if yerr is not None else None)


def raw(file_id_or_pmt, pmt=None):
    """
    Return raw shot-by-shot photon counts for a single PMT as a
    (num_points, num_shots) integer array.
    Uses the single open file when called with just a PMT number.

        counts = raw(-1)            # PMT -1, single file open
        counts = raw(103550, 0)     # PMT 0, explicit file
        bright = raw(-1) > 1        # threshold to bool
    """
    file_id, pmt = _single_file_or(file_id_or_pmt, pmt)
    raw_group = get_dataset(file_id, 'raw')
    if raw_group is None:
        print(f"'raw' dataset not found in {file_id}.")
        return None
    num_points = int(get_dataset(file_id, 'num_points'))
    first      = np.array(raw_group['0'])   # (num_shots, num_pmt)
    offset     = first.shape[1] // 2
    col        = pmt + offset
    return np.stack([np.array(raw_group[str(i)])[:, col] for i in range(num_points)])


def joint_pop(file_id, state, pmts=None):
    """
    Compute the joint population of a multi-qubit state across all scan points.

    Args:
        file_id : RID, nickname, or open GoldH5File object
        state   : bit string, e.g. '01'
                  '0' = dark (at or below threshold), '1' = bright (above threshold)
                  bit order matches active_pmts left to right
        pmts    : ordered list of PMT indices, e.g. [-1, 0].
                  Defaults to the file's active_pmts.

    Returns:
        (pops, errs) -- numpy arrays of length num_points

    Examples:
        pops, errs = joint_pop(103550, '01')           # uses file's active_pmts
        pops, errs = joint_pop(103550, '01', [-1, 0])  # explicit PMT list
    """
    THRESHOLD = 1

    file = file_id if hasattr(file_id, '_virtual_datasets') else _get_file(str(file_id))
    if file is None:
        return None, None

    if pmts is None:
        pmts = getattr(file, 'active_pmts', None)
        if not pmts:
            print("No active_pmts on file and none provided. Pass pmts explicitly.")
            return None, None

    if len(state) != len(pmts):
        print(f"State '{state}' has {len(state)} bits but {len(pmts)} PMTs were given.")
        return None, None

    raw = get_dataset(file, 'raw')
    if raw is None:
        print("'raw' dataset not found.")
        return None, None

    num_points  = int(get_dataset(file, 'num_points'))
    first_point = np.array(raw['0'])    # (num_shots, num_pmt)
    num_pmt     = first_point.shape[1]
    offset      = num_pmt // 2

    raw_indices = [p + offset for p in pmts]
    want_bright = [c == '1' for c in state]

    pops_arr = np.zeros(num_points)
    errs_arr = np.zeros(num_points)

    for i in range(num_points):
        counts = np.array(raw[str(i)])  # (num_shots, num_pmt)
        bright = counts > THRESHOLD

        match = np.ones(counts.shape[0], dtype=bool)
        for raw_idx, want in zip(raw_indices, want_bright):
            match &= (bright[:, raw_idx] == want)

        n = counts.shape[0]
        p = float(np.mean(match))
        pops_arr[i] = p
        errs_arr[i] = np.sqrt(p * (1.0 - p) / n) if n > 0 else 0.0

    return pops_arr, errs_arr


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
            if isinstance(item, _DATASET_TYPES):
                shape, dtype = item.shape, item.dtype
                if shape == () or shape == (1,):
                    value = item[()] if shape == () else item[0]
                    label = f"[bold]{key}[/] [dim]({dtype}, value={value})[/]"
                else:
                    label = f"[bold]{key}[/] [dim](shape={shape}, dtype={dtype})[/]"
                tree.add(label)
            elif isinstance(item, _GROUP_TYPES):
                add_to_tree(item, tree.add(f"[bold]{key}[/] (Group)"))
            else:
                tree.add(f"[bold]{key}[/] ({type(item).__name__})")

    console = Console(highlight=False, no_color=True)
    if start_root:
        root_obj = get_dataset(filename, start_root)
        if root_obj is None:
            console.print("[red]start root not found[/red]")
            return
        kind = 'Group' if isinstance(root_obj, _GROUP_TYPES) else 'Dataset'
        tree = Tree(f"[bold]{getattr(root_obj, 'name', start_root)}[/] ({kind})")
        if isinstance(root_obj, _GROUP_TYPES):
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
