__author__ = 'cmantas'
from Node import Node
from VM import get_all_vms
from json import loads, dumps
from os import remove
from os.path import isfile
from lib.persistance_module import get_script_text, env_vars
from lib.tiramola_logging import get_logger

orchestrator = None     # the VM to which the others report to

seeds = []              # the seed node(s) of the casssandra cluster !!! ONLY ONE IS SUPPORTED !!!
nodes = []              # the rest of the nodes of the Cassandra cluster
stash = []              # list of the Nodes that are available (active) but not used

# the name of the cluster is used as a prefix for the VM names
cluster_name = env_vars['active_cluster_name']

# the save file for saving/reloading the active cluster
save_file = "files/saved_%s_cluster.json" % cluster_name

# the flavor and image for the VMs used int the cluster
Node.flavor = env_vars["default_flavor"]
Node.image = env_vars["cassandra_base_image"]

log = get_logger('CLUSTER', 'DEBUG', logfile='files/logs/Coordinator.log')


def create_cluster(worker_count=0):
    """
    Creates a Cassandra Cluster with a single Seed Node and 'worker_count' other nodes
    :param worker_count: the number of the nodes to create-apart from the seednode
    """
    #create the seed node
    seeds.append(Node(cluster_name, node_type="seed", number=0, create=True, IPv4=True))
    #create the rest of the nodes
    for i in range(worker_count):
        nodes.append(Node(cluster_name, node_type="node", number="%02d"%(len(nodes)+1), create=True))
    #wait until everybody is ready
    save_cluster()
    wait_everybody()
    find_orchestrator()
    inject_hosts_files()
    log.info('Every node is ready for SSH')


def wait_everybody():
    """
    Waits for all the Nodes in the cluster to be SSH-able
    """
    log.info('Waiting for SSH on all nodes')
    for i in seeds + nodes:
        i.wait_ready()


def bootstrap_cluster():
    """
    Runs the necessary boostrap commnands to each of the Seed Node and the other nodes
    """
    inject_hosts_files()
    log.info("Running bootstrap scripts")
    #bootstrap the seed node
    seeds[0].bootstrap()
    #bootstrap the rest of the nodes
    for n in nodes:
        n.bootstrap(params={"seednode": seeds[0].get_private_addr()})
    log.info("READY!!")


def find_orchestrator():
    in_nodes = Node.get_all_nodes(check_active=True)
    for n in in_nodes:
        if "orchestrator" in n.name:
            global orchestrator
            orchestrator = n
            return


def resume_cluster():
    """
    Re-loads the cluster representation based on the VMs pre-existing on the IaaS and the 'save_file'
    """
    if not isfile(save_file):
        log.info("No existing created cluster")
        return
    saved_cluster = loads(open(save_file, 'r').read())
    saved_nodes = saved_cluster['nodes']
    saved_seeds = saved_cluster['seeds']
    saved_stash = saved_cluster['stash']
    nodes[:] = []
    seeds[:] = []

    in_nodes = Node.get_all_nodes(check_active=True)
    #check that all saved nodes actually exist and exit if not remove
    to_remove = []
    for n in saved_nodes:
        if n not in [i.name for i in in_nodes]:
            log.error("node %s does actually exist in the cloud, re-create the cluster" % n)
            remove(save_file)
            exit(-1)
    for n in in_nodes:
        if n.name not in saved_nodes+saved_seeds:
            if n.name in saved_stash:
                stash.append(n)
            if "orchestrator" in n.name:
                global orchestrator
                orchestrator = n
            continue
        else:
            if n.type == "seed": seeds.append(n)
            elif n.type == "node": nodes.append(n)
    #sort nodes by name
    nodes.sort(key=lambda x: x.name)
    stash.sort(key=lambda x: x.name)


