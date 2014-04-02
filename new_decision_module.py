__author__ = 'tiramola group'

import CassandraCluster
import os, logging, datetime, operator, thread, math, random, itertools, time
import logging.handlers as handlers
import numpy as np
from lib.fuzz import fgraph, fset
from scipy.cluster.vq import kmeans2
from lib.persistance_module import env_vars
from scipy.stats import linregress
from collections import deque


class RLDecisionMaker:
    def __init__(self, cluster):
        self.cluster = cluster
        self.debug = True
        if self.debug:
            self.currentState = cluster
        else:
            self.currentState = len(CassandraCluster.get_hosts())
        self.nextState = self.currentState
        self.waitForIt = 10

        # The policy for getting throughput and latency when computing the reward func.
        # average, centroid
        self.measurementsPolicy = 'centroid'
        self.prediction = False
        ## find a better way to do this
        self.acted = ["done"]

        # used only in simulation!!
        self.countdown = 0

        # A dictionary that will remember rewards and metrics in states previously visited
        self.memory = {}

        for i in range(env_vars["initial_cluster_size"], env_vars["max_cluster_size"]+1):
            self.memory[str(i)] = {}
            #self.memory[str(i)]['V'] = None # placeholder for rewards and metrics
            self.memory[str(i)]['r'] = None
            self.memory[str(i)]['arrayMeas'] = None

        ## Install logger
        LOG_FILENAME = 'files/logs/Coordinator.log'
        self.my_logger = logging.getLogger('RLDecisionMaker')
        self.my_logger.setLevel(logging.DEBUG)

        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        self.my_logger.addHandler(handler)

        # Load any previous statics.
        self.measurementsFile = 'files/logs/measurements.txt'
        self.sumMetrics = {}
        meas = open(self.measurementsFile, 'a')
        if os.stat(self.measurementsFile).st_size == 0:
            # The file is empty, set the headers for each column.
            meas.write('State\t\tLambda\t\tThroughput\t\tLatency\t\tCPU\t\tTime\n')
        else :
            # Read the measurements saved in the file.
            meas.close()
            meas = open(self.measurementsFile, 'r')

            meas.next() # Skip the first line with the headers of the columns
            for line in meas:
                # Skip comments (used in training sets)
                if not line.startswith('###'):
                    m = line.split('\t\t')
                    self.add_measurement(m)

        meas.close()

    # param metrics: array The metrics to store. An array containing [state, lamdba, throughput, latency, time]
    # param writeFile: boolean If set write the measurement in the txt file
    def add_measurement(self, metrics, writeFile=False):

        if self.measurementsPolicy.startswith('average'):
            if not self.sumMetrics.has_key(metrics[0]):
                # Save the metric with the state as key metrics = [state, inlambda, throughput, latency]
                self.sumMetrics[metrics[0]] = {'inlambda': 0.0, 'throughput': 0.0, 'latency': 0.0, 'divide_by': 0}

            self.sumMetrics[metrics[0]] = {'inlambda': self.sumMetrics[metrics[0]]['inlambda'] + float(metrics[1]),
                                           'throughput': self.sumMetrics[metrics[0]]['throughput'] + float(metrics[2]),
                                     'latency': self.sumMetrics[metrics[0]]['latency'] + float(metrics[3]),
                                     'divide_by': self.sumMetrics[metrics[0]]['divide_by'] + 1}

        # metrics-> 0: state, 1: lambda, 2: thoughtput, 3:latency, 4:cpu, 5:time
        if not self.memory.has_key(metrics[0]):
            self.memory[str(metrics[0])] = {}
            #self.memory[str(metrics[0])]['V'] = None # placeholder for rewards and metrics
            self.memory[str(metrics[0])]['r'] = None
            self.memory[str(metrics[0])]['arrayMeas'] = np.array([float(metrics[1]), float(metrics[2]),
                                                                      float(metrics[3]), float(metrics[4])], ndmin=2)
        elif self.memory[metrics[0]]['arrayMeas'] == None:
            self.memory[metrics[0]]['arrayMeas'] = np.array([float(metrics[1]), float(metrics[2]),
                                                                     float(metrics[3]), float(metrics[4])], ndmin=2)
        else:
            self.memory[metrics[0]]['arrayMeas'] = np.append(self.memory[metrics[0]]['arrayMeas'],
                                                             [[float(metrics[1]), float(metrics[2]),
                                                               float(metrics[3]), float(metrics[4])]], axis=0)
        # but add 1 zero measurement for each state for no load cases ??? too many 0s affect centroids?

