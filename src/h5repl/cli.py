"""Command-line interface entry point for h5repl"""
import matplotlib.pyplot as plt
import numpy as np
import code
import inspect
import re
import readline
import h5py
import rich
from pathlib import Path
import builtins
from . import h5utils, globals 

class H5REPL(code.InteractiveConsole):
    def __init__(self):
        # Add custom variables to be used in REPL environment
        self.variables = {"plt": plt, "np": np, "help" : help}
        # Add all public variables from h5utils
        self.variables.update({k: v for k, v in vars(h5utils).items()})# if not k.startswith("_")})
        # Add all public variables from globals
        self.variables.update({k: v for k, v in vars(globals).items()})# if not k.startswith("_")})

        # Set up the custom completer function for tab completion
        readline.set_completer(self.custom_completer)
        readline.parse_and_bind("tab: complete")

        super().__init__(locals=self.variables)

    def custom_completer(self, source, state):
        """
        Handles tab-autocompletion 
        Only does tab-autocompletion for file ID's and functions
        """
        options = []
        print(source)
        if source.startswith("get_dataset"):
            print("HER1")
            args = re.split(",", source)
            print(args)
            if len(args) == 2: # If we're looking at the second argument
                arg1 = re.split("\\(", args[0]).strip()
                arg2 = args[1].strip()
                file = globals.OPEN_FILES[arg1]
                file.visit(lambda name : options.append(name) if isinstance(file[name], h5py.Dataset) and name.startswith(arg2) else None)
                print("HERE")

        # Only autocomplete on the end part of the string after a \s ( or , 
        source = re.split("\\s|\\(|,|\\[", source)[-1] 
        if source.startswith('np'): 
            # np autocomplete
            options += [name for name in dir(np) if name.startswith(source)]
        elif source.startswith('plt'):  
            # matplotlib.pyplot autocomplete
            options += [name for name in dir(plt) if name.startswith(source)]
        else:
            # Custom autocomplete options
            options += [name for name in self.variables.keys() if name.startswith(source)]
            options += [name for name in globals.OPEN_FILES.keys() if name.startswith(source)]
                
        
        if state < len(options):
            return options[state]
        else:
            return None

    def preprocess(self, source):
        # Strip whitespace
        source = source.strip()

        # Replace nicknames/IDs with strings
        for key in globals.OPEN_FILES.keys():
            source = re.sub(key, f"\"{key}\"", source)
        return source

    def runsource(self, source, filename="<input>", symbol="single"):
        source = self.preprocess(source)
        print(source)
        # If input is just a name, it will try to match it to a function and print the docstring
        if source.isidentifier():
            try:
                obj = eval(source, self.locals)
                if callable(obj):
                    doc = inspect.getdoc(obj)
                    print(f"\nDocstring for {source}:\n{'-'*40}")
                    print(doc or "(No docstring available)")
                    print("-"*40 + "\n")
                    return False  # Don’t treat it as code
            except Exception:
                pass  # fall back to normal execution

        # Run the user’s code as normal
        result = super().runsource(source, filename, symbol)
        
        # If there is an open figure, refresh it 
        if plt.get_fignums() != []:
            try:
                print(plt.get_fignums())
                plt.draw()       # Update plot elements
                plt.pause(0.01)  # Allow GUI event loop to update
            except Exception as e:
                print(f"[Plot update skipped: {e}]")
        
        return result


def main():
    
    # x = np.linspace(0, 10, 100)
    # y = np.sin(x)

    # plt.plot(x, y)
    # plt.show(block=False)  # Don’t block, keep REPL alive

    # print("Interactive h5repl REPL started.")
    # print("Try commands like: plt.grid(), plt.title('hi'), plt.plot(x, y**2)")
    # print("Type exit() or Ctrl-D to quit.\n")

    help = ""


    # Override built in open function:
    builtins.open = h5utils.h5open

    H5REPL().interact(banner="") 