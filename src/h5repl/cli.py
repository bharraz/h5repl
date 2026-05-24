"""Command-line interface entry point for h5repl"""
import matplotlib.pyplot as plt
import numpy as np
import code
import inspect
import re
import h5py
import rich
from pathlib import Path
import builtins

from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts.prompt import CompleteStyle
from . import h5utils, globals , PTKCompleter

class H5REPL(code.InteractiveConsole):
    def __init__(self):
        # Add custom variables to be used in REPL environment
        self.variables = {"plt": plt, "np": np, "help" : help}
        # Add all public variables from h5utils
        self.variables.update({k: v for k, v in vars(h5utils).items()})# if not k.startswith("_")})
        # Add all public variables from globals
        self.variables.update({k: v for k, v in vars(globals).items()})# if not k.startswith("_")})

        # Set up the custom completer function for tab completion
        self.session = PromptSession(completer=PTKCompleter.PTKCompleter(self.variables.keys()),
                                        complete_while_typing=True,  
                                        complete_style="READLINE_LIKE"  
        )

        super().__init__(locals=self.variables)

    def preprocess(self, source):
        """Preprocesses source string before it is sent to runsource"""
        # Strip whitespace
        source = source.strip()

        # Replace nicknames/IDs with strings
        for key in globals.OPEN_FILES.keys():
            source = re.sub(key, f"\"{key}\"", source)
        return source

    def runsource(self, source, filename="<input>", symbol="single"):
        """Modified function for running the line of code after preprocessing"""
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
    
    def interact(self, banner=None):
        """Overridden function for interactive session to make it a bit cleaner"""
        if banner:
            print(banner)
        while True:
            try:
                line = self.session.prompt(">>> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            else:
                more = self.push(line)
                while more:
                    try:
                        line = self.session.prompt("... ")
                    except (EOFError, KeyboardInterrupt):
                        print()
                        more = False
                    else:
                        more = self.push(line)


def main():
    help = ""

    # Override built in open function:
    builtins.open = h5utils.h5open

    H5REPL().interact(banner="") 