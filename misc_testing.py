__author__ = 'cmantas'

a = {'a': 1, 'b': 2};
b = {'a': 3}

c = dict(a.items() + b.items())

from time import time

print time()
from os import remove, mkdir
from shutil import move

import time
#time.ctime() # 'Mon Oct 18 13:35:29 2010'

