"""
Series.py
Contains a class which acts as a single series for a single plot.
A series is constructed of 1 or more files and handles how the data from each is processed
"""

class Series():

	def __init__(self, hfile, operation=None, label=""):
		self.operation = operation
		self.label = label
		self.files = [hfile]
    
	def map_files(self, operation):
		"""Maps the passed operation onto all files"""
		return