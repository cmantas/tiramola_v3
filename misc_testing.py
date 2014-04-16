__author__ = 'cmantas'

a = {'a': 1, 'b': 2};
b = {'a': 3}

c = dict(a.items() + b.items())

print c