'''
Created on 2023/5/12

@author: martinlee
'''

import os
import glob

# Get a list of all Python module files in this folder
modules = glob.glob(os.path.dirname(__file__) + "/*.py")
__all__ = [os.path.basename(f)[:-3] for f in modules if os.path.isfile(f) and not f.endswith('__init__.py')]
print(__all__)
# Import all the modules
for module in __all__:
    __import__(module, globals(), locals(), [], 0)