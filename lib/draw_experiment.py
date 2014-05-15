import itertools, sys
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as pl

from collections import deque

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


def draw_exp(meas_file):
    states = []
    l = []
    thr = []
    lat = []
    cpu = []
    ticks = []
    fig_name = meas_file.replace('.txt', '')
    fig_name = fig_name.replace('measurements-', '')

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
            cpu.append(float(m[4]))
            ticks.append(mins)
            mins = mins + 0.5
    meas.close()

    fig = pl.figure(1)
    ax1 = fig.add_subplot(111)
    #print str(len(ticks))
    #print str(len(l))
    ax1.plot(ticks, l, 'black', ticks, thr, 'g-')
    ax1.set_xlabel('Time (min)')
    #ax1.set_xticks(np.arange(48))
    # Make the y-axis label and tick labels match the line color.
    ax1.set_ylabel('Load (reqs/sec)', color='black')
    #ax1.set_ylim((0, 100000))
    ax1.grid(True)

    ax2 = ax1.twinx()
    ax2.plot(ticks, states, 'r--')
    ax2.set_ylabel('Cluster Size', color='black')
    ax2.set_ylim((0, 26))
    #for tl in ax2.get_yticklabels():
    #	tl.set_color('r')
    #pl.grid(True)
    pl.title('Lambda vs. Time')
    pl.savefig(fig_name)

    pl.clf()
    pl.cla()
    # run running average on lambda measurements
    n = 3
    run_avg_gen = moving_average(l, n)
    thr_avg_gen = moving_average(thr, n)
    l_run_avg = []
    for r in run_avg_gen:
        l_run_avg.append(float(r))
        ticks_ra = ticks[1:(len(ticks)-1)] #np.arange(i-8, i-2, 1)
    thr_run_avg =[]
    for u in thr_avg_gen:
        thr_run_avg.append(float(u))

    fig2 = pl.figure(2)
    ax1 = fig2.add_subplot(111)
    #print str(len(ticks_ra))
    #print str(len(l_run_avg))
    ax1.plot(ticks_ra, l_run_avg, 'black', ticks_ra, thr_run_avg, 'g-')
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

    pl.title('Running average (n=3) Lambda vs. Time')
    pl.savefig(fig_name +'-run-avg-3')

    pl.clf()
    pl.cla()
    # run running average on lambda measurements
    n = 5
    run_avg_gen = moving_average(l, n)
    l_run_avg = []
    for r in run_avg_gen:
        l_run_avg.append(float(r))
        ticks_ra = ticks[2:(len(ticks)-2)] #np.arange(i-8, i-2, 1)

    fig3 = pl.figure(3)
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

    fig4 = pl.figure(4)
    ax1 = fig4.add_subplot(111)
    ax1.plot(ticks, cpu, 'black')#, t, my_inlambda, 'g-')
    ax1.set_xlabel('Time (min)')
    ax1.set_ylabel('CPU Usage (%)', color='black')
    #ax1.set_ylim((0, 50))
    ax1.grid(True)

    ax2 = ax1.twinx()
    ax2.plot(ticks, states, 'r--')
    ax2.set_ylabel('Cluster Size', color='black')
    ax2.set_ylim((0, 26))

    pl.title('CPU Usage vs. Time')
    pl.savefig(fig_name +'-cpu')

    pl.clf()
    pl.cla()

    fig5 = pl.figure(5)
    ax1 = fig5.add_subplot(111)
    ax1.plot(ticks, lat, 'black')#, t, my_inlambda, 'g-')
    ax1.set_xlabel('Time (min)')
    ax1.set_ylabel('Latency (msec)', color='black')
    #ax1.set_ylim((0, 1500))
    ax1.grid(True)

    ax2 = ax1.twinx()
    ax2.plot(ticks, states, 'r--')
    ax2.set_ylabel('Cluster Size', color='black')
    ax2.set_ylim((0, 26))

    pl.title('Latency vs. Time')
    pl.savefig(fig_name +'-latency')

    return

if __name__ == '__main__':
    draw_exp(sys.argv[1])