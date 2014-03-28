__author__ = 'cmantas'

from VM import VM, Timer
from VM import get_all_vms
from lib.persistance_module import env_vars, get_script_text


class CassandraNode:
    """
    Class that represents a node in a cassandra cluster. Can be of type 'SEED' or 'REGULAR' (default)
    """
    #static vars
    image = env_vars["cassandra_base_image"]

    def __init__(self, name=None, node_type="REGULAR", create=False, vm=None):
        """
        Creates a CassandraNode object.
        :param name:
        :param node_type: if "SEED" then will be treated as seednode
        :param create: if True then the actual VM will be created
        :param vm: if not None then this CassandraNode will be created from an existing vm
        """
        self.bootstraped = False
        self.name = name
        self.type = node_type
        self.vm = None
        if not vm is None:
            # init a node from a VM
            self.from_vm(vm)
        if create:
            self.create()

    def __str__(self):
        rv = "Cassandra Node || name: %s, type: %s" % (self.name, self.type)
        return rv

    def create(self):
        """
        creates the VM that this Cassandra Node will run on
        :return:
        """
        flavor = env_vars["cassandra_%s_flavor" % self.type]
        #create the VM
        self.vm = VM(self.name, flavor, self.image, create=True)

    def from_vm(self, vm):
        """
        Creates a CassandraNode from an existing VM
        :param vm:
        :return:
        """
        if not vm.created:
            print  "this VM is not created, so you cann't create a node from it"
        self.name = vm.name
        self.vm = vm
        if "seed" in vm.name:
            self.type = "SEED"
        elif "client" in vm.name:
            self.type = "CLIENT"
        else:
            self.type = "REGULAR"

    def bootstrap(self, params = None):
        """
        Bootstraps a node with the rest of the Casandra cluster
        """
        command = ""
        print "NODE: [%s] running bootstrap scripts" % self.name
        if self.type == "SEED":
            command += get_script_text("cassandra_seednode_bootstrap")
        elif self.type == "CLIENT":
            if self.name.endswith('1'):
                command += get_script_text("ganglia_endpoint")
            command += get_script_text("cassandra_client_bootstrap")

        else:
            command = get_script_text("cassandra_node_bootstrap")
        timer = Timer.get_timer()
        self.vm.run_command(command, silent=True)
        print "NODE: %s is now bootstrapped (took %d sec)" % (self.name, timer.stop())
        self.bootstraped = True

    def decommission(self):
        """
        Cecommissions a node from the Cassandra Cluster
        :return:
        """
        print "NODE: Decommissioning node: " + self.name
        keyspace = env_vars['keyspace']
        timer = Timer.get_timer()
        self.vm.run_command("nodetool repair -h %s %s" % (self.name, keyspace))
        self.vm.run_command("nodetool decommission")
        print "NODE: %s is decommissioned (took %d secs)" % (self.name, timer.stop())
        #self.vm.shutdown()


    def kill(self):
        command = get_script_text("cassandra_kill")
        self.vm.run_command(command, silent=True)

    def get_status(self):
        """
        Gets the status of the node as far as Cassandra is concerned (uses hooks inside of VM)
        :return:
        """
        if self.vm.get_cloud_status() != "ACTIVE":
            return "stopped"
        #wait for the vm to be ready and SSH-able
        self.vm.wait_ready()
        status = self.vm.run_command("ctool status", indent=0, prefix='')
        return status.strip()


    def inject_server_hosts(self, hosts):
        text = ""
        for h in hosts:
            text += h + "\n"
        print "injecting: \n"+text
        self.vm.run_command("echo '%s' > /opt/hosts")

    def __str__(self):
        str = "Node %s" % self.name
        return str


def get_all_nodes(check_active=False):
    vms = get_all_vms(check_active=check_active)
    nodes = []
    seeds = []
    clients = []
    for vm in vms:
        if not vm.name.startswith("cassandra"):
            continue
        else:
            node = CassandraNode(vm=vm)
            if node.type == 'SEED': seeds.append(node)
            elif node.type == "CLIENT": clients.append(node)
            else: nodes.append(node)
    return seeds, nodes, clients

