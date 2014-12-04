#! /usr/bin/env python
import itertools, sys
from persistance_module import env_vars
#import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as pl
from collections import deque

############ figure size (in inches@80bpi) #################
width = 12
height = 6
dpi = 80

fig_name=""

def moving_average(iterable, n=3):
    # moving_average([40, 30, 50, 46, 39, 44]) --> 40.0 42.0 45.0 43.0
    # http://en.wikipedia.org/wiki/Moving_average
    it = iter(iterable)
    d = deque(itertools.islice(it, n-1))
    d.appendleft(0)
    s = sum(d)
    for elem in it:
        s += elem - d.popleft()
        d.append(elem)
        yield s / float(n)


def my_avg(l, a=0.1):
    prev=l[0]
    rv = [prev]
    for x in l[1:]:
        v = (1.0-a)*prev + a*x
        rv.append(v)
        prev = v
    return rv

def my_draw(x, y, x_label, y_label, graph_name, ax2_x=None, ax2_label=None):
    fig5 = pl.figure(5, figsize=(width,height), dpi=dpi)
    ax1 = fig5.add_subplot(111)
    ax1.plot(x, y, 'black')
    ax1.set_xlabel(x_label)
    ax1.set_ylabel(y_label, color='black')
    ax1.set_ylim((10, 100))
    ax1.grid(True)

    if not ax2_x is None:
        ax2 = ax1.twinx()
        ax2.plot(x, ax2_x, 'g')
        ax2.set_ylabel(ax2_label, color='black')

    pl.title(graph_name)
    pl.savefig(fig_name + "_"+graph_name)
    pl.clf()
    pl.cla()
    return




def draw_exp(meas_file):




    return

if __name__ == '__main__':
    if len(sys.argv) == 2:
        draw_exp(sys.argv[1])
    else:
        print 'Usage: python draw_experiment.py measurements_file'
