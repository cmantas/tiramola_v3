__author__ = 'cmantas'

import CassandraCluster as Servers
import ClientsCluster as Clients
from lib.persistance_module import env_vars
from time import sleep
from Monitoring import MonitorVms
from new_decision_module import RLDecisionMaker as DM
from lib.tiramola_logging import get_logger
import logging
import  sys
import thread

####### Variables  ###############
initial_cluster_size = env_vars["min_cluster_size"]
clients_count = env_vars["clients_count"]
metrics_interval = env_vars["metric_fetch_interval"]

level = logging.DEBUG
my_logger = log = get_logger('COORDINATOR', 'INFO', logfile='files/logs/Coordinator.log')
my_logger.debug("--------- NEW RUN  -----------------")

#the pending decision at the moment
decision = None


def implement_decision():
    """
    Used to asynchronously implement the decision that has been updated  by the run function
    """
    global decision
    action = decision["action"]
    count = decision['count']
    decision_module.pending_action = action
    if action == "ADD":
        my_logger.info("Will add %d nodes" % count)
        Servers.add_nodes(count)
    elif action == "REMOVE":
        my_logger.info("Will remove %d nodes" % count)
        Servers.remove_nodes(count)
    elif action == "PASS":
        my_logger.debug("doing nothing")
    decision_module.pending_action = None
    decision_module.currentState = Servers.node_count()



#check if cluster exists and create it if not
if Servers.exists():
    my_logger.info( "Cluster exists")
    #make sure no workload is running
    Clients.kill_nodes()
else:
    #create the cluster
    Servers.create_cluster(initial_cluster_size-1)
    Clients.create_cluster(clients_count)
    Servers.bootstrap_cluster()
    t_vars = env_vars["training_vars"]
    Servers.run_load_phase(t_vars['total_records'])
    #waiting for load to finish
    my_logger.info('Sleeping a while after load phase')
    sleep(300)
    pass

#get the endpoint for the monitoring system
monitoring_endpoint = Clients.get_monitoring_endpoint()
#refresh metrics
monVms = MonitorVms(monitoring_endpoint)
decision_module = DM(monitoring_endpoint, Servers.node_count())


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
    env_vars['gain'] = '100*num_nodes'
    env_vars['decision_interval'] = 60
    t_vars = env_vars["training_vars"]
    global decision_module
    decision_module.waitForIt = env_vars['decision_interval']/ env_vars['metric_fetch_interval']
    svr_hosts = Servers.get_hosts(private=True)
    params = {'type': 'sinusoid', 'servers': svr_hosts, 'target': t_vars['target_load'],
              'offset': t_vars['offset_load'], 'period': t_vars['period']}
    Clients.run(params)

    #hinder the first decision
    run()


train()

