__author__ = 'cmantas'
from time import sleep
import CassandraCluster as Servers
import ClientsCluster as Clients
from lib.persistance_module import env_vars
from Monitoring import MonitorVms
from new_decision_module import RLDecisionMaker as DM
from lib.tiramola_logging import get_logger
import thread

####### Variables  ###############
my_logger = get_logger('COORDINATOR', 'INFO', logfile='files/logs/Coordinator.log')
my_logger.debug("--------- NEW RUN  -----------------")

#the (pending) decision at the present moment
decision = None


def implement_decision():
    """
    Used to asynchronously implement the decision that has been updated  by the run function
    """
    global decision
    action = decision["action"]
    count = decision['count']

    if action == "ADD":
        decision_module.pending_action = action
        my_logger.info("Will add %d nodes" % count)
        Servers.add_nodes(count)
    elif action == "REMOVE":
        decision_module.pending_action = action
        my_logger.info("Will remove %d nodes" % count)
        Servers.remove_nodes(count)
    elif action == "PASS":
        return
    decision_module.pending_action = None
    decision_module.currentState = Servers.node_count()


#check if cluster exists
if Servers.exists():
    my_logger.info( "Cluster exists using it as is")
    #make sure no workload is running
else:
    my_logger.error("Create the cluster first and then run the coordinator")
    exit(-1)

#get the endpoint for the monitoring system
monitoring_endpoint = Clients.get_monitoring_endpoint()
#refresh metrics
monVms = MonitorVms(monitoring_endpoint)


def run():
    """
    Runs cluster with automatic decision taking
    """
    global decision_module
    decision_module = DM(monitoring_endpoint, Servers.node_count())
    #the time interval between metrics refresh
    metrics_interval = env_vars["metric_fetch_interval"]
    while True:
    # main loop that fetches metric and takes decisions
        sleep(metrics_interval)
        all_metrics = monVms.refreshMetrics()
        global decision
        decision = decision_module.take_decision(all_metrics)
        thread.start_new(implement_decision, ())


def train():
    """
    Runs a training phase in order to collect a training set of metrics for the given cluster
    """
    #change the gain function for training purposes
    env_vars['gain'] = 'num_nodes'
    # load the training vars
    t_vars = env_vars["training_vars"]
    env_vars['decision_interval'] = t_vars['decision_interval']
    env_vars['period'] = t_vars['period']
    env_vars['max_cluster_size'] = t_vars['max_cluster_size']
    env_vars['min_cluster_size'] = t_vars['min_cluster_size']
    #get the server hostnames and addresses
    svr_hosts = Servers.get_hosts(private=True)
    #create the parameters dictionary for the training phase
    params = {'type': 'sinusoid', 'servers': svr_hosts, 'target': t_vars['target_load'],
              'offset': t_vars['offset_load'], 'period': t_vars['period']}
    #run the workload with the specified params to the clients
    Clients.run(params)
    #now run as usual
    run()

if __name__ == "__main__":
    train()

