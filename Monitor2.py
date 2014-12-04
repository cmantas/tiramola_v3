__author__ = 'cmantas'
import numpy as np
from lib.tiramola_logging import get_logger
import socket
import sys
import xml.parsers.expat
LOG_FILENAME = 'files/logs/Coordinator.log'
#import ClientsCluster as Clients
import CassandraCluster as Servers
from time import sleep
from threading import Thread
from lib.persistance_module import env_vars
import os


class GParser:

    def __init__(self):
        self.inhost =0
        self.inmetric = 0
        self.allmetrics = {}
        self.currhostname = ""

    def parse(self, ganglia_file):
        """
        parses an xml ganglia file
        :param ganglia_file:
        :return: a dictionary of all ganlia metrics and their values
        """
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = self.start_element
        p.EndElementHandler = self.end_element
        p.ParseFile(ganglia_file)

        if self.allmetrics == {}: raise Exception('Host/value not found')
        return self.allmetrics

    def start_element(self, name, attrs):

        # edo xtizo to diplo dictionary. vazo nodes kai gia kathe node vazo polla metrics.
        #print attrs
        if name == "HOST":
            #if attrs["NAME"]==self.host:
            self.allmetrics[attrs["NAME"]]={}
            # edo ftiaxno ena adeio tuple me key to onoma tou node kai value ena adeio dictionary object.
            self.inhost=1
            self.currhostname = attrs["NAME"]
            #print "molis mpika sto node me dns " , self.currhostname

        elif self.inhost == 1 and name == "METRIC": # and attrs["NAME"]==self.metric:
            #print "attrname: " , attrs["NAME"] , " attr value: " , attrs["VAL"]
            self.allmetrics[self.currhostname][attrs["NAME"]] = attrs["VAL"]

    def end_element(self, name):
            if name == "HOST" and self.inhost==1:
                self.inhost = 0
                self.currhostname = ""


