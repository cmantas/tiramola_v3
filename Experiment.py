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


## global logger
log = get_logger("EXPERIMENT", 'INFO')


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
    import ClientsCluster, CassandraCluster
    svr_hosts = CassandraCluster.get_hosts(private=True)
    params = {'type':'stress', 'servers': svr_hosts}
    ClientsCluster.run(params)


def kill_workload():
    log.info("killing workload")
    import ClientsCluster
    ClientsCluster.kill_nodes()


def auto_pilot(minutes):
    log.info("Running Tiramola Auto Provisioning super algorithm")
    secs = 60 * minutes
    import Coordinator
    Coordinator.run(secs)

def monitor(minutes):
    log.info("simply monitoring")
    global  env_vars
    env_vars["gain"] = '0'


def experiment():
    try:
        experiment_name = args['name']
        log.info("=======> EXPERIMENT: %s  <======" % experiment_name)
    except KeyError as e:
        log.error("experiment requires argument %s" % e.args[0])
        return

    log.info("Running a full experiment")

    #delete any previous measurements
    try:
        global dir_path
        remove("files/measurements/measurements.txt", dir_path)
    except:
        pass

    run_sinusoid()

    #empty the contents of the coordinator.log
    try:
        open('files/logs/Coordinator.log', 'w+').close()
        #f = open('file.txt', 'r+')
        #f.truncate()
    except:
        pass


    # create a directory for the experiment results
    dir_path = "files/measurements/"+experiment_name
    if isdir(dir_path):
        dir_path += "_"+str(int(random()*1000))
    try:
        mkdir(dir_path)
    except:
        log.error("Could not create experiment directory")

    # run the tiramola automatic provisioning algorithm
    try:
        auto_pilot()
    except:
        traceback.print_exc(file=open(dir_path+"/errors", "w+"))

    #kill the workload
    kill_workload()

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
        reload_env_vars()
        global o_ev, env_vars
        o_ev = exp['env_vars']

        env_vars.update(o_ev)
        #env_vars['gain']=o_ev['gain']

        if 'simulation' in exp and exp['simulation']:
            simulate()
        else:
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
                sleep(30)
                args["records"] = env_vars['records']
                load_data()
                sleep(2*60)


            #run the experiment
            try:
                experiment()
            except:
                traceback.print_exc(file=open(dir_path+"/errors", "w+"))