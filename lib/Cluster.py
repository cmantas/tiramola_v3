__author__ = 'cmantas'
from lib.tiramola_logging import get_logger
from multiprocessing import Process
from lib.persistance_module import get_script_text, home, env_vars


class Cluster(object):
    # the logger for this file
    log = get_logger('CLUSTER', 'DEBUG', logfile=home+'files/logs/Coordinator.log')

    def __init__(self):
        self.all_nodes = []
        self.log = Cluster.log

        # the name of the cluster is used as a prefix for the VM names
        self.cluster_name = "cluster"
        pass


    @staticmethod
    def wait_proc(proc, node, timeout, log=None):
        """
        Waits for a process to finish running for a given timeout and throws an exception if not finished
        :param proc:
        :param node:
        :return:
        """
        proc.join(timeout)
        #check if it has not finished yet fail if so
        if proc.is_alive():
            if not log is None:
                log.error("Timeout occurred for process")
            proc.terminate()
            raise Exception("Script timed out for "+node.name)
        elif not log is None: log.debug(node.name+" DONE")

    @staticmethod
    def run_script(script_content, nodes, serial=True, timeout=600, log=None):
        """
        Runs a script to the specified VMs
        :param script_content:
        :param serial:
        :param timeout:
        :return: None
        """
        if not log is None:
            log.info('Running a script to  %d nodes' % len(nodes))
        procs = []

        #start the procs that add the nodes
        for node in nodes:
            p = Process(target=node.run_command, args=(script_content,))
            procs.append(p)
            p.start()
            if serial:
                # if adding in serial, wait each proc
                if not log is None:log.debug("waiting for node #"+node.name)
                Cluster.wait_proc(p, node, timeout)

        if not serial:
            #wait for all the procs to finish in parallel
            if not log is None:log.debug("Waiting for all the procs to finish")
            for i in range(len(nodes)):
                Cluster.wait_proc(procs[i], nodes[i], timeout)
            if not log is None: log.info("Finished running script")

    def run_to_all(self, script_content, serial=True, timeout=600):
        """
        Runs a script to all the nodes in the cluster
        :param script_content:
        :param serial:
        :param timeout:
        """
        self.run_script(script_content, self.all_nodes, serial, timeout, self.log)


    def wait_everybody(self):
        """
        Waits for all the Nodes in the cluster to be SSH-able
        """
        self.log.info('Waiting for SSH on all nodes')
        for i in self.all_nodes:
            i.wait_ready()


    def bootstrap_cluster(self):
        """
        Runs the necessary boostrap commnands to each of the Seed Node and the other nodes
        """
        for n in self.all_nodes:
            n.bootstrap()
        self.inject_hosts_files()


    def kill_nodes(self):
        """
        Runs the kill scripts for all the nodes in the cluster
        """
        self.log.info("Killing nodes")
        for n in self.all_nodes:
            n.kill()


    def update_hostfiles(self, servers):
        if not env_vars["update_hostfiles"]:
            self.log.info("Not updtading ycsb client host files")
            return
        self.log.info("updating hostfiles")
        # generate ycsb-specific hosts file text
        host_text = ""

        if "cassandra_seednode" in servers.keys(): del servers["cassandra_seednode"]

        #generate the "hosts" text for YCSB
        for key, value in servers.iteritems(): host_text += value+"\n"
        host_text = host_text[:-1]  # remove trailing EOL

        #DEBUG keep just one host
        #host_text = servers["cassandra_node_01"]

        command = "echo '%s' > /opt/hosts;" % host_text
        self.run_script(command, self.all_nodes, serial=False)


    def get_hosts(self, string=False, private=False):
        """
        Produces a mapping of hostname-->IP for the nodes in the cluster
        :param include_clients: if False (default) the clients are not included
        :param string: if True the output is a string able to be appended in /etc/hosts
        :return: a dict or a string of hostnames-->IPs
        """
        hosts = dict()
        for i in self.all_nodes:
            if private:
                hosts[i.name] = i.get_private_addr()
            else:
                hosts[i.name] = i.get_public_addr()
        return hosts


    def node_count(self):
        return len(self.all_nodes)


    def exists(self):
        if len(self.all_nodes) == 0:
            return False
        else:
            return True


    def get_monitoring_endpoint(self):
        """
        returns the IP of the node that has the monitoring data we want
        """
        return self.all_nodes[0].get_public_addr()