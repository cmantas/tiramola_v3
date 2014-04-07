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
clients = []            # the clients of the cluster
stash = []              # list of the Nodes that are available (active) but not used

# the name of the cluster is used as a prefix for the VM names
cluster_name = env_vars['active_cluster_name']

# the save file for saving/reloading the active cluster
save_file = "files/saved_%s_cluster.json" % cluster_name

# the flavor and image for the VMs used int the cluster
Node.flavor = env_vars["default_flavor"]
Node.image = env_vars["cassandra_base_image"]

log = get_logger('CLUSTER\t\t\t', 'INFO')


def create_cluster(worker_count=0, client_count=0):
    """
    Creates a Cassandra Cluster with a single Seed Node and 'worker_count' other nodes
    :param worker_count: the number of the nodes to create-apart from the seednode
    """
    #create the seed node
    seeds.append(Node(cluster_name, node_type="seed", number=0, create=True, IPv4=True))
    #create the rest of the nodes
    for i in range(worker_count):
        nodes.append(Node(cluster_name, node_type="node", number=len(nodes)+1, create=True))
    for i in range(client_count):
        if i == 0:
            # give a floating IPv4 to the first client only
            clients.append(Node(cluster_name, node_type="client", number=len(clients)+1, create=True,  IPv4=True))
        else:
            clients.append(Node(cluster_name, node_type="client", number=len(clients)+1, create=True))
    #wait until everybody is ready
    save_cluster()
    wait_everybody()
    inject_hosts_files()
    log.info('Every node is ready for SSH')


def wait_everybody():
    """
    Waits for all the Nodes in the cluster to be SSH-able
    """
    log.info('Waiting for SSH on all nodes')
    for i in seeds + nodes + clients:
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
    for n in nodes+clients:
        n.bootstrap(params={"seednode": seeds[0].get_private_addr()})
    log.info("READY!!")


def resume_cluster():
    """
    Re-loads the cluster representation based on the VMs pre-existing on the IaaS and the 'save_file'
    """
    if not isfile(save_file):
        log.info("No existing created cluster")
        return
    saved_cluster = loads(open(save_file, 'r').read())
    saved_nodes = saved_cluster['nodes']
    saved_clients = saved_cluster['clients']
    saved_seeds = saved_cluster['seeds']
    saved_stash = saved_cluster['stash']
    nodes[:] = []
    seeds[:] = []

    in_nodes = Node.get_all_nodes(cluster_name=cluster_name, check_active=True)
    #check that all saved nodes actually exist and exit if not remove
    to_remove = []
    for n in saved_nodes:
        if n not in [i.name for i in in_nodes]:
            log.error("node %s does actually exist in the cloud, re-create the cluster" % n)
            remove(save_file)
            exit(-1)
    for n in in_nodes:
        if n.name not in saved_nodes+saved_seeds+saved_clients:
            if n.name in saved_stash:
                stash.append(n)
            continue
        else:
            if n.type == "seed": seeds.append(n)
            elif n.type == "node": nodes.append(n)
            elif n.type == "client": clients.append(n)
    #sort nodes by name
    nodes.sort(key=lambda x: x.name)
    clients.sort(key=lambda x: x.name)


def save_cluster():
    """
    Creates/Saves the 'save_file'
    :return:
    """
    cluster = dict()
    cluster["seeds"] = [s.name for s in seeds]
    cluster["nodes"] = [n.name for n in nodes]
    cluster["clients"] = [c.name for c in clients]
    cluster["stash"] = [c.name for c in stash]
    string = dumps(cluster, indent=3)
    f = open(save_file, 'w+')
    f.write(string)


def kill_clients():
    """
    Runs the kill scripts for all the clients
    """
    log.error(" Killing clients")
    for c in clients: c.kill()


def kill_nodes():
    """
    Runs the kill scripts for all the nodes in the cluster
    """
    log.info("Killing cassandra nodes")
    for n in seeds+nodes+stash:
        n.kill()


def kill_all():
    """
    Kill 'em all
    """
    kill_clients()
    kill_nodes()


