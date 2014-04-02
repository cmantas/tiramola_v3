"""\
FuzzPy: Fuzzy sets for Python

@author: Aaron Mavrinac
@organization: University of Windsor
@contact: mavrin1@uwindsor.ca
@license: LGPL-3
"""

__version__ = (0, 4, 2)

__all__ = ['iset', 'fset', 'fnumber', 'graph', 'fgraph', 'visualization']
__name__ = 'fuzz'

from lib.fuzz.iset import *
from lib.fuzz.fset import *
from lib.fuzz.fnumber import *
from lib.fuzz.graph import *
from lib.fuzz.fgraph import *
from lib.fuzz.visualization import *
