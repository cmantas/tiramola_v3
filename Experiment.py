__author__ = 'cmantas'
import sys, traceback
from lib.tiramola_logging import get_logger
from os import remove, mkdir
from shutil import move, copy
from time import strftime
from os.path import isdir
from random import random
from json import load, dumps
from lib.persistance_module import reload_env_vars
from time import sleep
import ClientsCluster, CassandraCluster

## global logger
log = get_logger("EXPERIMENT", 'INFO')

measurements_dir = "files/measurements"


def run_sinusoid(target, period, offset):
        import ClientsCluster, CassandraCluster
        svr_hosts = CassandraCluster.get_hosts(private=False)
        args = dict()
        args["target"] = target
        args["period"] = period
        args['type'] = 'sinusoid'
        args['servers'] = svr_hosts
        args['offset'] =offset
        ClientsCluster.run(args)


def run_stress():
    log.info("running stress workload" )
    svr_hosts = CassandraCluster.get_hosts(private=True)
    params = {'type':'stress', 'servers': svr_hosts}
    ClientsCluster.run(params)


def experiment(name, target, period, offset, minutes):

    #delete any previous measurements
    try:
        remove("%s/measurements.txt" % measurements_dir)
    except:
        pass

    run_sinusoid(target, period, offset)

    #empty the contents of the coordinator.log
    try:
        open('files/logs/Coordinator.log', 'w+').close()
    except:
        pass

    # create a directory for the experiment results
    dir_path = measurements_dir+"/"+name
    if isdir(dir_path):
        dir_path += "_"+str(int(random()*1000))
    try:
        mkdir(dir_path)
    except:
        log.error("Could not create experiment directory")
        exit(-1)


    # actually run the tiramola automatic provisioning algorithm
    try:
        log.info("Running the Coordinator")
        secs = 60 * minutes
        import Coordinator
        Coordinator.run(secs)
        pass
    except:
        print traceback.format_exc()
        traceback.print_exc(file=open(dir_path+"/errors", "w+"))

    #kill the workload
    log.info(" killing workload")
    ClientsCluster.kill_nodes()

    #move the measurements file
    move("files/measurements/measurements.txt", dir_path)

    info_long = "target = %d\noffset = %d\nperiod = %dmin\nduration = %dmin\ndate = %s" %\
           (target, offset, period/60, minutes, strftime('%b%d-%H:%M'))
    global env_vars
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


def run_experiments(experiment_file):

    #load the file with all the experiments
    try:
        exp_list = load(open(experiment_file))
    except:
        log.error("Malformed JSON experiments file")

    #run each one of the experiments
    for exp in exp_list:
        # overwrite the given env_vars
        from lib.persistance_module import env_vars
        reload_env_vars()
        global o_ev, env_vars
        o_ev = exp['env_vars']

        env_vars.update(o_ev)

        if 'simulation' in exp and exp['simulation']:
            simulate()
        else:
            target = int(exp['workload']["target"])
            period = 60*int(exp['workload']["period"])
            offset = int(exp['workload']["offset"])
            minutes = int(exp['time'])
            name = exp['name']

            if (not ('clean' in exp)) or bool(exp['clean']):
                #clean-start the cluster by default or if clean is True
                CassandraCluster.kill_nodes()
                used = env_vars["min_cluster_size"]
                CassandraCluster.bootstrap_cluster(used)
                #load_data
                svr_hosts = CassandraCluster.get_hosts(private=True)
                args = {'type': 'load', 'servers': svr_hosts, 'records': env_vars['records']}
                ClientsCluster.run(args)

            #run the experiment
            experiment(name, target, period, offset, minutes)




if __name__ == '__main__':
    print 'testing experiments creation'
    run_experiments("test.json")