def inject_hosts_files():
    """
    Creates a mapping of hostname -> IP for all the nodes in the cluster and injects it to all Nodes so that they
    know each other by hostname. Also restarts the ganglia daemons
    :return:
    """
    log.info("Injecting host files")
    hosts = dict()
    for i in seeds+nodes + clients:
        hosts[i.name] = i.get_private_addr()
    #manually add  the entry for the seednode
    hosts["cassandra_seednode"] = seeds[0].get_private_addr()
    #add the host names to etc/hosts
    orchestrator.inject_hostnames(hosts)
    for i in seeds+nodes+clients:
        i.inject_hostnames(hosts)
    seeds[0].run_command("service ganglia-monitor restart; service gmetad restart", silent=True)
    orchestrator.run_command("service ganglia-monitor restart; service gmetad restart", silent=True)


def find_orchestrator():
    """
    Uses the firs VM whose name includes 'orchestrator' as an orchestrator for the cluster
    :return:
    """
    vms = get_all_vms()
    for vm in vms:
        if "orchestrator" in vm.name:
            global orchestrator
            orchestrator = Node(vm=vm)
            return


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
        n.inject_hostnames(get_hosts(private=True))
        n.bootstrap()
        log.info("Node %s is live " % new_guy.name)
    #inform all
    inject_hosts_files()


def remove_nodes(count=1):
    """
    Removes a node from the cassandra cluster. Refreshes the hosts in all nodes
    :return:
    """
    action = env_vars['decommission_action']
    for i in range(count):
        dead_guy = nodes.pop()
        log.info("Removing node %s" % dead_guy.name)
        dead_guy.decommission()
        if action == "KEEP":
            stash[:] = [dead_guy] + stash
        log.info("Node %s is removed" % dead_guy.name)
        save_cluster()
    inject_hosts_files()


def run_load_phase(record_count):
    """
    Runs the load phase on all the cluster clients with the right starting entry, count on each one
    :param record_count:
    """
    #first inject the hosts file
    host_text = ""
    for h in seeds+nodes: host_text += h.get_private_addr()+"\n"
    start = 0
    step = record_count/len(clients)
    for c in clients:
        load_command = "echo '%s' > /opt/hosts;" % host_text
        load_command += get_script_text("ycsb", "load") % (str(record_count), str(step), str(start), c.name[-1:])
        log.info("running load phase on %s" % c.name)
        c.run_command(load_command, silent=True)
        start += step


def run_sinusoid(target_total, offset_total, period):
    """
    Runs a sinusoidal workload on all the Client nodes of the cluster
    :param target_total: Total target ops/sec for all the cluster
    :param offset_total: total offset
    :param period: Period of the sinusoid
    """
    target = target_total / len(clients)
    offset = offset_total / len(clients)
    #first inject the hosts file
    host_text = ""
    for h in seeds+nodes: host_text += h.get_private_addr()+"\n"
    start = 0
    for c in clients:
        load_command = "echo '%s' > /opt/hosts;" % host_text
        load_command += get_script_text("ycsb", "run_sin") % (target, offset, period, c.name[-1:])
        log.info("running workload on %s" % c.name)
        c.run_command(load_command, silent=True)


def destroy_all():
    """
    Destroys all the VMs in the cluster (not the orchestrator)
    """
    log.info("Destroying the %s cluster" % cluster_name)
    for n in seeds+nodes+clients+stash:
        n.destroy()
    remove(save_file)


def get_hosts(include_clients=False, string=False, private=False):
    """
    Produces a mapping of hostname-->IP for the nodes in the cluster
    :param include_clients: if False (default) the clients are not included
    :param string: if True the output is a string able to be appended in /etc/hosts
    :return: a dict or a string of hostnames-->IPs
    """
    hosts = dict()
    all_nodes = seeds + nodes
    if include_clients:
        all_nodes += clients
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
    for c in clients:
        if c.name != "cassandra_client_1":
            continue
        return c.get_public_addr()


#=============================== MAIN ==========================


################ INIT actions ###########
find_orchestrator()
resume_cluster()
########################################



