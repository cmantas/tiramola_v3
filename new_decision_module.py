__author__ = 'tiramola group'

import CassandraCluster
import os
from lib.fuzz import fgraph, fset
import datetime, operator
import thread
from scipy.stats import linregress
import numpy as np



def __init__(cluster, ):
    pass


def takeDecision(self, rcvallmetrics):
        '''
         this method reads allmetrics object created by MonitorVms and decides to change the number of participating
         virtual nodes.
        '''
        ## Take decision based on metrics
        action = "none"

#        self.my_logger.debug("TAKEDECISION rcvallmetrics: " + str(rcvallmetrics))
        allmetrics = None
        allmetrics = rcvallmetrics.copy()
        self.my_logger.debug("TAKEDECISION state: " + str(self.currentState))

#        if not self.acted[len(self.acted)-1].startswith("done") :
#            self.my_logger.debug("Last action "+ str(self.acted[len(self.acted)-1]) +" hasn't finished yet, see you later!")
#            return True

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
            nodes = 0
            for host in allmetrics.values():
                if isinstance(host,dict):
                    # Commented out the following line because if I don't use client1, I won't collect any of the clients' metrics
                    #if host.has_key("ycsb_LAMDA_1"):
                    for key in host.keys():
                        if key.startswith('ycsb_LAMDA'):
                            allmetrics['inlambda'] += float(host[key])
                        if key.startswith('ycsb_THROUGHPUT'):
                            allmetrics['throughput'] += float(host[key])
                        if key.startswith('ycsb_READ') or key.startswith('ycsb_UPDATE') or key.startswith('ycsb_RMW') or key.startswith('ycsb_INSERT'):
                            allmetrics['latency'] += float(host[key])
#                            self.my_logger.debug("Latency : "+ str(host[key]) +" collected from client: "+ str(key) +
#                                                 " latency so far: "+ str(allmetrics['latency']))
                            if host[key] > 0:
                                clients += 1
                    for key in host.keys():
                        if key.startswith('cpu_nice') or key.startswith('cpu_wio') or key.startswith('cpu_user') or key.startswith('cpu_system'):
                            allmetrics['cpu'] += float(host[key])
                            #nodes += 1
                    nodes += 1
#                    self.my_logger.debug("Collecting metrics of host: " + str(host))
            try:
                allmetrics['latency'] = allmetrics['latency'] / clients
#                self.my_logger.debug("Final latency for this measurement: "+ str(allmetrics['latency']) +" by "+ str(clients)+ " clients!")
            except:
                allmetrics['latency'] = 0

            try:
                allmetrics['cpu'] = allmetrics['cpu'] / nodes # average node cpu usage
            except:
                allmetrics['cpu'] = 0

        #self.my_logger.debug( "TAKEDECISION allmetrics: " + str(allmetrics))

        #1. Save the current metrics in memory.
