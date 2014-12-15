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
    fig, ax1 = pl.subplots(figsize=(width,height))
    ax1 = fig.add_subplot(111)
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

def load_data(meas_file):
    states = []
    l = []
    thr = []
    lat = []
    cpu = []
    ticks = []
    meas = open(meas_file, 'r')
    #meas = open('/home/christina/tiramola/real_experiments/training-sets/90G-debugging/measurements-90G-states-10-14-clients-16-threads-200-target-10000.txt', 'r')
    meas.next() # Skip the first line with the headers of the columns
    mins = 0.0
    for line in meas:
        if not line.startswith('###') and not line.startswith('\n'):
            m = line.split('\t\t')
            #print str(m)
            states.append(int(m[0]))
            l.append(float(m[1]))
            thr.append(float(m[2]))
            lat.append(float(m[3]))
            cpu.append(100.0-float(m[4]))
#            datetime.strptime('2012-11-14 14:32:30', '%Y-%m-%d %H:%M:%S')
            #t = time.strptime(m[5].rstrip(), "%Y-%m-%d %H:%M:%S")
            ticks.append(mins)
#            mins = mins + 0.5
            print 'Actual: Time ' + str(mins) + ' load ' + str(float(m[1]))
            mins += float(env_vars['metric_fetch_interval']) / 60

    meas.close()
    return states, l, thr, cpu, lat, ticks


def load_predictions(pred_file):
    pred_l = []
    ticks = []
    preds = open(pred_file, 'r')
    #preds.next()
    #mins = 0.0
    for line in preds:
        if not line.startswith('###') and not line.startswith('\n'):
            m = line.split('\t\t')
            pred_l.append(float(m[2]))
            ticks.append(float(m[1]))
            #ticks.append(mins)
            #mins += float(env_vars['metric_fetch_interval']) / 60
            print 'Prediction: Time ' + str(float(m[1])) + ' load ' + str(float(m[2]))
    preds.close()
    return pred_l, ticks


def draw_exp(meas_file):
    global fig_name
    fig_name = meas_file.replace('.txt', '')
    fig_name = fig_name.replace('measurements-', '')
    states, l, thr, cpu, lat, ticks = load_data(meas_file)
    fig, ax1 = pl.subplots(figsize=(width,height))
    #plot the 2 values
    a, = ax1.plot(ticks, l, 'black')
    b, = ax1.plot(ticks, thr, 'g')

    ax1.set_xlabel('Time (min)')
    #ax1.set_xticks(np.arange(48))
    # Make the y-axis label and tick labels match the line color.
    pl.minorticks_on()
    ax1.set_ylabel('Load (reqs/sec)', color='black')
    ax1.set_ylim(bottom=2000)
    ax1.grid(True, which="major")
    ax1.grid(True, which="minor", color='#C0C0C0')
    #ax1.tick_params(axis='x',which='minor',bottom='on')

    #clone the diagram and plot ontop
    ax2 = ax1.twinx()
    c, = ax2.plot(ticks, states, 'r--', linewidth=2)
    ax2.set_ylabel('# of nodes', color='black', position=(0, 0.6))
    ax2.set_ylim((5, 20))
    ax2.get_yaxis().set_tick_params(which='both', direction='in')

    #set the legend
    pl.legend([a, b,c], ["target", "throughput", "cluster size"], loc=4)
    pl.title('Lambda vs. Time')
    pl.savefig(fig_name, bbox_inches='tight')

    pl.clf()
    pl.cla()


    # run running average on lambda measurements
    n = 5
    run_avg_gen = moving_average(l, n)
    l_run_avg = []
    for r in run_avg_gen:
        l_run_avg.append(float(r))
        ticks_ra = ticks[2:(len(ticks)-2)] #np.arange(i-8, i-2, 1)

    fig3 = pl.figure(3, figsize=(width,height), dpi=dpi)
    ax1 = fig3.add_subplot(111)
    #print str(len(ticks_ra))
    #print str(len(l_run_avg))
    ax1.plot(ticks_ra, l_run_avg, 'black')#, t, my_inlambda, 'g-')
    ax1.set_xlabel('Time (min)')
    #ax1.set_xticks(np.arange(48))
    # Make the y-axis label and tick labels match the line color.
    ax1.set_ylabel('Load (reqs/sec)', color='black')
    #ax1.set_ylim((0, 120000))
    ax1.grid(True)

    ax2 = ax1.twinx()
    ax2.plot(ticks, states, 'r--')
    ax2.set_ylabel('Cluster Size', color='black')
    ax2.set_ylim((0, 26))

    pl.title('Running average (n=5) Lambda vs. Time')
    pl.savefig(fig_name +'-run-avg-5')

    pl.clf()
    pl.cla()

    fig4 = pl.figure(4, figsize=(width,height), dpi=dpi)
    ax1 = fig4.add_subplot(111)
    a, = ax1.plot(ticks, cpu, 'r')#, t, my_inlambda, 'g-')
    ax1.set_xlabel('Time (min)')
    ax1.set_ylabel('usage %')
    #ax1.set_ylim((0, 50))
    ax1.grid(True)

    ax2 = ax1.twinx()
    b, = ax2.plot(ticks, thr, 'g')
    ax2.set_ylabel('reqs/sec')
    pl.legend([a, b], ["CPU", "Throughput"], loc=4, borderaxespad=0)
    pl.title('CPU Usage vs. Time')
    pl.savefig(fig_name + '-cpu')

    pl.clf()
    pl.cla()

    fig5 = pl.figure(5, figsize=(width,height), dpi=dpi)
    ax1 = fig5.add_subplot(111)
    ax1.plot(ticks, lat, 'black')#, t, my_inlambda, 'g-')
    ax1.set_xlabel('Time (min)')
    ax1.set_ylabel('Latency (msec)', color='black')
    ax1.set_ylim((10, 100))
    ax1.grid(True)


    pl.title('Latency vs. Time')
    pl.savefig(fig_name + '-latency')

    pl.clf()
    pl.cla()

    #cmantas
    lat_avg = my_avg(lat, a=0.2)
    thr_avg = my_avg(thr, a=0.2)
    my_draw(ticks, lat_avg, "Time (sec)", "latency EWMA (msec)", 'latency_ewma', thr_avg, "throughput")


    # load prediction graph
    pfile = meas_file.replace('measurements.txt', 'predictions.txt')
    fig6 = pl.figure(6, figsize=(width, height), dpi=dpi)
    ax1 = fig6.add_subplot(111)

    #plot the 2 values
    a, = ax1.plot(ticks, l, 'black')
    preds, ticks = load_predictions(pfile)
    b, = ax1.plot(ticks, preds, 'r')

    ax1.set_xlabel('Time (min)')
    #ax1.set_xticks(np.arange(48))
    # Make the y-axis label and tick labels match the line color.
    pl.minorticks_on()
    ax1.set_ylabel('Load (reqs/sec)', color='black')
    ax1.set_ylim(bottom=-2000)
    ax1.grid(True, which="major")
    ax1.grid(True, which="minor", color='#C0C0C0')
    #ax1.tick_params(axis='x',which='minor',bottom='on')

    #set the legend
    pl.legend([a, b], ["Actual Load", "Predicted Load"], loc=4)
    pl.title('Actual vs. Predicted Load')
    pl.savefig(fig_name + '-predicted', bbox_inches='tight')

    pl.clf()
    pl.cla()

    return

if __name__ == '__main__':
    if len(sys.argv) == 2:
        draw_exp(sys.argv[1])
    else:
        print 'Usage: python draw_experiment.py measurements_file'