class MonitorVms:
    def __init__(self, monitoring_address, monitoring_port=8649):

        self.ganglia_host = monitoring_address
        self.ganglia_port = monitoring_port

        ## Install logger

        self.my_logger = get_logger("MonitorVMs", "INFO", logfile=LOG_FILENAME)

        self.allmetrics={}
        self.parser = GParser()
        # initialize parser object. in the refreshMetrics function call the .parse of the
        # parser to update the dictionary object.
        self.pullMetrics()


    def pullMetrics(self):
        """
        runs periodically and refreshes the metrics
        :return:
        """
        #self.my_logger.debug("Refreshing metrics from %s:%s" % (self.ganglia_host, self.ganglia_port))
        for res in socket.getaddrinfo(self.ganglia_host, self.ganglia_port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.soc = socket.socket(af, socktype, proto)
            except socket.error as msg:
                s = None
                continue
            try:
                self.soc.connect(sa)
            except socket.error as msg:
                self.soc.close()
                self.soc = None
                continue
            break
        if self.soc is None:
            print 'could not open socket %s:%s' % (str(self.ganglia_host), str(self.ganglia_port))
            sys.exit(1)
        self.allmetrics = None
        f = self.soc.makefile("r")
        self.allmetrics = self.parser.parse(f)
        f.close()
        f = None
        self.soc.close()
        #self.my_logger.debug("REFRESHMETRICS allmetrics: "+str(self.allmetrics))
        return self.allmetrics



class YCSB_Monitor():

    log = get_logger("MONITOR", "DEBUG")

    def __init__(self, monitoring_endpoint,  measurementsFile = env_vars["measurements_file"]):
        self.monitoring_endpoint = monitoring_endpoint
        self.monVms = MonitorVms(monitoring_endpoint)
        self.thread = None
        self.measurementsPolicy = 'centroid'
        self.measurementsFile = measurementsFile
        # A dictionary that will remember rewards and metrics in states previously visited
        self.memory = {}
        for i in range(env_vars["min_cluster_size"], env_vars["max_cluster_size"] + 1):
            self.memory[str(i)] = {}
            #self.memory[str(i)]['V'] = None # placeholder for rewards and metrics
            self.memory[str(i)]['r'] = None
            self.memory[str(i)]['arrayMeas'] = None

        # Load any previous statics.
        self.measurementsFile = env_vars["measurements_file"]
        self.trainingFile = env_vars["training_file"]
        self.sumMetrics = {}
        # initialize measurements file
        meas = open(self.measurementsFile, 'a+')
        if os.stat(self.measurementsFile).st_size == 0:
            # The file is empty, set the headers for each column.
            meas.write('State\t\tLambda\t\tThroughput\t\tLatency\t\tCPU\t\tTime\n')
        meas.close()

        # load training set
        meas = open(self.trainingFile, 'r+')
        if os.stat(self.trainingFile).st_size != 0:
            # Read the training set measurements saved in the file.
            meas.next()  # Skip the first line with the headers of the columns
            for line in meas:
                # Skip comments (used in training sets)
                if not line.startswith('###'):
                    m = line.split('\t\t')
                    self.add_measurement(m)
        meas.close()


    def add_measurement(self, metrics, write_mem=True, write_file=False):
        """
        adds the measurement to either memory or file or both
        @param metrics: array The metrics to store. An array containing [state, lamdba, throughput, latency, time]
        @param writeFile: boolean If set write the measurement in the txt file
        :return:
        """
        if self.measurementsPolicy.startswith('average'):
            if not self.sumMetrics.has_key(metrics[0]):
                    # Save the metric with the state as key metrics = [state, inlambda, throughput, latency]
                    self.sumMetrics[metrics[0]] = {'inlambda': 0.0, 'throughput': 0.0, 'latency': 0.0, 'divide_by': 0}

            self.sumMetrics[metrics[0]] = {'inlambda': self.sumMetrics[metrics[0]]['inlambda'] + float(metrics[1]),
                                           'throughput': self.sumMetrics[metrics[0]]['throughput'] + float(metrics[2]),
                                           'latency': self.sumMetrics[metrics[0]]['latency'] + float(metrics[3]),
                                           'divide_by': self.sumMetrics[metrics[0]]['divide_by'] + 1}
        if write_mem:
            # metrics-> 0: state, 1: lambda, 2: thoughtput, 3:latency, 4:cpu, 5:time
            if not self.memory.has_key(metrics[0]):
                self.memory[str(metrics[0])] = {}
                #self.memory[str(metrics[0])]['V'] = None # placeholder for rewards and metrics
                self.memory[str(metrics[0])]['r'] = None
                self.memory[str(metrics[0])]['arrayMeas'] = np.array([float(metrics[1]), float(metrics[2]),
                                                                      float(metrics[3]), float(metrics[4])], ndmin=2)
            elif self.memory[metrics[0]]['arrayMeas'] is None:
                self.memory[metrics[0]]['arrayMeas'] = np.array([float(metrics[1]), float(metrics[2]),
                                                                 float(metrics[3]), float(metrics[4])], ndmin=2)
            else:
                self.memory[metrics[0]]['arrayMeas'] = np.append(self.memory[metrics[0]]['arrayMeas'],
                                                                 [[float(metrics[1]), float(metrics[2]),
                                                                   float(metrics[3]), float(metrics[4])]], axis=0)
                # but add 1 zero measurement for each state for no load cases ??? too many 0s affect centroids?
        if write_file:
            if write_mem:
                used = "Yes"
            else:
                used = "No"
            ms = open(self.measurementsFile, 'a')
            # metrics[5] contains the time tick -- when running a simulation, it represents the current minute,
            # on actual experiments, it is the current time. Used for debugging and plotting
            ms.write(str(metrics[0]) + '\t\t' + str(metrics[1]) + '\t\t' + str(metrics[2]) + '\t\t' +
                     str(metrics[3]) + '\t\t' + str(metrics[4]) + '\t\t' + str(metrics[5]) + '\t\t'+ used+'\n')
            ms.close()


    def get_metrics(self):
        inmetrics = self.monVms.pullMetrics()
        out_metrics = {}


        # avoid type errors at start up
        if not inmetrics.has_key('inlambda'):
            out_metrics['inlambda'] = 0

        if not inmetrics.has_key('throughput'):
            out_metrics['throughput'] = 0

        if not inmetrics.has_key('latency'):
            out_metrics['latency'] = 0

        if not inmetrics.has_key('cpu'):
            out_metrics['cpu'] = 0
         ## Aggreggation of YCSB client metrics
        clients = 0
        # We used to collect server cpu too, do we need it?
        #self.log.debug("TAKEDECISION state: %d, pending action: %s. Collecting metrics" % (self.currentState, str(self.pending_action)))
        for host in inmetrics.keys():
            metric = inmetrics[host]
            if isinstance(metric, dict):
                for key in metric.keys():
                    if key.startswith('ycsb_TARGET'):
                        out_metrics['inlambda'] += float(metric[key])
                    elif key.startswith('ycsb_THROUGHPUT'):
                        out_metrics['throughput'] += float(metric[key])
                    elif key.startswith('ycsb_READ') or key.startswith('ycsb_UPDATE') or key.startswith(
                            'ycsb_RMW') or key.startswith('ycsb_INSERT'):
                        out_metrics['latency'] += float(metric[key])
                    elif key.startswith('cpu_user'):
                        out_metrics['cpu'] += float(metric[key])
                        #self.log.debug("Latency : "+ str(host[key]) +" collected from client: "+ str(key)
                        #                     +" latency so far: "+ str(inmetrics['latency']))
                        if metric[key] > 0:
                            clients += 1
        try:
            out_metrics['latency'] = out_metrics['latency'] / clients
            #self.my_logger.debug("Final latency for this measurement: "+ str(allmetrics['latency']) +" by "
            # + str(clients)+ " clients!")
        except:
            out_metrics['latency'] = 0

        return out_metrics




if __name__ == "__main__":
    print "hello"

    monitor = YCSB_Monitor("83.212.118.57", measurementsFile="dummy.log")

    while True:
        print monitor.get_metrics()
        sleep(3)