#        self.addMeasurement([str(self.currentState), allmetrics['inlambda'], allmetrics['throughput'], allmetrics['latency'],
#                             allmetrics['cpu'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")], True)

        #self.my_logger.debug("gmetric -n ycsb_throughput -v "+ str(allmetrics['throughput'])+" -d 15 -t float -u 'reqs/sec' -S "+ str(self.NoSQLCluster.cluster[str(self.utils.hostname_template)+"master"].private_dns_name) +":" +str(self.utils.hostname_template)+ "master")
        # Publish measurements to ganglia
        try:
            os.system("gmetric -n ycsb_inlambda -v "+ str(allmetrics['inlambda'])+" -d 15 -t float -u 'reqs/sec' -S "+ str(self.NoSQLCluster.cluster[str(self.utils.hostname_template)+"master"].private_dns_name) +":" +str(self.utils.hostname_template)+ "master")
            os.system("gmetric -n ycsb_throughput -v "+ str(allmetrics['throughput'])+" -d 15 -t float -u 'reqs/sec' -S "+ str(self.NoSQLCluster.cluster[str(self.utils.hostname_template)+"master"].private_dns_name) +":" +str(self.utils.hostname_template)+ "master")
            os.system("gmetric -n ycsb_latency -v "+ str(allmetrics['latency']) + " -d 15 -t float -u ms -S " +  str(self.NoSQLCluster.cluster[str(self.utils.hostname_template)+"master"].private_dns_name) +":" +str(self.utils.hostname_template)+ "master")
            os.system("gmetric -n ycsb_cpu -v "+ str(allmetrics['CPU']) + " -d 15 -t float -u 'Percent' -S " +  str(self.NoSQLCluster.cluster[str(self.utils.hostname_template)+"master"].private_dns_name) +":" +str(self.utils.hostname_template)+ "master")
        except:
            pass


        if not self.acted[len(self.acted)-1].startswith("done") :
            # Take decision as soon as decisions are unblocked.
            self.waitForIt = 0
            self.my_logger.debug("Last action "+ str(self.acted[len(self.acted)-1]) +" hasn't finished yet, see you later!")
            if self.acted[len(self.acted)-1].startswith("remove"):
                #1. Save the current metrics in memory.
                self.addMeasurement([str(self.currentState), allmetrics['inlambda'], allmetrics['throughput'], allmetrics['latency'],
                             allmetrics['cpu'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")], True)
            elif self.acted[len(self.acted)-1].startswith("add"):
                self.my_logger.debug("Discarding measurement: "+ str([str(self.currentState), allmetrics['inlambda'], allmetrics['throughput'], allmetrics['latency'],
                             allmetrics['cpu'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]))
                dms = open(self.utils.install_dir+'/logs/discarded-measurements.txt', 'a')
                # metrics[5] contains the time tick -- when running a simulation, it represents the current minute,
                # on actual experiments, it is the current time. Used for debugging and plotting
                dms.write(str(self.currentState)+'\t\t'+str(allmetrics['inlambda'])+'\t\t'+str(allmetrics['throughput'])+'\t\t'+
                     str(allmetrics['latency'])+'\t\t'+str(allmetrics['cpu'])+'\t\t'+
                     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'\n')
                dms.close()
            return True

        #1. Save the current metrics in memory.
        self.addMeasurement([str(self.currentState), allmetrics['inlambda'], allmetrics['throughput'], allmetrics['latency'],
                             allmetrics['cpu'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")], True)

        if self.waitForIt == 0:
            self.waitForIt = 10
        else:
            self.my_logger.debug("New decision in " + str(float(self.waitForIt)/2) + " mins, see you later!")
            self.waitForIt = self.waitForIt - 1
            return True

        states = fset.FuzzySet()

        # Select values close to the current throughtput
        # define tha lambda range we're interested in -+ 5%
        from_inlambda = 0.95 * allmetrics['inlambda']
        to_inlambda = 1.05 * allmetrics['inlambda']
#        from_inlambda = allmetrics['inlambda'] - 3000
#        to_inlambda = allmetrics['inlambda'] + 3000

        self.my_logger.debug("TAKEDECISION current lambda: " + str(allmetrics['inlambda']) + " lambda range: " +
                             str(from_inlambda) + " - " + str(to_inlambda))
        # too low to care, the initial num of nodes can answer 1000 req/sec, so consider it as 0 1000 * len(cluster.size)!!
        if 0.0 < to_inlambda < 1000:
            from_inlambda = 0.0
            self.my_logger.debug("TAKEDECISION current lambda: " + str(allmetrics['inlambda']) + " changed lambda range to: " +
                             str(from_inlambda) + " - " + str(to_inlambda))
        # Create the graph using the values in memory if any, or defaults
        for i in range(int(self.utils.initial_cluster_size), int(self.utils.max_cluster_size)+1): ## !!
            vals = {}

            #vals['max_throughput'] = float(i) * float(self.utils.serv_throughput) # arxiki timi se periptwsi pou den exeis 3anadei to state upologizei poso tha ithele na einai to throughput
            vals['num_nodes'] = i
            # != currrent state
            if int(self.currentState) != i:
            met = {}
            if self.measurementsPolicy.startswith('average'):
                met = self.getAverages(str(i))
            elif self.measurementsPolicy.startswith('centroid'):
                met = self.doKmeans(str(i), from_inlambda, to_inlambda)
                #self.my_logger.debug("TAKEDECISION state: "+ str(i) +" met: "+ str(met))
                if met != None and len(met) > 0 :
                    vals['inlambda'] = met['inlambda']
                    vals['throughput'] = met['throughput']
                    vals['latency'] = met['latency']
                    vals['cpu'] = met['cpu']
                    self.my_logger.debug( "TAKEDECISION kmeans metrics' state " + str(i) + " values: " + str(vals))
                    # Been in this state before, use the measurements
                    self.memory[str(i)]['r'] = eval(self.utils.gain, vals)
                    #self.my_logger.debug("TAKEDECISION adding visited state "+ str(i) +" with gain "+ str(self.memory[str(i)]['r']))
                else:
                    # No clue for this state use defaults/current measurements...
                    vals['inlambda'] = allmetrics['inlambda']
                    vals['throughput'] = allmetrics['throughput']
                    vals['latency'] = allmetrics['latency']
                    self.my_logger.debug( "TAKEDECISION state " + str(i) + " default values allmetrics: " + str(vals))
                    self.memory[str(i)]['r'] = eval(self.utils.gain, vals)

                    #self.my_logger.debug("TAKEDECISION adding state "+ str(i) +" with gain "+ str(self.memory[str(i)]['r']))
                if int(self.currentState) != i:
                    states.add(fset.FuzzyElement(str(i), self.memory[str(i)]['r']))
            # The current state, use current measurement
            #else:
            if int(self.currentState) == i:
                allmetrics['max_throughput'] = i * float(self.utils.serv_throughput)
                allmetrics['num_nodes'] = i
                cur_gain = eval(self.utils.gain, allmetrics)
                self.my_logger.debug("TAKEDECISION state "+ str(i) +" current reward : "+ str(cur_gain) +" training set reward: "+
                                     str(self.memory[str(i)]['r']))
                self.memory[str(i)]['r'] = cur_gain
                states.add(fset.FuzzyElement(str(i), cur_gain))


        v=[]

        for i in states.keys():
            v.append(i)

        v = set(v)

        stategraph = fgraph.FuzzyGraph(viter = v, directed = True)

        # The subgraph we are interested in. It contains only the allowed transitions from the current state.
        from_node = max(int(self.utils.initial_cluster_size), (int(self.currentState) - int(self.utils.rem_nodes)))
        to_node = min((int(self.currentState) + int(self.utils.add_nodes)), int(self.utils.max_cluster_size))
#        self.my_logger.debug("TAKEDECISION creating graph from node: max("+ self.utils.initial_cluster_size +", "+
#                             self.currentState +" - "+ self.utils.rem_nodes +") = "+ str(from_node) +" to node: min("+
#                             self.currentState +" + "+ self.utils.add_nodes +", "+ self.utils.max_cluster_size +") = "+ str(to_node))
        for j in range(from_node, to_node+1):
            if j != int(self.currentState):
                # Connect nodes with allowed transitions from the current node.connect(tail, head, mu)
                stategraph.connect(str(j), self.currentState, eval(self.utils.trans_cost, allmetrics))
#                self.my_logger.debug("TAKEDECISION connecting state "+ self.currentState +" with state "+ str(j))
                # Connect nodes with allowed transitions from node j.
                for k in range(max(int(self.utils.initial_cluster_size), j - int(self.utils.rem_nodes)), min(j + int(self.utils.add_nodes), int(self.utils.max_cluster_size))+1):
                    if k != j:
#                        self.my_logger.debug("TAKEDECISION connecting state "+ str(j) +" with state "+ str(k))
                        stategraph.connect(str(k), str(j), eval(self.utils.trans_cost, allmetrics))

        #Calculate the V matrix for available transitions
        V = {}

        for s in range(from_node, to_node+1):
            # Get allowed transitions from this state.
            if self.memory[str(s)]['r'] != None:
                # For each state s, we need to calculate the transitions allowed.
                allowed_transitions = stategraph.edges(head=str(s))

                Vs = []

                for t in allowed_transitions:
                    # No V from last run
                    if self.memory[t[0]]['V'] == None:
                        self.memory[t[0]]['V'] = self.memory[t[0]]['r']
                    # t[0] is the tail state of the edge (the next state)
                    Vs.append(self.memory[t[0]]['V'])
#                    self.my_logger.debug("TAKEDECISION tail state: "+ t[0] +" head state: "+
#                                         t[1] +" V("+t[0]+") = "+ str(self.memory[t[0]]['V']))
#                    self.my_logger.debug("TAKEDECISION transition cost from state:"+ str(t[1]) +" to state: "+ str(t[0]) +
#                                         " is "+ str(stategraph.mu(t[1],t[0])))
#                if len(Vs) > 0:
#                    V[s] = self.memory[str(s)]['r'] + float(self.utils.gamma) * max(Vs)
#                else:
#                    V[s] = self.memory[str(s)]['r']
                V[s] = self.memory[str(s)]['r']
#                self.my_logger.debug("TAKEDECISION Vs: "+ str(Vs) +", max V = "+ str(max(Vs)) +" V["+str(s)+"] "+ str(V[s]))

        # Find the max V
        self.nextState = str(max(V.iteritems(), key=operator.itemgetter(1))[0])
        #self.my_logger.debug("TAKEDECISION next state: "+ str(self.nextState))
        # Remember the V values calculated ???
        for i in V.keys():
            self.memory[str(i)]['V'] = V[i]
            self.my_logger.debug("TAKEDECISION V("+ str(i) +") = "+ str(V[i]))

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

        if int(self.nextState) > int(self.currentState):
            action = "add"
        elif int(self.nextState) < int(self.currentState):
            action = "remove"

        self.my_logger.debug('action: ' + action)

        ## ACT
        self.my_logger.debug("Taking decision with acted: " + str(self.acted))
        ## Don't perform the action if we're debugging/simulating!!!
        if self.debug :
            if self.acted[len(self.acted)-1] == "done" and not action.startswith("none"):
                self.acted.append("busy")
                self.countdown = 5
                #self.currentState = str(self.nextState)
            else:
                self.my_logger.debug("TAKEDECISION Waiting for action to finish: " +  str(action) + str(self.acted))

        else :
            if self.acted[len(self.acted)-1] == "done" :
                ## start the action as a thread
                thread.start_new_thread(self.polManager.act, (action, self.acted, self.currentState, self.nextState))
                self.my_logger.debug("Action undertaken: " + str(action) + " current state: " + str(self.currentState)
                                     + " next: " + str(self.nextState))
                self.currentState = self.nextState
            else: # shouldn't end up here
                ## Action still takes place so do nothing
                self.my_logger.debug("Waiting for action to finish: " +  str(action) +" "+ str(self.acted))

        action = "none"

        return True