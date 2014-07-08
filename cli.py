__author__ = 'cmantas'
import sys
from lib.tiramola_logging import get_logger
from os import remove, mkdir
from shutil import move

raw_args = sys.argv
args = dict()


def parse_args():
    chosen_function = raw_args[1]
    global args
    for arg in raw_args[2:]:
        i = arg.find("=")
        if i == -1:
            args[arg] = True
        else:
            key = arg[:i]
            value = arg[i+1:]
            args[key] = value
    return chosen_function

log = get_logger("CLI", 'INFO')

##############################  AVAILABLE ACTIONS  #######################################


def info():
        print """==============   USAGE   ==================
tiramola hosts
tiramola private_hosts
tiramola create_cluster nodes=2 clients=2
tiramola bootstrap_cluster used=8
tiramola load_data records=100000
tiramola run_sinusoid target=100 offset=80 period=60 #period time in minutes
tiramola add_nodes [count=2]
tiramola remove_nodes [count=2]
tiramola kill_workload
tiramola kill_nodes
tiramola destroy_servers
tiramola add_clients count=2
tiramola train
tiramola auto_pilot time=60 #time in minutes
"""


def load_data():
    try:
        record_count = int(args["records"])
        log.info("Loading %d records in the cluster" % record_count)
        import CassandraCluster, ClientsCluster
        svr_hosts = CassandraCluster.get_hosts(private=True)
        args['type'] = 'load'
        args['servers'] = svr_hosts
        ClientsCluster.run(args)
    except KeyError as e:
        log.info("record_count requires argument %s" % e.args[0])


def run_sinusoid():
    try:
        global target, period, offset
        target = int(args["target"])
        period = 60 * int(args["period"])
        args["period"] = period
        offset = int(args["offset"])
        log.info("running sinusoid for target=%d, offset=%d, period=%d sec" % (target, offset, period))
        import ClientsCluster, CassandraCluster
        svr_hosts = CassandraCluster.get_hosts(private=False)
        args['type'] = 'sinusoid'
        args['servers'] = svr_hosts
        ClientsCluster.run(args)
    except KeyError as e:
        log.info("run_sinusoid requires argument %s" % e.args[0])


def run_stress():
    log.info("running stress workload" )
    import ClientsCluster, CassandraCluster
    svr_hosts = CassandraCluster.get_hosts(private=True)
    params = {'type':'stress', 'servers': svr_hosts}
    ClientsCluster.run(params)


def create_cluster():
    try:
        nodes = int(args["nodes"])
        log.info("creating cluster with %d nodes " % nodes)
        import CassandraCluster
        CassandraCluster.create_cluster(nodes-1)
    except KeyError as e:
        log.info("create_cluster requires argument %s" % e.args[0])


def create_clients():
    try:
        nodes = int(args["nodes"])
        log.info("creating %d client nodes " % nodes)
        import ClientsCluster
        ClientsCluster.create_cluster(nodes)
    except KeyError as e:
        log.info("create_clients requires argument %s" % e.args[0])


def add_clients():
    if "count" in args.keys():
        count = int(args['count'])
    else:
        count = 1;
    log.info("adding %d clients" % count)
    import ClientsCluster
    ClientsCluster.add_nodes(count)


def remove_clients():
    if "count" in args.keys():
        count = int(args['count'])
    else:
        count = 1;
    log.info("removing %d clients" % count)
    import ClientsCluster
    ClientsCluster.remove_nodes(count)


def kill_workload():
    log.info("killing workload")
    import ClientsCluster
    ClientsCluster.kill_nodes()


def kill_nodes():
    log.info("killing cassandra nodes")
    import CassandraCluster
    CassandraCluster.kill_nodes()


def bootstrap_cluster():
    try:
        used = int(args['used'])
        log.info('Bootstraping Cluster with %d nodes' % used)
        import CassandraCluster
        CassandraCluster.bootstrap_cluster(used)
    except KeyError as e:
        log.error("bootstrap_cluster requires argument %s" % e.args[0])


def destroy_servers():
    import CassandraCluster
    CassandraCluster.destroy_all()


def destroy_clients():
    import ClientsCluster
    ClientsCluster.destroy_all()


def hosts():
    import CassandraCluster, ClientsCluster
    svr_hosts = CassandraCluster.get_hosts(include_stash=True)
    clnt_hosts = ClientsCluster.get_hosts()
    hosts = dict(svr_hosts.items() + clnt_hosts.items())
    rv = ""
    for h in hosts.keys():
            rv += hosts[h] + " " + h + "\n"
    print rv


def private_hosts():
    import CassandraCluster
    hosts = CassandraCluster.get_hosts(include_clients=True, private=True)
    rv = ""
    for h in hosts.keys():
            rv += hosts[h] + " " + h + "\n"
    print rv


def add_nodes():
    if "count" in args.keys():
        count = int(args['count'])
    else:
        count = 1;
    import CassandraCluster
    CassandraCluster.add_nodes(count)


def remove_nodes():
    if "count" in args.keys():
        count = int(args['count'])
    else:
        count = 1;
    import CassandraCluster
    CassandraCluster.remove_nodes(count)


def train():
    log.info(" Will run training routine. WARNING: will start workload automatically")
    import Coordinator
    Coordinator.train()


def auto_pilot():
    log.info("Running Tiramola Auto Provisioning super algorithm")
    global minutes
    try:
        minutes = int(args['time'])
    except KeyError as e:
        log.error("auto_pilot requires argument %s" % e.args[0])
        return
    secs = 60 * minutes
    import Coordinator
    Coordinator.run(secs)


def monitor():
    log.info("simply monitoring")
    global  env_vars
    env_vars["gain"] = '0'
    auto_pilot()


def simulate():
    try:
        remove("files/measurements/measurements.txt")
    except:
        pass
    from new_decision_module import RLDecisionMaker
    fsm = RLDecisionMaker("localhost", 8)
    fsm.simulate_training_set()
    from lib.draw_experiment import draw_exp
    try:
        mkdir("files/measurements/simulation/")
    except:
        pass
    move("files/measurements/measurements.txt", "files/measurements/simulation/measurements.txt")
    draw_exp("files/measurements/simulation/measurements.txt")


def run_experiments():

    try:
        experiment_file = args['file']
    except KeyError as e:
        log.error("run_experiments requires argument %s" % e.args[0])
        return
    import Experiment
    Experiment.run_experiments(experiment_file)


def repair():
    import CassandraCluster
    CassandraCluster.repair_cluster()



############################   MAIN  ################################################


function = parse_args()

try:
    #just call the appropriate function with eval!
    eval(function+"()")
except NameError as ne:
    log.error("No such action")
    print str(ne)
    info()
