__author__ = 'cmantas'
import sys, traceback
from lib.tiramola_logging import get_logger
from os import remove, mkdir
from shutil import move, copy
from time import strftime
from os.path import isdir
from random import random
from json import load, dumps

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
    log.info(" Will run training routine. WARNING: will start workload automatically")
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
    try:
        experiment_name = args['name']
    except KeyError as e:
        log.error("experiment requires argument %s" % e.args[0])
        return

    log.info("Running a full experiment")
    run_sinusoid()
    try:
        #empty the contents of the coordinator.log
        open('files/logs/Coordinator.log', 'w+').close()
        #f = open('file.txt', 'r+')
        #f.truncate()
    except:
        pass

    auto_pilot()

    #kill the workload
    kill_workload()

    global dir_path
    dir_path = "files/measurements/"+experiment_name

    if isdir(dir_path):
        dir_path += "_"+str(int(random()*1000))
    try:
        mkdir(dir_path)
    except:
        log.error("Could not create experiment directory")

    move("files/measurements/measurements.txt", dir_path)

    info_long = "target = %d\noffset = %d\nperiod = %dmin\nduration = %dmin\ndate = %s" %\
           (target, offset, period/60, minutes, strftime('%b%d-%H:%M'))
    from lib.persistance_module import env_vars
    info_long += "\ngain = " + env_vars['gain']
    info_long += "\ndecision_interval = " + str(env_vars['decision_interval'])
    info_long += "\ndecision_threshold = " + str(int(float(env_vars['decision_threshold'])*100)) + "%"
    try:
        global o_ev
        info_long += "\n" + dumps(o_ev, indent=3)
    except:
        pass

    #write information to file
    with open (dir_path+"/info", 'w+') as f:
        f.write(info_long)

    # move the Coordinator log
    try:
        copy("files/logs/Coordinator.log", dir_path)
    except:
        pass

    #draw the result graphs
    from lib.draw_experiment import draw_exp
    try:
        draw_exp(dir_path+"/measurements.txt")
    except:
            traceback.print_exc(file=open(dir_path+"/errors", "w+"))

    log.info("EXPERIMENT DONE: Result measurements in: "+dir_path)


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
    global args
    try:
        experiment_file = args['file']
    except KeyError as e:
        log.error("run_experiments requires argument %s" % e.args[0])
        return

    #load the file with all the experiments
    exp_list = load(open(experiment_file))

    #run each one of the experiments
    for exp in exp_list:
        # overwrite the given env_vars
        from lib.persistance_module import env_vars
        global o_ev
        o_ev = exp['env_vars']
        env_vars.update(o_ev)

        # re-construct the args dict
        args = exp['workload']
        args['time'] = exp['time']
        args['name'] = exp['name']

        kill_workload()
        if (not ('clean' in exp)) or bool(exp['clean']):
            #clean-start the cluster by default or if clean is True
            kill_nodes()
            args["used"] = env_vars["min_cluster_size"]
            bootstrap_cluster()
            args["records"] = env_vars['records']
            load_data()

        #run the experiment
        try:
            experiment()
        except:
            traceback.print_exc(file=open(dir_path+"/errors", "w+"))



############################   MAIN  ################################################


function = parse_args()

try:
    #just call the appropriate function with eval!
    eval(function+"()")
except NameError:
    log.error("No such action")
    info()
