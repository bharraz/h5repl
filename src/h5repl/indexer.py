"""Optional indexer functionality -- to be configured per system"""
from .globals import *
import sqlite3
import os
import time
from pathlib import Path
from typing import Optional
import re


class Indexer:
    def __init__(self):
        db_path = Path(PKG_ROOT) / ".h5index.db"
        if db_path.exists():
            print("true")
        
        self.con = sqlite3.connect(db_path)

    def index_all(self):
        def get_file_info(root_dir):
            for entry in os.scandir(root_dir):
                if entry.is_dir():  # Recursively walk into subdirectories
                    yield from get_file_info(entry.path)  # Recursive call for subdirectories
                elif entry.is_file():  # Process files
                    # Get creation time (using os.stat().st_ctime, works on most systems)
                    creation_time = time.ctime(entry.stat().st_ctime)  # Convert timestamp to readable format
                    yield entry.path, creation_time
        
        for fp_name, filepath in CFG['file_directories'].items(): 
            print(f"indexing: {filepath}")
            for file_path, creation_time in get_file_info(filepath):
                print(f"File: {file_path} | Created on: {creation_time}")


if __name__ == "__main__":
    indexer = Indexer()
