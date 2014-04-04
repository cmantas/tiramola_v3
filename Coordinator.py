__author__ = 'cmantas'

import CassandraCluster as Cluster
from lib.persistance_module import env_vars
from time import sleep
from Monitoring import MonitorVms
from new_decision_module import RLDecisionMaker as DM

####### Variables  ###############
initial_cluster_size = env_vars["initial_cluster_size"]
clients_count = env_vars["clients_count"]
metrics_interval = env_vars["metric_fetch_interval"]


def implement_decision():
    action = decision["action"]
    count = decision['count']
    if action == "ADD":
        print "will add nodes"
    elif action == "REMOVE":
        print "will remove nodes"
    elif action == "PASS":
        print "doing nothing"



#check if cluster exists and create it if not
if Cluster.exists():
    print "Cluster exists"
else:
    # Cluster.create_cluster(initial_cluster_size-1, clients_count)
    # Cluster.bootstrap_cluster()
    pass

#get the endpoint for the monitoring system
monitoring_endpoint = Cluster.get_monitoring_endpoint()
#refresh metrics
monVms = MonitorVms(monitoring_endpoint)

decision_module = DM(monitoring_endpoint, Cluster.node_count())


while True:
# main loop that fetches metric and takes decisions
    sleep(metrics_interval)
    allmetrics = monVms.refreshMetrics()
    decision = decision_module.take_decision(allmetrics)
    print decision
    implement_decision(decision)
