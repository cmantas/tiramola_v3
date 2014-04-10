__author__ = 'cmantas'
import sys
from lib.tiramola_logging import get_logger
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
tiramola bootstrap_cluster
tiramola load_data records=100000
tiramola run_sinusoid target=100 offset=80 period=60
tiramola add_nodes [count=2]
tiramola remove_nodes [count=2]
tiramola kill_workload
tiramola kill_nodes
tiramola destroy_all
tiramola add_clients count=2
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
        target = int(args["target"])
        period = int(args["period"])
        offset = int(args["offset"])
        log.info("running sinusoid for target=%d, offset=%d, period=%d" % (target, offset, period))
        import ClientsCluster, CassandraCluster
        svr_hosts = CassandraCluster.get_hosts(private=True)
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
        if 'clients' in args:
            clients = int(args["clients"])
        else:
            clients = 0
        log.info("creating cluster with %d nodes and %d clients" % (nodes, clients))
        import CassandraCluster
        CassandraCluster.create_cluster(nodes-1, clients)
    except KeyError as e:
        log.info("create_cluster requires argument %s" % e.args[0])


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
    import CassandraCluster
    CassandraCluster.bootstrap_cluster()


def destroy_all():
    import CassandraCluster
    CassandraCluster.destroy_all()


def hosts():
    import CassandraCluster, ClientsCluster
    svr_hosts = CassandraCluster.get_hosts()
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


def run_coordinator():
    import Coordinator


############################   MAIN  ################################################


function = parse_args()

try:
    #just call the appropriate function with eval!
    eval(function+"()")
except NameError:
    log.error("No such action")
    info()