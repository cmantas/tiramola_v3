__author__ = 'cmantas'

from VM import VM, Timer
from VM import get_all_vms
from lib.persistance_module import env_vars, get_script_text


class Node (VM):
    """
    Class that represents a node a cluster. extends VM
    """

    ### you should specify the image
    flavor = env_vars["default_flavor"]
    image = env_vars["default_image"]

    def __init__(self, cluster_name='', node_type='', number=0, create=False, IPv4=False, wait=False, vm=None):
        """
        Creates a Node object.
        :param cluster_name:
        :param node_type: the type of the node
        :param create: if True then the actual VM will be created
        :param vm: used to create a Node from a pre-existing VM
        """
        self.bootstraped = False
        self.name = cluster_name + "_" + node_type + "_" + str(number)
        self.type = node_type
        self.number = number
        if not vm is None:
            # init a node from a VM
            self.from_vm(vm)
        else:
            super(Node, self).__init__(self.name, self.flavor, self.image, IPv4=IPv4, create=create, wait=wait)

    def __str__(self):
        rv = "Node || name: %s, type: %s" % (self.name, self.type)
        return rv

    def from_vm(self, vm):
        """
        Creates a Node from a pre-existing VM
        :param vm:
        :return:
        """
        if not vm.created:
            print "this VM is not created, so you cann't create a node from it"
        self.name = vm.name
        super(Node, self).__init__(self.name, self.flavor, self.image, IPv4=vm.IPv4)
        self.id = vm.id
        self.created = True
        self.type = self.name[self.name.find("_")+1:][:self.name[self.name.find("_")+1:].find("_")]
        self.addresses = vm.addresses

    def bootstrap(self, params=None):
        """
        Runs the required bootstrap scripts on the node
        """
        command = ""
        print "NODE: [%s] running bootstrap script" % self.name
        command += get_script_text(self.type, "bootstrap")
        timer = Timer.get_timer()
        rv = self.run_command(command, silent=True)
        print "NODE: %s is now bootstrapped (took %d sec)" % (self.name, timer.stop())
        self.bootstraped = True

    def decommission(self):
        """
        Cecommissions a node from the Cluster
        :return:
        """
        print "NODE: [%s] running decommission script" % self.name
        command = get_script_text(self.type, "decommission")
        timer = Timer.get_timer()
        self.run_command(command, silent=True)
        action = env_vars["decommission_action"]
        if action == "KEEP": pass
        elif action == "SHUTDOWN": self.shutdown()
        elif action == "DESTROY": self.destroy()
        print "NODE: %s is now decommissioned (took %d sec)" % (self.name, timer.stop())

    def kill(self):
        """
        Runs the required scripts to kill the application being run in the cluster
        """
        print "NODE: [%s] running kill script" % self.name
        command = get_script_text(self.type, "kill")
        self.run_command(command, silent=True)

    def inject_hostnames(self, hostnames):
        """
        Recreates the /etc/hosts file in the node so that it inlcludes the given hostnames and ips
        :param hostnames: a mapping of hostnames-->IPs
        """
        #add some default hostnames
        hostnames["localhost"] = "127.0.0.1"
        hostnames["ip6-localhost ip6-loopback"] = "::1"
        hostnames["ip6-localnet"] = "fe00::0"
        hostnames["ip6-mcastprefix"] = "ff00::0"
        hostnames["ip6-allnodes"] = "ff02::1"
        hostnames["ip6-allrouters"] = "ff02::2"
        text = ""
        for host in hostnames.keys():
            text += "\n%s %s" % (hostnames[host], host)
        self.run_command("echo '## AUTO GENERATED #### \n%s' > /etc/hosts; echo %s >/etc/hostname" %
                         (text, self.name), silent=True)

    def get_status(self):
        """
        Gets the status of the node, combining IaaS status and hooks inside the VM
        TODO: specify status script and run to get status
        :return the status
        """
        if self.get_cloud_status() != "ACTIVE":
            return "stopped"
        #wait for the vm to be ready and SSH-able
        self.wait_ready()
        status = self.run_command("ctool status", indent=0, prefix='')
        return status.strip()


    @staticmethod
    def get_all_nodes(cluster_name="", check_active=False):
        """
        Returns a Node instance for each one of the VMs running in the cluster
        :param cluster_name: only return Nodes of the specified cluster (whose name starts with 'cluster_name')
        :param check_active: if true only return VMs whose IaaS status is 'ACTIVE'
        :return:
        """
        vms = get_all_vms(check_active=check_active)
        nodes = []
        for vm in vms:
            if (cluster_name != "") and (not vm.name.startswith(cluster_name)):
                continue
            else:
                node = Node(vm=vm)
                nodes.append(node)
        return nodes

