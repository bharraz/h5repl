"""
h5utils.py
Contains all functions for opening hdf5 files and accessing data.
"""

import h5py
import os
import numpy as np
from rich.tree import Tree
from rich.console import Console
from .globals import *
from . import goldh5file

_GROUP_TYPES = (h5py.Group, goldh5file._VirtualGroup)
_DATASET_TYPES = (h5py.Dataset, goldh5file._VirtualDataset)

def _add_file(file, nickname):
    """Adds the passed file to OPEN_FILES in globals"""
    OPEN_FILES[nickname] = file

def h5open(ID, nickname=None, verbose=True):
    """
    Opens h5 file given ID and adds it to currently open files. 
    Will check all directories found under [file_directories] in the config file
    Adds the opened file to OPEN_FILES with nickname as the key if successfully matched the ID

    Args: 
        ID (int or str) : ID of the desired file, used to match the filename
        nickname (str, optional) : nickname for the file, to be used as a pointer to the file. By defualt it is the ID
        verbose (boolean, optional) : Prints the filepath of the found file
    
    Returns: 
        False on failure, True on success
    """
    ID = str(ID)
    # Loop through all directories in CFG
    for fp_name, filepath in CFG['file_directories'].items(): 
        # Do an OS Walk and find the first match for ID
        # TODO: Make this walk from most recent to least recently edited
        # TODO: Maybe make the walk happen only once and create a datastructure holding all filepaths for efficiency
        #   Alternatively, constantly build a map of all the IDs in directories found in config, save it locally, and use that to access
        for root, dirs, files in os.walk(filepath): 
            for name in files:
                if ID in name:
                    full_fp = root + "/" + name
                    if verbose:
                        print(f"Opening File at {full_fp}")
                    _add_file(goldh5file.GoldH5File(full_fp, 'r'), ID if nickname == None else nickname)
                    return True
    
    print(f"File with ID {ID} not found.")
    return False

def h5close(filename):
    """Close one open HDF5 file and remove it from OPEN_FILES."""
    if isinstance(filename, h5py.File):
        file_obj = filename
        key = None
        for k, v in OPEN_FILES.items():
            if v is file_obj:
                key = k
                break
        try:
            file_obj.close()
        except Exception as e:
            print(f"Error closing file object: {e}")
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
    """Takes a string or a h5File and returns the file or opens the file and returns it if possible"""
    if isinstance(filename, h5py.File):
        return filename

    filename = str(filename)
    if filename not in OPEN_FILES.keys():
        print(f"Could not find an open file with name {filename}, attempting to open it:")
        if h5open(filename) is False:
            print(f"Could not find file with name {filename}")
            return None

    return OPEN_FILES[filename]

def _get_dataset_helper(h5obj, name):
    """
    Recursively search for a dataset or group with the given name in the HDF5 object.
    Returns a list of matches for datasets that contain the name "name"
    """
    found = []
    if name in h5obj: 
        return [h5obj[name]]
    for key, item in h5obj.items():
        if isinstance(item, _GROUP_TYPES):
            found = found + _get_dataset_helper(item, name)
    return found

def get_dataset(filename, name):
    """
    Args:
        filename: int or str, nickname of the open file or ID to open file by
        name: Name of the dataset to be returned
    
    Returns:
        dataset value, as either a numpy array or a float when possible.
        If the dataset is a group in the h5file, return the group
        If there are multiple matches, it uses the last found match and prints a warning
        If there are no matches, returns None
    """
    file = _get_file(filename)
    if file is None:
        return None

    obj = _get_dataset_helper(file, name)
    if obj == []:
        return None

    if len(obj) != 1:
        print(f"Warning, multiple matches for dataset with name {name}")
        print(f"Found Matches: {obj}")
        obj = obj[-1]
    else:
        obj = obj[0]

    if isinstance(obj, _DATASET_TYPES):
        # Return value as numpy array or float if possible
        arr = obj[()]
        try:
            if hasattr(arr, 'shape') and arr.shape == ():
                return float(arr)
            return arr
        except Exception:
            return arr
    else:
        # Return the group
        return obj

def h5print(filename, skip_roots=None, start_root=None):
    """
    Print a pretty structure of the HDF5 file using the rich package.
    Shows dataset shape, dtype, and value if scalar. Can skip or start from specific roots.

    Args:
        filename: int or str, nickname of the open file or ID to open file by
        skip_roots: list of str, roots to skip (default: empty list)
        start_root: str or None, root to start printing from (default: None)
    """
    file = _get_file(filename)
    skip_roots = skip_roots or []

    def add_to_tree(h5obj, tree):
        # Recursively add groups and datasets to the rich tree
        for key, item in h5obj.items():
            if key in skip_roots:
                continue  # Skip any roots specified by the user
            if isinstance(item, _DATASET_TYPES):
                shape = item.shape
                dtype = item.dtype
                if shape == () or shape == (1,):
                    # Scalar dataset: print the value
                    value = item[()] if shape == () else item[0]
                    label = f"[bold]{key}[/] [dim](Dataset, {dtype}, value={value})[/]"
                else:
                    # Non-scalar dataset: print shape and dtype
                    label = f"[bold]{key}[/] [dim](Dataset, shape={shape}, dtype={dtype})[/]"
                tree.add(label)
            elif isinstance(item, _GROUP_TYPES):
                # Add group and recurse
                label = f"[bold]{key}[/] (Group)"
                branch = tree.add(label)
                add_to_tree(item, branch)
            else:
                # Other HDF5 object types
                label = f"[bold]{key}[/] ({type(item).__name__})"
                tree.add(label)

    console = Console()
    if start_root:
        # If a start_root is specified, find it using get_dataset
        root_obj = get_dataset(filename, start_root)
        if root_obj is None:
            console.print("[red]start root not found[/red]")
            return
        # Set the root label for the tree
        root_label = f"[bold]{getattr(root_obj, 'name', start_root)}[/] ({'Group' if isinstance(root_obj, _GROUP_TYPES) else 'Dataset'})"
        tree = Tree(root_label)
        if isinstance(root_obj, _GROUP_TYPES):
            # If it's a group, print its subtree
            add_to_tree(root_obj, tree)
        elif isinstance(root_obj, _DATASET_TYPES):
            # If it's a dataset, print its info
            shape = root_obj.shape
            dtype = root_obj.dtype
            if shape == () or shape == (1,):
                value = root_obj[()] if shape == () else root_obj[0]
                tree.add(f"[dim](Dataset, {dtype}, value={value})[/]")
            else:
                tree.add(f"[dim](Dataset, shape={shape}, dtype={dtype})[/]")
    else:
        # Print the whole file tree from the file root
        root_label = f"[bold]{getattr(file, 'filename', filename)}[/] (HDF5 File)"
        tree = Tree(root_label)
        add_to_tree(file, tree)
    # Print the tree to the console
    console.print(tree)