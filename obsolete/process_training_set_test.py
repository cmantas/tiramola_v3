__author__ = 'cmantas'

filename = 'files/measurements/clean-metrics.txt'


class Metric:
    def __init__(self, state, lamda, throughput, latency):
        self.state = int(round(float(state)))
        self.lamda = int(round(float(lamda)))
        self.throughput = int(round(float(throughput)))
        self.latency = float(latency)

    def __str__(self):
        return "state: %d, lambda: %d, throughput: %d, latency: %f" % \
               (self.state, self.lamda, self.throughput, self.latency)


metrics = []

#parse metrics
for line in open(filename, 'r'):
    ll = line.split()
    metric = Metric(ll[0], ll[1], ll[2], ll[3])
    metrics.append(metric)

min_lambda = (min(metrics, key=lambda x: x.lamda)).lamda
max_lambda = (max(metrics, key=lambda x: x.lamda)).lamda

min_state = (min(metrics, key=lambda x: x.state)).state
max_state = (max(metrics, key=lambda x: x.state)).state

#sort my lambda
#metrics.sort(key=lambda x: x.lamda)


#emprical
tp_per_node = 800


representative_metrics = []

# clusterize by lambda
min_cluster_lambda = 0
for state in range(min_state, max_state+1):
    max_cluster_lambda = tp_per_node * state
    cluster = [m for m in metrics if (m.lamda<max_cluster_lambda and m.lamda>=min_cluster_lambda)]
    min_cluster_lambda = max_cluster_lambda

    #process this cluster
    if len(cluster) == 0:
        continue
    min_cluster_state = (min(metrics, key=lambda x: x.state)).state
    max_cluster_state = (max(metrics, key=lambda x: x.state)).state
    #for each of the states in this cluster
    for state in range(min_cluster_state, max_cluster_state):
        #find the metrics in this state
        state_metrics = [m for m in cluster if m.state == state]

        #process latencies for this state
        min_state_latency = (min(state_metrics, key=lambda x: x.latency)).latency
        max_state_latency = (max(state_metrics, key=lambda x: x.latency)).latency
        avg_latency = sum( [m.latency for m in state_metrics ]) / len(state_metrics)
        median_latency = state_metrics[len(state_metrics)/2].latency
        print 'State %2s. Latency: min %3.3f, avg %3.3f, median %3.3f, max %3.3f' % \
              (state, min_state_latency, avg_latency, median_latency, max_state_latency)

        #process throughput for this state

        avg_throughput = sum([m.throughput for m in state_metrics]) / len(state_metrics)
        print "average throughput = " + str(avg_throughput)

        #keep only one representative metric
        representative_metrics.append( Metric(state, (max_cluster_lambda+min_cluster_lambda)/2, avg_throughput, median_latency))




## export the representative metrics to json list

exported_metrics = []

for m in representative_metrics:
    exported_metrics.append({"lambda": m.lamda, "state": m.state, 'throughput': m.throughput, 'latency': m.latency})


from json import dump

dump(exported_metrics, file("files/measurements/processed_metrics.json", "w+"), indent=3    )