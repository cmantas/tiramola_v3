__author__ = 'cmantas'
import sys
from lib.tiramola_logging import get_logger
from os import remove, mkdir
from shutil import move
from time import strftime
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
tiramola destroy_all
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
        log.info("creating cluster with %d nodes " % nodes)
        import CassandraCluster
        CassandraCluster.create_cluster(nodes-1)
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
    try:
        used = int(args['used'])
        log.info('Bootstraping Cluster with %d nodes' % used)
        import CassandraCluster
        CassandraCluster.bootstrap_cluster(used)
    except KeyError as e:
        log.error("bootstrap_cluster requires argument %s" % e.args[0])


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


def train():
    log.info(" Will run training routine. WARNING: will start load automatically")
    import Coordinator
    Coordinator.train()


def auto_pilot():
    log.info("Running Tiramola Auto Provisioning super algorithm")
    try:
        global minutes
        minutes = int(args['time'])
        secs = 60 * minutes
        import Coordinator
        Coordinator.run(secs)
    except KeyError as e:
        log.error("auto_pilot requires argument %s" % e.args[0])


def experiment():
    log.info("Running a full experiment")
    run_sinusoid()
    try:
        remove("files/measurements/measurements.txt")
    except:
        pass
    auto_pilot()

    #move the newly generated measurements
    info_short = "target=%dK,offset=%dK,period=%dmin" % (target/1000, offset/1000, period)
    #dir_path = "files/measurements/"+strftime('%b%d-%H:%M')
    dir_path = "files/measurements/"+info_short
    mkdir(dir_path)
    move("files/measurements/measurements.txt", dir_path)

    #draw the result graphs
    from lib.draw_experiment import draw_exp
    draw_exp(dir_path+"/measurements.txt")

    #kill the workload
    kill_workload()
    info_long = "target = %d\noffset = %d\nperiod = %dmin\nduration = %dmin\ndate = %s" %\
           (target, offset, period/60, minutes, strftime('%b%d-%H:%M'))

    #write information to file
    with open (dir_path+"/info", 'w+') as f:
        f.write(info_long)

    log.info("EXPERIMENT DONE: Result measurements in: "+dir_path)


def draw():
    from lib.draw_experiment import draw_exp
    draw_exp("files/measurements/measurements.txt")



############################   MAIN  ################################################


function = parse_args()

try:
    #just call the appropriate function with eval!
    eval(function+"()")
except NameError:
    log.error("No such action")
    info()