def save_cluster():
    """
    Creates/Saves the 'save_file'
    :return:
    """
    cluster = dict()
    cluster["seeds"] = [s.name for s in seeds]
    cluster["nodes"] = [n.name for n in nodes]
    cluster["stash"] = [c.name for c in stash]
    string = dumps(cluster, indent=3)
    f = open(save_file, 'w+')
    f.write(string)


def kill_nodes():
    """
    Runs the kill scripts for all the nodes in the cluster
    """
    log.info("Killing cassandra nodes")
    for n in seeds+nodes+stash:
        n.kill()


def inject_hosts_files():
    """
    Creates a mapping of hostname -> IP for all the nodes in the cluster and injects it to all Nodes so that they
    know each other by hostname. Also restarts the ganglia daemons
    :return:
    """
    # FIXME remove Clients entries. Servers should only know themselves
    log.info("Injecting host files")
    hosts = dict()
    for i in seeds+nodes :
        hosts[i.name] = i.get_private_addr()
    #manually add  the entry for the seednode
    hosts["cassandra_seednode"] = seeds[0].get_private_addr()
    #add the host names to etc/hosts
    orchestrator.inject_hostnames(hosts, delete=cluster_name)
    for i in seeds+nodes:
        i.inject_hostnames(hosts, delete=cluster_name)
    seeds[0].run_command("service ganglia-monitor restart; service gmetad restart", silent=True)
    orchestrator.run_command("service ganglia-monitor restart; service gmetad restart", silent=True)


def add_nodes(count=1):
    """
    Adds a node to the cassandra cluster. Refreshes the hosts in all nodes
    :return:
    """
    log.info('Adding %d nodes' % count )
    new_nodes = []
    for i in range(count):
        if not len(stash) == 0:
            new_guy = stash.pop(0)
            log.info("Using %s from my stash" % new_guy.name)
        else:
            new_guy = Node(cluster_name, 'node', str(len(nodes)+1), create=True)
        nodes.append(new_guy)
        new_nodes.append(new_guy)
        save_cluster()
    for n in new_nodes:
        n.wait_ready()
        #inject host files to everybody
        n.inject_hostnames(get_hosts(private=True), delete=cluster_name)
        n.bootstrap()
        log.info("Node %s is live " % n.name)
    #inform all
    inject_hosts_files()


def remove_nodes(count=1):
    """
    Removes a node from the cassandra cluster. Refreshes the hosts in all nodes
    :return:
    """
    action = env_vars['cassandra_decommission_action']
    for i in range(count):
        dead_guy = nodes.pop()
        log.info("Removing node %s" % dead_guy.name)
        dead_guy.decommission()
        if action == "KEEP":
            stash[:] = [dead_guy] + stash
        log.info("Node %s is removed" % dead_guy.name)
        save_cluster()
    inject_hosts_files()


def destroy_all():
    """
    Destroys all the VMs in the cluster (not the orchestrator)
    """
    log.info("Destroying the %s cluster" % cluster_name)
    for n in seeds+nodes+stash:
        n.destroy()
    remove(save_file)


def get_hosts(string=False, private=False):
    """
    Produces a mapping of hostname-->IP for the nodes in the cluster
    :param string: if True the output is a string able to be appended in /etc/hosts
    :return: a dict or a string of hostnames-->IPs
    """
    hosts = dict()
    all_nodes = seeds + nodes
    for i in all_nodes:
        if private:
            hosts[i.name] = i.get_private_addr()
        else:
            hosts[i.name] = i.get_public_addr()
    if private:
        hosts['cassandra_seednode'] = seeds[0].get_private_addr()
    else:
        hosts['cassandra_seednode'] = seeds[0].get_public_addr()
    return hosts


def node_count():
    return len(seeds+nodes)


def exists():
    if len(seeds+nodes) == 0:
        return False
    else:
        return True


def get_monitoring_endpoint():
    """
    returns the IP of the node that has the monitoring data we want
    """
    seeds[0].get_public_addr()


#=============================== MAIN ==========================


################ INIT actions ###########
resume_cluster()
########################################



