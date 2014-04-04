__author__ = 'cmantas'

import CassandraCluster as Cluster
from lib.persistance_module import env_vars
from time import sleep
from Monitoring import MonitorVms
from new_decision_module import RLDecisionMaker as DM
import logging
import  sys
import thread

####### Variables  ###############
initial_cluster_size = env_vars["min_cluster_size"]
clients_count = env_vars["clients_count"]
metrics_interval = env_vars["metric_fetch_interval"]

level = logging.DEBUG
my_logger = logging.getLogger('Coordinator')
my_logger.setLevel(level)

handler = logging.handlers.RotatingFileHandler('files/logs/Coordinator.log', maxBytes=2 * 1024 * 1024, backupCount=5)
handler2 = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("[%(levelname)s] %(name)s : %(message)s")
handler2.setFormatter(formatter)
my_logger.handlers = []
my_logger.addHandler(handler)
my_logger.addHandler(handler2)


def implement_decision():
    action = decision["action"]
    count = decision['count']
    decision_module.pending_action = action
    if action == "ADD":
        my_logger.info("will add %d nodes" % count)
        Cluster.add_nodes(count)
    elif action == "REMOVE":
        my_logger.info("will remove %d nodes" % count)
        Cluster.remove_nodes(count)
    elif action == "PASS":
        my_logger.info("doing nothing")
    decision_module.pending_action = None
    decision_module.currentState = Cluster.node_count()



#check if cluster exists and create it if not
if Cluster.exists():
    my_logger.info( "Cluster exists")
    #make sure no workload is running
    Cluster.kill_clients()
else:
    #create the cluster
    Cluster.create_cluster(initial_cluster_size-1, clients_count)
    Cluster.bootstrap_cluster()
    t_vars = env_vars["training_vars"]
    Cluster.run_load_phase(t_vars['total_records'])
    #waiting for load to finish
    my_logger.info('COORDINATOR: Sleeping a while after load phase')
    sleep(300)
    pass

#get the endpoint for the monitoring system
monitoring_endpoint = Cluster.get_monitoring_endpoint()
#refresh metrics
monVms = MonitorVms(monitoring_endpoint)

decision_module = DM(monitoring_endpoint, Cluster.node_count())


def run():
    while True:
    # main loop that fetches metric and takes decisions
        sleep(metrics_interval)
        all_metrics = monVms.refreshMetrics()
        global decision
        decision = decision_module.take_decision(all_metrics)
        thread.start_new(implement_decision, ())


def train():
    #change the gain function for training purposes
    env_vars['gain'] = 'num_nodes'
    t_vars = env_vars["training_vars"]
    Cluster.run_sinusoid(t_vars['target_load'], t_vars['offset_load'], t_vars['period'])
    #hinder the first decision
    run()


train()

