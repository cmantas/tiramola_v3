__author__ = 'cmantas'
_author__ = 'cmantas'
from Node import Node
from VM import get_all_vms
from json import loads, dumps
from os import remove
from os.path import isfile
from lib.persistance_module import get_script_text, env_vars
from lib.tiramola_logging import get_logger
from threading import Thread
from lib.Cluster import *


class Clients(Cluster):
    """
    Represents the Clients Cluster
    """
    orchestrator = None     # the VM to which the others report to
    # the flavor and image for this cluster's VMs
    flavor = env_vars["client_flavor"]
    image = env_vars["cassandra_base_image"]

    def __init__(self):
        super(Clients, self).__init__()
        self.cluster_name = "clients"
        self.node_type = "client"
        # the save file for saving/reloading the active cluster
        self.save_file = home+"files/saved_%s_cluster.json" % self.cluster_name
        # the logger for this file
        self.log = get_logger('CLIENTS', 'INFO', logfile=home+'files/logs/Coordinator.log')




    def find_orchestrator(self):
        in_nodes = Node.get_all_nodes(check_active=True)
        for n in in_nodes:
            if "orchestrator" in n.name:
                global orchestrator
                orchestrator = n
                return


    def resume_cluster(self):
        """
        Re-loads the cluster representation based on the VMs pre-existing on the IaaS and the 'save_file'
        """
        self.log.info("Loading info from the IaaS")
        if not isfile(self.save_file):
            self.log.info("No existing created cluster")
            saved_nodes = []
        else:
            saved_cluster = loads(open(self.save_file, 'r').read())
            saved_nodes = saved_cluster['clients']

        in_nodes = Node.get_all_nodes(check_active=True)
        for n in in_nodes:
            if n.name not in saved_nodes:
                if "orchestrator" in n.name:
                    global orchestrator
                    orchestrator = n
                    self.log.debug('Found orchestrator %s' % n.name)
                continue
            else:
                self.all_nodes.append(n)
        #sort nodes by name
        self.all_nodes.sort(key=lambda x: x.name)

    def save_cluster(self):
        """
        Creates/Saves the 'save_file'
        :return:
        """
        cluster = dict()
        cluster["clients"] = [c.name for c in self.all_nodes]
        string = dumps(cluster, indent=3)
        f = open(self.save_file, 'w+')
        f.write(string)

    def create_cluster(self, count=1):
        self.all_nodes = []
        for i in range(count):
            self.all_nodes.append(Node(self.cluster_name, node_type=self.node_type, number="%02d" % (i+1), create=True, IPv4=True,
                                flavor=self.flavor, image=self.image))

        #save the cluster to file
        self.save_cluster()
        #wait until everybody is ready
        self.wait_everybody()
        self.find_orchestrator()
        self.inject_hosts_files()
        self.log.info('Every node is ready for SSH')


    def inject_hosts_files(self):
        """
        Creates a mapping of hostname -> IP for all the nodes in the cluster and injects it to all Nodes so that they
        know each other by hostname. Also restarts the ganglia daemons
        :return:
        """
        self.log.info("Injecting host files")
        hosts = dict()
        for i in self.all_nodes:
            hosts[i.name] = i.get_public_addr()
        #add the host names to etc/hosts
        orchestrator.inject_hostnames(hosts, delete=self.cluster_name)
        for i in self.all_nodes:
            i.inject_hostnames(hosts, delete=self.cluster_name)
        self.all_nodes[0].run_command("service ganglia-monitor restart; service gmetad restart", silent=True)
        orchestrator.run_command("service ganglia-monitor restart; service gmetad restart", silent=True)




    def add_nodes(self, count=1):
        """
        Adds a node to the cassandra cluster. Refreshes the hosts in all nodes
        :return:
        """
        self.log.info('Adding %d nodes' % count)
        new_nodes = []
        Node.flavor = env_vars['client_flavor']
        for i in range(count):
            #check if cluster did not previously exist
            if i == 0 and len(self.all_nodes) == 0:
                # give a floating IPv4 to the first node only
                new_guy = Node(self.cluster_name, '', len(self.all_nodes)+1, create=True,  IPv4=True)
            else:
                new_guy = Node(self.cluster_name, node_type="", number=len(self.all_nodes)+1, create=True)
            self.all_nodes.append(new_guy)
            new_nodes.append(new_guy)
            self.save_cluster()
        for n in new_nodes:
            n.wait_ready()
            #inject host files to everybody
            n.inject_hostnames(self.get_hosts(private=True), delete=self.cluster_name)
            n.bootstrap()
            self.log.info("Node %s is live " % new_guy.name)
        #inform all
        self.inject_hosts_files()

    def remove_nodes(self, count=1):
        """
        Removes a node from the cassandra cluster. Refreshes the hosts in all nodes
        :return:
        """
        for i in range(count):
            dead_guy = self.all_nodes.pop()
            self.log.info("Removing node %s" % dead_guy.name)
            dead_guy.decommission()
            self.log.info("Client %s is removed" % dead_guy.name)
            self.save_cluster()
        self.inject_hosts_files()


    def run(self, params):

        self.bootstrap_cluster()

        run_type = params['type']

        servers = params['servers']
        self.update_hostfiles(servers)

        #choose type of run and do necessary actions
        if run_type=='stress':
            for c in self.all_nodes:
                load_command = get_script_text(self.cluster_name, self.node_type, "run")
                self.log.info("running stress workload on %s" % c.name)
                c.run_command(load_command, silent=True)
        elif run_type == 'sinusoid':
            global env_vars
            target = int(params['target']) / len(self.all_nodes)
            offset = int(params['offset']) / len(self.all_nodes)
            period = int(params['period'])
            threads = int(env_vars['client_threads'])
            for c in self.all_nodes:
                load_command = get_script_text(self.cluster_name, self.node_type, "run_sin") % (target, offset, period, threads)
                #load_command += get_script_text(cluster_name, "", "run_sin") % (target, offset, period)
                self.log.info("running sinusoid on %s" % c.name)
                c.run_command(load_command, silent=True)
        elif run_type == 'load':
            record_count = int(params['records'])
            start = 0
            step = record_count/len(self.all_nodes)
            threads = []
            for c in self.all_nodes:
                #load_command = get_script_text(self.cluster_name, self.node_type, "load") % (str(record_count), str(step), str(start))
                load_command = get_script_text(self.cluster_name, self.node_type, "load").format(record_count, step, start)
                #load_command += get_script_text(cluster_name, "", "load") % (str(record_count), str(step), str(start))
                self.log.info("running load phase on %s for %d records" % (c.name, record_count))
                t = Thread(target=c.run_command, args=(load_command,) )
                threads.append(t)
                t.start()
                start += step
            self.log.info("waiting for load phase to finish in clients")
            for t in threads:
                t.join()
            self.log.info("load finished")


    def destroy_all(self):
        """
        Destroys all the VMs in the cluster (not the orchestrator)
        """
        self.log.info("Destroying the %s cluster" % self.cluster_name)
        for n in self.all_nodes:
            n.destroy()
        remove(self.save_file)






my_Clients = Clients()
# always runs
my_Clients.resume_cluster()
