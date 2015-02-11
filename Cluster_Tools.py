__author__ = 'cmantas'
from lib.tiramola_logging import get_logger
from multiprocessing import Process
from lib.persistance_module import get_script_text, home



# the logger for this file
log = get_logger('CLUSTER', 'INFO', logfile=home+'files/logs/Coordinator.log')


def wait_proc(proc, node, timeout):
    """
    Waits for a process to finish running for a given timeout and throws an exception if not finished
    :param proc:
    :param node:
    :return:
    """
    proc.join(timeout)
    #check if it has not finished yet fail if so
    if proc.is_alive():
        log.error("Timeout occurred for process")
        proc.terminate()
        raise Exception("Script timed out for "+node.name)
    else:
        log.info(node.name+" DONE")


def run_script(script_content, nodes, serial=True, timeout=600):
    """
    Runs a script file to all the nodes in the cluster
    :param script_name:
    :param serial:
    :param timeout:
    :return:
    """
    log.info('Running a script to  %d nodes' % len(nodes))
    procs = []

    #start the procs that add the nodes
    for node in nodes:
        p = Process(target=node.run_command, args=(script_content,))
        procs.append(p)
        p.start()
        if serial:
            # if adding in serial, wait each proc
            log.info("waiting for node #"+node.name)
            wait_proc(p, node, timeout)

    if not serial:
        #wait for all the procs to finish in parallel
        log.debug("Waiting for all the procs to finish")
        for i in range(len(nodes)):
            wait_proc(procs[i], nodes[i], timeout)


def wait_everybody(nodes):
    """
    Waits for all the Nodes in the cluster to be SSH-able
    """
    log.info('Waiting for SSH on all nodes')
    for i in nodes:
        i.wait_ready()