#        else:
#            self.my_logger.debug("ADDMEASUREMENT zero measurement, won't be considered "+ str(metrics[3]))

        if writeFile:
            ms = open(self.measurementsFile, 'a')
            # metrics[5] contains the time tick -- when running a simulation, it represents the current minute,
            # on actual experiments, it is the current time. Used for debugging and plotting
            ms.write(str(metrics[0])+'\t\t'+str(metrics[1])+'\t\t'+str(metrics[2])+'\t\t'+
                     str(metrics[3])+'\t\t'+str(metrics[4])+'\t\t'+str(metrics[5])+'\n')
            ms.close()


    # param state: string Get the average metrics (throughput, latency) for this state.
    # return a dictionary with the averages
    def get_averages(self, state):
        averages = {}
        if self.sumMetrics.has_key(state):
            averages['throughput'] = float(self.sumMetrics[state]['throughput']/self.sumMetrics[state]['divide_by'])
            averages['latency'] = float(self.sumMetrics[state]['latency']/self.sumMetrics[state]['divide_by'])

            self.my_logger.debug("GETAVERAGES Average metrics for state: "+ state +" num of measurements: "+ str(self.sumMetrics[state]['divide_by']) +
                                 " av. throughput: "+ str(averages['throughput']) +" av. latency: " +
                                 str(averages['latency']))
        return averages

    def doKmeans(self, state, from_inlambda, to_inlambda):
        # Run kmeans for the measurements of this state and return the centroid point (throughput, latency)
        ctd = {}
        label = []
        centroids = {}
        if self.memory[state]['arrayMeas'] != None :
            self.my_logger.debug("DOKMEANS length of self.memory[state]['arrayMeas']: " + str(len(self.memory[state]['arrayMeas'])))
            sliced_data = None
            for j in self.memory[state]['arrayMeas']:
                #self.my_logger.debug("DOKMEANS self.memory[state]['arrayMeas'][j]: "+ str(j))
                # If this measurement belongs in the slice we're insterested in
                if j[0] >= from_inlambda and j[0] <= to_inlambda:
                    #self.my_logger.debug("DOKMEANS adding measurement : "+ str(j))
                    # add it
                    if sliced_data == None:
                        sliced_data = np.array(j, ndmin=2)
                    else:
                        sliced_data = np.append(sliced_data, [j], axis=0)

            k = 1 # number of clusters
            # 1. No known lamdba values close to current lambda measurement
            if sliced_data == None:
                # Check if there are any known values from +-50% inlambda.
#                original_inlambda = float(from_inlambda* (10/9))
#                from_inlambda = 0.8 * original_inlambda
#                to_inlambda = 1.2 * original_inlambda
#                self.my_logger.debug("Changed lambda range to +- 20%: "+ str(from_inlambda) + " - "+ str(to_inlambda))
#                for j in self.memory[state]['arrayMeas']:
#                    #self.my_logger.debug("DOKMEANS self.memory[state]['arrayMeas'][j]: "+ str(j))
#                    # If this measurement belongs in the slice we're insterested in
#                    if j[0] >= from_inlambda and j[0] <= to_inlambda:
#                        # add it
#                        if sliced_data == None:
#                            sliced_data = np.array(j, ndmin=2)
#                        else:
#                            sliced_data = np.append(sliced_data, [j], axis=0)
#                #centroids, label = kmeans2(self.memory[state]['arrayMeas'], k, minit='points') # (obs, k)
#            #else:
#            if sliced_data == None:
                self.my_logger.debug("No known lamdba values close to current lambda measurement. Returning zeros!")
            else:
                self.my_logger.debug("DOKMEANS length of sliced_data to be fed to kmeans: "+ str(len(sliced_data)))
                centroids, label = kmeans2(sliced_data, k, minit='points')

            # initialize dictionary
            num_of_meas = {}
            #num_of_meas = {'0': 0, '1': 0, '2': 0, '3': 0, '4': 0}
            for j in range(0, k):
                num_of_meas[str(j)] = 0
            if len(label) > 0:
                for i in label:
                    num_of_meas[str(i)] += 1

                max_meas_cluster = max(num_of_meas.iteritems(), key=operator.itemgetter(1))[0]
