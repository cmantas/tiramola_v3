__author__ = 'cmantas'
import sys

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



##############################  AVAILABLE ACTIONS  #######################################

def info():
        print """==============   USAGE   ==================
tiramola hosts
tiramola private_hosts
tiramola create_cluster nodes=2 clients=2
tiramola bootstrap_cluster
tiramola load_data records=100000
tiramola run_sinusoid target=100 offset=80 period=60
tiramola add_node
tiramola remove_node
tiramola kill_workload
tiramola kill_nodes
tiramola destroy_all
"""


def load_data():
    try:
        record_count = int(args["records"])
        print "CLI: Loading %d records in the cluster" % record_count
        import CassandraCluster
        CassandraCluster.run_load_phase(record_count)
    except KeyError as e:
        print "CLI: record_count requires argument %s" % e.args[0]


def run_sinusoid():
    try:
        target = int(args["target"])
        period = int(args["period"])
        offset = int(args["offset"])
        print "CLI: running sinusoid for target=%d, offset=%d, period=%d" % (target, offset, period)
        import CassandraCluster
        CassandraCluster.run_sinusoid(target, offset, period)
    except KeyError as e:
        print "CLI: run_sinusoid requires argument %s" % e.args[0]


def create_cluster():
    try:
        nodes = int(args["nodes"])
        clients = int(args["clients"])
        print "CLI: creating cluster with %d nodes and %d clients" % (nodes, clients)
        import CassandraCluster
        CassandraCluster.create_cluster(nodes-1, clients)
    except KeyError as e:
        print "CLI: create_cluster requires argument %s" % e.args[0]


def kill_workload():
    print "CLI: killing workload"
    import CassandraCluster
    CassandraCluster.kill_clients()


def kill_nodes():
    print "CLI: killing cassandra nodes"
    import CassandraCluster
    CassandraCluster.kill_nodes()


def bootstrap_cluster():
    import CassandraCluster
    CassandraCluster.bootstrap_cluster()


def destroy_all():
    import CassandraCluster
    CassandraCluster.destroy_all()


def hosts():
    import CassandraCluster
    hosts = CassandraCluster.get_hosts(include_clients=True)
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


def add_node():
    import CassandraCluster
    CassandraCluster.add_node()


def remove_node():
    import CassandraCluster
    CassandraCluster.remove_node()


def run_coordinator():
    import Coordinator


############################   MAIN  ################################################


function = parse_args()

try:
    #just call the appropriate function with eval!
    eval(function+"()")
except NameError:
    print "CLI: No such action"
    info()