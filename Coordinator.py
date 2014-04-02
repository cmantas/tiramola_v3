__author__ = 'cmantas'

import CassandraCluster as Cluster
from lib.persistance_module import env_vars
from time import sleep
from Monitoring import MonitorVms


####### Variables  ###############
initial_cluster_size = env_vars["initial_cluster_size"]
clients_count = env_vars["clients_count"]
metrics_interval = env_vars["metric_fetch_interval"]




#check if cluster exists and create it if not
if Cluster.exists():
    print "Cluster exists \n %s" % str(Cluster.get_hosts())
else:
    # Cluster.create_cluster(initial_cluster_size-1, clients_count)
    # Cluster.bootstrap_cluster()
    pass

#get the endpoint for the monitoring system
monitoring_endpoint = Cluster.get_monitoring_endpoint()
#refresh metrics
monVms = MonitorVms("snf-490086.vm.okeanos.grnet.gr")




while True:
# main loop that fetches metric and takes decisions
    sleep(metrics_interval)
    allmetrics = monVms.refreshMetrics()
    # decision = dm.take_decision(allmetrics)
    # enforce(decision)
    print "allmetrics length ", len(allmetrics)
