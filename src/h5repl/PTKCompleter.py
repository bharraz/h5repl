"""Prompt toolkit (PTK) based autocomplete for expanded functionality"""
import re
import h5py
import numpy as np
import matplotlib.pyplot as plt
from prompt_toolkit.completion import Completer, Completion
from . import h5utils, globals, goldh5file

class PTKCompleter(Completer):
    def __init__(self, variables):
        """Variables is a list of relevant symbols to be considered for autocomplete"""
        self.variables = variables
   
    def get_completions(self, document, complete_event):
        """Handles custom tab-autocompletion"""
        # Sometimes check full line
        full_line = document.text_before_cursor
        # Sometimes only autocomplete on the end part of the string after a \s ( [ or , 
        last_symbol = re.split(r"\s|\(|,|\[", full_line)[-1] 

        options = []
        # Autocomplete with dataset names if doing get_dataset
        matches = re.match(r'get_dataset\(\s*([^,]+?)\s*,\s*["\']?(.*?)["\']?\s*$', full_line)
        # matches = re.match(r"get_dataset\(\s*([^,]+?)\s*,\s*(.*?)\s*$", full_line)
        if matches:
            try:
                arg1, arg2 = matches.groups()
                file = globals.OPEN_FILES[arg1]
                def find_matching_datasets(name, obj):
                    if isinstance(obj, (h5py.Dataset, goldh5file._VirtualDataset)) and name.startswith(arg2):
                        options.append(name)
                file.visititems(find_matching_datasets)
            except Exception as e:
                print(f"\nAutocomplete error: {e}")
        elif last_symbol.startswith('np'): 
            # np autocomplete
            options += [name for name in dir(np) if name.startswith(last_symbol)]
        elif last_symbol.startswith('plt'):  
            # matplotlib.pyplot autocomplete
            options += [name for name in dir(plt) if name.startswith(last_symbol)]
        else:
            # Custom autocomplete options
            options += [name for name in self.variables if name.startswith(last_symbol)]
            options += [name for name in globals.OPEN_FILES.keys() if name.startswith(last_symbol)]
         
        # Yield all matches
        for option in sorted(set(options)):
            yield Completion(option, start_position=-len(last_symbol))