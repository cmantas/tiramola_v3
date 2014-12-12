__author__ = 'cmantas'
import traceback
from lib.tiramola_logging import get_logger
from os import remove, mkdir, listdir
from shutil import move, copy
from time import strftime
from os.path import isdir, isfile, join, exists
from random import random
from json import load, dumps, loads
from lib.persistance_module import env_vars, reload_env_vars
from time import sleep
import ClientsCluster, CassandraCluster

## global logger
log = get_logger("EXPERIMENT", 'INFO')
o_ev = {}
measurements_dir = "files/measurements"


def list_files(dir_path):
    """
    lists all files (not dirs) in a given directory
    :param dir_path:
    :return:
    """
    return [f for f in listdir(dir_path) if isfile(join(dir_path, f))]


def wait_get_one(dir_path):
    """
    returns the content
    :param dir_path:
    :return:
    """
    files = list_files(dir_path)
    print_once = True
    while len(files)==0:
        if print_once:
            print "Waiting for files..."
            print_once = False
        sleep(1)
        files = list_files(dir_path)
    fname = dir_path + "/" + files.pop()
    return fname


def watch(dir_path, callback):
    """
    watches a directory and when there are files available in it, it loads their contents to memory, moves them
    and then calls the callback function giving the file contents as an argument
    :param dir_path:
    :param callback:
    :return:
    """
    while True:
        fname = wait_get_one(dir_path)
        f = open(fname, 'r')
        contents = f.read()
        f.close
        done_dir = dir_path+"/done"
        if not exists(done_dir):
            mkdir(done_dir)
        move(fname, done_dir)
        callback(contents)


def run_sinusoid(target, period, offset):
        import ClientsCluster, CassandraCluster
        svr_hosts = CassandraCluster.get_hosts(private=False)
        args = dict()
        args["target"] = target
        args["period"] = period
        args['type'] = 'sinusoid'
        args['servers'] = svr_hosts
        args['offset'] = offset
        ClientsCluster.run(args)


def run_stress():
    log.info("running stress workload")
    svr_hosts = CassandraCluster.get_hosts(private=True)
    params = {'type': 'stress', 'servers': svr_hosts}
    ClientsCluster.run(params)


def experiment(name, target, period, offset, minutes):
    """
    runs a full experiment and outputs the the results to directory inside the measurements dir
    :param name:
    :param target:
    :param period:
    :param offset:
    :param minutes:
    :return:
    """
    #delete any previous measurements
    try:
        remove("%s/measurements.txt" % measurements_dir)
    except:
        pass
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
    success = False
    try:
        run_sinusoid(target, period, offset)

        # actually run the tiramola automatic provisioning algorithm
        try:
            log.info("Running the Coordinator")
            secs = 60 * minutes
            import Coordinator
            Coordinator.run(secs)
            success = True
        except:
            print traceback.format_exc()
            traceback.print_exc(file=open(dir_path+"/errors", "w+"))

        # kill the workload
        log.info(" killing workload")
        ClientsCluster.kill_nodes()

        # move the measurements file
        move("files/measurements/measurements.txt", dir_path)
        # move the predictions file
        move("files/measurements/predictions.txt", dir_path)

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
    except:
        traceback.print_exc(file=open(dir_path+"/errors", "w+"))
    return success


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


def clean_start():
    success = False
    while not success:
        try:
            #clean-start the cluster by default or if clean is True
            CassandraCluster.kill_nodes()
            used = env_vars["min_cluster_size"]
            CassandraCluster.bootstrap_cluster(used)
            #load_data
            svr_hosts = CassandraCluster.get_hosts()
            args = {'type': 'load', 'servers': svr_hosts, 'records': env_vars['records']}
            ClientsCluster.run(args)
            success = True
        except:
            log.error("Failed to clean, restarting")
            sleep(120)


def run_experiments(experiment_file):
    """
    loads the experiments from a file to a list and runs them in batch
    :param experiment_file:
    :return:
    """
        #load the file with all the experiments
    exp_list = load(open(experiment_file))
    run_batch_experiments(exp_list)


def run_experiments_from_string(string_exp):
    exp_list = loads(string_exp)
    run_batch_experiments(exp_list)


def run_batch_experiments(exp_list):
    """
    runs a batch of experiments as specified to the experiment file
    :param experiment_file:
    :return:
    """
    #run each one of the experiments

    log.info("running batch experiments")

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

            #run the experiment
            tries = 5
            success = False
            while not success and tries > 0:
                if (not ('clean' in exp)) or bool(exp['clean']):
                    clean_start()
                else:
                    #make sure the cluster is at its min size
                    CassandraCluster.set_cluster_size(env_vars["min_cluster_size"])
                success =  experiment(name, target, period, offset, minutes)
                if not success:
                    log.info("Experiment failed, sleeping 10mins and Retrying")
                    sleep(600)
                    tries -=1


if __name__ == '__main__':
    print 'testing experiments creation'
    run_experiments("test.json")