#            self.my_logger.debug("DOKMEANS state: "+ state +" kmeans2 centroids: "+ str(centroids) +" label: "+
#                       str(num_of_meas) + " cluster with max measurements: "+ str(max_meas_cluster))
                ctd['inlambda'] = centroids[int(max_meas_cluster)][0]
                ctd['throughput'] = centroids[int(max_meas_cluster)][1]
                ctd['latency'] = centroids[int(max_meas_cluster)][2]
                #ctd['cpu'] = centroids[int(max_meas_cluster)][3]
            else:
                self.my_logger.debug("DOKMEANS one of the clusters was empty and so label is None :|. Returning zeros")
                ctd['inlambda'] = 0.0
                ctd['throughput'] = 0.0
                ctd['latency'] = 0.0
                #ctd['cpu'] = 0.0
                #return None
        else:
            self.my_logger.debug("DOKMEANS self.memory[state]['arrayMeas'] is None :|")

        return ctd

    def moving_average(self, iterable, n=3):
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

    def predict_load(self):
        # Linear Regression gia na doume to slope
        stdin, stdout = os.popen2("tail -n 20 "+self.measurementsFile)
        stdin.close()
        lines = stdout.readlines(); stdout.close()
        ten_min_l = [] # store past 10 mins lambda's
        ten_min = [] # store past 10 mins ticks
        for line in lines:
            m = line.split('\t\t') # state, lambda, throughput, latency, cpu, time tick
            ten_min_l.append(float(m[1]))
            ten_min.append(float(m[5]))
            # run running average on the 10 mins lambda measurements
            n = 5
            run_avg_gen = self.moving_average(ten_min_l, n)
            run_avg = []
            for r in run_avg_gen:
                run_avg.append(float(r))
            ten_min_ra = ten_min[2:18]  # np.arange(i-8, i-2, 1)

        # linear regression on the running average
        #(slope, intercept, r_value, p_value, stderr) = linregress(ten_min, ten_min_l)
        (slope, intercept, r_value, p_value, stderr) = linregress(ten_min_ra, run_avg)
        # fit the running average in a polynomial
        coeff = np.polyfit(ten_min, ten_min_l, deg=2)
        self.my_logger.debug("Slope (a): "+ str(slope) + " Intercept(b): " + str(intercept))
        self.my_logger.debug("Polynom coefficients: "+ str(coeff))
        #self.my_logger.debug("next 10 min prediction "+str(float(slope * (p + 10) + intercept + stderr)))
        predicted_l = float(slope * (ten_min[19] + 10) + intercept + stderr) # lambda in 10 mins from now
        #predicted_l = np.polyval(coeff, (ten_min[9] + 10)) # lambda in 10 mins from now

        if slope > 0 :
        #if predicted_l > allmetrics['inlambda'] :
            dif = 6000 + 10 * int(slope)
            #dif = 6000 + 0.2 * int(predicted_l - allmetrics['inlambda'])
            self.my_logger.debug("Positive slope: "+ str(slope) + " dif: " + str(dif)
                                 + ", the load is increasing. Moving the lambda slice considered 3K up")
        else :
            dif = -6000 + 10 * int(slope)
            #dif = -6000 + 0.2 * int(predicted_l - allmetrics['inlambda'])
            self.my_logger.debug("Negative slope "+ str(slope) + " dif: " + str(dif)
                                 + ", the load is decreasing. Moving the lambda slice considered 3K down")
            #dif = ((predicted_l - allmetrics['inlambda'])/ allmetrics['inlambda']) * 0.1 * 6000#* allmetrics['inlambda']
            #dif = int((predicted_l / allmetrics['inlambda']) * 6000)

        return predicted_l

    def take_decision(self, rcvallmetrics):
            '''
             this method reads allmetrics object created by Monitoring.py and decides whether a change of the number of participating
             virtual nodes is due.
            '''
            ## Take decision based on metrics
            action = "none"

    #        self.my_logger.debug("TAKEDECISION rcvallmetrics: " + str(rcvallmetrics))
            # read metrics
            allmetrics = None
            allmetrics = rcvallmetrics.copy()
            self.my_logger.debug("TAKEDECISION state: " + str(self.currentState))

            # avoid type errors at start up
            if not allmetrics.has_key('inlambda'):
                allmetrics['inlambda'] = 0

            if not allmetrics.has_key('throughput'):
                allmetrics['throughput'] = 0

            if not allmetrics.has_key('latency'):
                allmetrics['latency'] = 0

            if not allmetrics.has_key('cpu'):
                allmetrics['cpu'] = 0

            if not self.debug :
                ## Aggreggation of YCSB client metrics
                clients = 0
                # We used to collect server cpu too, do we need it?
                for host in allmetrics.values():
                    if isinstance(host, dict):
                        for key in host.keys():
                            if key.startswith('ycsb_LAMDA'):
                                allmetrics['inlambda'] += float(host[key])
                            if key.startswith('ycsb_THROUGHPUT'):
                                allmetrics['throughput'] += float(host[key])
                            if key.startswith('ycsb_READ') or key.startswith('ycsb_UPDATE') or key.startswith('ycsb_RMW') or key.startswith('ycsb_INSERT'):
                                allmetrics['latency'] += float(host[key])
                                #self.my_logger.debug("Latency : "+ str(host[key]) +" collected from client: "+ str(key)
                                #                     +" latency so far: "+ str(allmetrics['latency']))
                                if host[key] > 0:
                                    clients += 1
                            self.my_logger.debug("Collecting metrics of host: " + str(host))
                try:
                    allmetrics['latency'] = allmetrics['latency'] / clients
                    #self.my_logger.debug("Final latency for this measurement: "+ str(allmetrics['latency']) +" by "
                    # + str(clients)+ " clients!")
                except:
                    allmetrics['latency'] = 0

                #self.my_logger.debug( "TAKEDECISION allmetrics: " + str(allmetrics))

                # Publish measurements to ganglia ?? HELP ??
                try:
                    os.system("gmetric -n ycsb_inlambda -v "+ str(allmetrics['inlambda'])+" -d 15 -t float -u 'reqs/sec' -S "+ str(self.cluster["cassandra_seednode"]) +":cassandra_seednode")
                    os.system("gmetric -n ycsb_throughput -v "+ str(allmetrics['throughput'])+" -d 15 -t float -u 'reqs/sec' -S "+ str(self.cluster["cassandra_seednode"]) +":cassandra_seednode")
                    os.system("gmetric -n ycsb_latency -v "+ str(allmetrics['latency']) + " -d 15 -t float -u ms -S " +  str(self.cluster["cassandra_seednode"]) +":cassandra_seednode")
                except:
                    pass


            # ?? HELP ??
            # acted: we need a shared structure for checking if an action (= adding/removing VMs) is taking place at the moment
            if not self.acted[len(self.acted)-1].startswith("done"):
                # Take decision as soon as decisions are unblocked.
                #self.waitForIt = 0
                self.my_logger.debug("Last action "+ str(self.acted[len(self.acted)-1]) +
                                     " hasn't finished yet, see you later!")
                print str(self.debug) + " Ouf " + str(self.countdown)
                if self.debug & self.countdown != 0:
                    if self.countdown == 1:
                        self.acted.pop()
                        self.my_logger.debug("Running a simulation, set state from: " + str(self.currentState) + " to "
                                             + str(self.nextState))
                        self.currentState = self.nextState

                    self.countdown = self.countdown - 1
                    print "Reducing countdown to "+ str(self.countdown)
                else:
                    print "Tha se trellanw..." +str (self.countdown - 1)
                    self.countdown = self.countdown - 1
                    print "Tha se trellanw..." +str (self.countdown)

                if self.acted[len(self.acted)-1].startswith("remove"):
                    #1. Save the current metrics in memory.
                    self.addMeasurement([str(self.currentState), allmetrics['inlambda'], allmetrics['throughput'],
                                allmetrics['latency'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")], True)
                elif self.acted[len(self.acted)-1].startswith("add"):
                    self.my_logger.debug("Discarding measurement: "+ str([str(self.currentState),
                                        allmetrics['inlambda'], allmetrics['throughput'], allmetrics['latency'],
                                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]))
                    dms = open('files/logs/discarded-measurements.txt', 'a')
                    # metrics[4] contains the time tick -- when running a simulation, it represents the current minute,
                    # on actual experiments, it is the current time. Used for debugging and plotting
                    dms.write(str(self.currentState)+'\t\t'+str(allmetrics['inlambda'])+'\t\t'+
                              str(allmetrics['throughput'])+'\t\t'+ str(allmetrics['latency'])+'\t\t'+
                              str(allmetrics['cpu'])+'\t\t'+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'\n')
                    dms.close()

                return True

            #1. Save the current metrics in memory.
            self.add_measurement([str(self.currentState), allmetrics['inlambda'], allmetrics['throughput'],
                                  allmetrics['latency'], allmetrics['cpu'],
                                  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")], True)

            if self.waitForIt == 0:
                self.waitForIt = 10
            else:
                self.my_logger.debug("New decision in " + str(self.waitForIt) + " mins, see you later!")
                self.waitForIt = self.waitForIt - 1

                return True

            # Select values close to the current throughtput, define tha lambda range we're interested in -+ 5%
            #from_inlambda = 0.95 * allmetrics['inlambda']
            #to_inlambda = 1.05 * allmetrics['inlambda']
            from_inlambda = allmetrics['inlambda'] - 3000
            to_inlambda = allmetrics['inlambda'] + 3000

            if self.prediction:
                predicted_l = self.predict_load()
                dif = abs(allmetrics['inlambda'] - predicted_l)
                self.my_logger.debug("Predicted: "+ str(predicted_l) +" lambda :"+ str(allmetrics['inlambda']) +" New diff: "+ str(dif))
                from_inlambda = predicted_l - 3000
                to_inlambda = predicted_l + 3000

            self.my_logger.debug("TAKEDECISION current lambda: " + str(allmetrics['inlambda']) + " lambda range: " +
                                 str(from_inlambda) + " - " + str(to_inlambda))
            # too low to care, the initial num of nodes can answer 1000 req/sec,
            # so consider it as 0 1000 * len(cluster.size)!!
            if 0.0 < to_inlambda < 1000:
                from_inlambda = 0.0
                self.my_logger.debug("TAKEDECISION current lambda: " + str(allmetrics['inlambda'])
                                     + " changed lambda range to: " + str(from_inlambda) + " - " + str(to_inlambda))


            # The subgraph we are interested in. It contains only the allowed transitions from the current state.
            from_node = max(int(env_vars["initial_cluster_size"]), (self.currentState - env_vars["rem_nodes"]))
            to_node = min(self.currentState + int(env_vars["add_nodes"]), int(env_vars["max_cluster_size"]))
            #self.my_logger.debug("TAKEDECISION creating graph from node: "+ str(from_node) +" to node "+ str(to_node))

            states = fset.FuzzySet()
            # Calculate rewards using the values in memory if any, or defaults
            for i in range(from_node, to_node+1):
                # se periptwsi pou den exeis 3anadei to state upologizei poso tha ithele na einai to throughput
                # allmetrics['max_throughput'] = float(i) * float(self.utils.serv_throughput)
                allmetrics['num_nodes'] = i

                met = {}
                if self.measurementsPolicy.startswith('average'):
                    met = self.getAverages(str(i))
                elif self.measurementsPolicy.startswith('centroid'):
                    met = self.doKmeans(str(i), from_inlambda, to_inlambda)
                    #self.my_logger.debug("TAKEDECISION state: "+ str(i) +" met: "+ str(met))
                    if met != None and len(met) > 0 :
                        # Been in this state before, use the measurements
                        allmetrics['inlambda'] = met['inlambda']
                        allmetrics['throughput'] = met['throughput']
                        allmetrics['latency'] = met['latency']
                        #self.my_logger.debug("TAKEDECISION adding visited state "+ str(i) +" with gain "+ str(self.memory[str(i)]['r']))
                    #else:
                        # No clue for this state use current measurements...
                        #self.my_logger.debug("TAKEDECISION unknown state "+ str(i) +" with gain "+ str(self.memory[str(i)]['r']))


                    self.memory[str(i)]['r'] = eval(env_vars["gain"], allmetrics)
                    if self.currentState != i:
                        self.my_logger.debug("TAKEDECISION adding state "+ str(i) +" with gain "+ str(self.memory[str(i)]['r']))
                        states.add(fset.FuzzyElement(str(i), self.memory[str(i)]['r']))
                # For the current state, use current measurement
                if self.currentState == i:
                    cur_gain = eval(env_vars["gain"], allmetrics)
                    # for debugging purposes I compare the current reward with the one computed using the training set
                    self.my_logger.debug("TAKEDECISION state "+ str(i) +" current reward : "+ str(cur_gain) +" training set reward: "+
                                         str(self.memory[str(i)]['r']))
                    self.memory[str(i)]['r'] = cur_gain
                    self.my_logger.debug("TAKEDECISION adding current state "+ str(i) +" with gain "+ str(cur_gain))
                    states.add(fset.FuzzyElement(str(i), cur_gain))

            # Create the transition graph
            v=[]
            for i in states.keys():
                v.append(i)
            v = set(v)
            stategraph = fgraph.FuzzyGraph(viter = v, directed = True)


            for j in range(from_node, to_node+1):
                if j != self.currentState:
                    # Connect nodes with allowed transitions from the current node.connect(tail, head, mu) head--mu-->tail
                    stategraph.connect(str(j), str(self.currentState), eval(env_vars["trans_cost"], allmetrics))
                    self.my_logger.debug("TAKEDECISION connecting state "+str(self.currentState)+" with state "+ str(j))
                    # Connect nodes with allowed transitions from node j.
                    #for k in range(max(int(env_vars["initial_cluster_size"]), j - int(env_vars["rem_nodes"])),
                    #               min(j + int(env_vars["add_nodes"]), int(env_vars["max_cluster_size"])+1)):
                    #    if k != j:
                    #        self.my_logger.debug("TAKEDECISION connecting state "+ str(j) +" with state "+ str(k))
                    #        stategraph.connect(str(k), str(j), eval(env_vars["trans_cost"], allmetrics))

            #Calculate the V matrix for available transitions
            V = {}

            for s in range(from_node, to_node+1):
                # Get allowed transitions from this state.
                if self.memory[str(s)]['r'] != None:
                    # For each state s, we need to calculate the transitions allowed.
                    #allowed_transitions = stategraph.edges(head=str(s))
                    #Vs = []
#                    for t in allowed_transitions:
                        # t[0] is the tail state of the edge (the next state)
                        # No V from last run
                        #if self.memory[t[0]]['V'] == None:
                        #    self.memory[t[0]]['V'] = self.memory[t[0]]['r']

    #                    Vs.append(self.memory[t[0]]['r'])
    #                    self.my_logger.debug("TAKEDECISION tail state: "+ t[0] +" head state: "+
    #                                         t[1] +" V("+t[0]+") = "+ str(self.memory[t[0]]['V']))
    #                    self.my_logger.debug("TAKEDECISION transition cost from state:"+ str(t[1]) +" to state: "+ str(t[0]) +
    #                                         " is "+ str(stategraph.mu(t[1],t[0])))

    #                The original algo uses previous values of max reward (+ gamma * previous max), we don't
    #                if len(Vs) > 0:
    #                    V[s] = self.memory[str(s)]['r'] + float(self.utils.gamma) * max(Vs)
    #                else:
    #                    V[s] = self.memory[str(s)]['r']
                    V[s] = self.memory[str(s)]['r']

                self.my_logger.debug("TAKEDECISION Vs: "+ str(V) +", max V = "+ str(max(V)) +" V["+str(s)+"] "+ str(V[s]))

            # Find the max V
            self.nextState = max(V.iteritems(), key=operator.itemgetter(1))[0]
            #self.my_logger.debug("TAKEDECISION next state: "+ str(self.nextState))
            # Remember the V values calculated ???
            #for i in V.keys():
            #    self.memory[str(i)]['V'] = V[i]
            #    self.my_logger.debug("TAKEDECISION V("+ str(i) +") = "+ str(V[i]))

    #        vis = fuzz.visualization.VisManager.create_backend(stategraph)
    #        (vis_format, data) = vis.visualize()
    #
    #        with open("%s.%s" % ("states", vis_format), "wb") as fp:
    #            fp.write(data)
    #            fp.flush()
    #            fp.close()

            if self.nextState !=  self.currentState:
                self.my_logger.debug( "Decided to change state to_next: "+ str(self.nextState) + " from_curr: "+ str(self.currentState))
                # You've chosen to change state, that means that nextState has a greater reward, therefore d is always > 0
                d = self.memory[str(self.nextState)]['r'] - self.memory[str(self.currentState)]['r']
                if (self.memory[str(self.currentState)]['r'] > 0):
                    if (float(d) / self.memory[str(self.currentState)]['r'] < 0.1):
                        #false alarm, stay where you are
                        self.nextState = self.currentState
                        self.my_logger.debug( "ups changed my mind...staying at state: "+str(self.currentState)
                                          +" cause the gain difference is: "+str(abs(d))+" which is less than 10% of the current reward "+
                                          str(float(abs(d)) / self.memory[str(self.currentState)]['r'])+" "+
                                          str(self.memory[str(self.currentState)]['r']))
                # If the reward is the same with the state you're in, don't move
                elif (d == 0):
                    #false alarm, stay where you are
                    self.nextState = self.currentState
                    self.my_logger.debug( "ups changed my mind...staying at state: "+ str(self.currentState) +" cause the gain difference is: "+
                                          str(abs(d)) +" which is less than 10% of the current reward "+ str(self.memory[str(self.currentState)]['r']))

            if self.nextState > self.currentState:
                action = "add"
            elif self.nextState < self.currentState:
                action = "remove"

            self.my_logger.debug('action: ' + action)

            ## ACT
            self.my_logger.debug("Taking decision with acted: " + str(self.acted))
            ## Don't perform the action if we're debugging/simulating!!!
            if self.debug:
                if self.acted[len(self.acted)-1] == "done" and not action.startswith("none"):
                    self.acted.append("busy")
                    self.countdown = 5
                    #self.currentState = str(self.nextState)
                    self.my_logger.debug("TAKEDECISION simulation, action will finish in: " +
                                         str(self.countdown) + " mins")
                else:
                    self.my_logger.debug("TAKEDECISION Waiting for action to finish: " +  str(action) + str(self.acted))

            else:
                if self.acted[len(self.acted)-1] == "done" :
                    ## start the action as a thread
                    #thread.start_new_thread(self.polManager.act, (action, self.acted, self.currentState, self.nextState))
                    self.my_logger.debug("Action undertaken: " + str(action) + " current state: " + str(self.currentState)
                                         + " next: " + str(self.nextState))
                    self.currentState = self.nextState
                else: # shouldn't end up here
                    ## Action still takes place so do nothing
                    self.my_logger.debug("Waiting for action to finish: " +  str(action) +" "+ str(self.acted))

            action = "none"

            return True

    def simulate(self):
        self.my_logger.debug("START SIMULATION!!")
        ## creates a sin load simulated for an hour
#        for i in range(0, 3600, 10):
        #for i in range(0, 14400, 60): # 4 hours
        for i in range(0, 900, 1):
            cpu = max(5, 60 * abs(math.sin(0.05 * math.radians(i))) - int(self.currentState))
            # lamdba is the query arrival rate, throughput is the processed queries
            #l = 60000 + 40000 * math.sin(0.01 * i) + random.uniform(-4000, 4000)
            #l = 50000 * math.sin(60 * math.radians(i)/40) + 65000 + random.uniform(-8000, 8000)
            #l = 40000 * math.sin(60 * math.radians(i)/50) + 45000 + random.uniform(-4000, 4000)
            #l = 30000 * math.sin(0.02 * i) + 55000 + random.uniform(-4000, 4000)
            l = 60000 * math.sin(0.04 * i) + 75000 + random.uniform(-6000, 6000)
            # first 10 mins
#            if i < 1200:
#                l = 20000
#            elif i < 2400:
#                l = 40000
#            elif i < 4400:
#                l = 60000
#            elif i < 6000:
#                l = 40000
#            elif i < 7200:
#                l = 20000

            maxThroughput = (float(self.currentState) * float(env_vars["serv_throughput"]))
#            latency = 200 # msec
#            if (l > maxThroughput):
#                latency += (l-maxThroughput)/10 # +100msec for every 1000 reqs queued
            #throughput = min(maxThroughput, l)# max throughput for the current cluster
            throughput = l #(+/- e ??)
            latency = 0.0000004 * l**2 + 200 # msec...
            if l > maxThroughput:
                throughput = maxThroughput - 0.01 * l
                latency = 0.00001 * (l - maxThroughput)**2 + (0.0000004 * maxThroughput**2 + 200) # msec... ?

            values = {'latency': latency, 'cpu': cpu, 'inlambda': l, 'throughput': throughput,
                      'num_nodes': self.currentState}
            self.my_logger.debug("SIMULATE i: " + str(i) + " state: "+str(self.currentState) + " values:" + str(values)
                                 + " maxThroughput: " + str(maxThroughput))

            #nomizw de xreiazetai giati ginetai kai take_decision kai se debug mode
            #self.addMeasurement([self.currentState, str(l), str(throughput), str(latency), str(i)], True)
            #if self.acted[len(self.acted)-1] == "done" :
            self.take_decision(values)

            time.sleep(1)
        return


if __name__ == '__main__':
    fsm = RLDecisionMaker(4)
    fsm.simulate()
