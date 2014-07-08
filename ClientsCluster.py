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

orchestrator = None     # the VM to which the others report to

all_nodes = []            # the clients of the cluster

# the name of the cluster is used as a prefix for the VM names
cluster_name = "clients"
node_type = "client"

# the save file for saving/reloading the active cluster
save_file = "files/saved_%s_cluster.json" % cluster_name

# the flavor and image for this cluster's VMs
flavor = env_vars["client_flavor"]
image = env_vars["cassandra_base_image"]

# the logger for this file
log = get_logger('CLIENTS', 'INFO', logfile='files/logs/Coordinator.log')


def wait_everybody():
    """
    Waits for all the Nodes in the cluster to be SSH-able
    """
    log.info('Waiting for SSH on all nodes')
    for i in all_nodes:
        i.wait_ready()


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
        saved_nodes = []
    else:
        saved_cluster = loads(open(save_file, 'r').read())
        saved_nodes = saved_cluster['clients']

    in_nodes = Node.get_all_nodes(check_active=True)
    for n in in_nodes:
        if n.name not in saved_nodes:
            if "orchestrator" in n.name:
                global orchestrator
                orchestrator = n
                log.debug('Found orchestrator %s' % n.name)
            continue
        else:
            all_nodes.append(n)
    #sort nodes by name
    all_nodes.sort(key=lambda x: x.name)


def save_cluster():
    """
    Creates/Saves the 'save_file'
    :return:
    """
    cluster = dict()
    cluster["clients"] = [c.name for c in all_nodes]
    string = dumps(cluster, indent=3)
    f = open(save_file, 'w+')
    f.write(string)


def create_cluster(count=1):
    global all_nodes
    all_nodes = []
    for i in range(count):
        all_nodes.append(Node(cluster_name, node_type="client", number="%02d" % (i+1), create=True, IPv4=True,
                            flavor=flavor, image=image))

    #save the cluster to file
    save_cluster()
    #wait until everybody is ready
    wait_everybody()
    find_orchestrator()
    inject_hosts_files()
    log.info('Every node is ready for SSH')


def inject_hosts_files():
    """
    Creates a mapping of hostname -> IP for all the nodes in the cluster and injects it to all Nodes so that they
    know each other by hostname. Also restarts the ganglia daemons
    :return:
    """
    log.info("Injecting host files")
    hosts = dict()
    for i in all_nodes:
        hosts[i.name] = i.get_public_addr()
    #add the host names to etc/hosts
    orchestrator.inject_hostnames(hosts, delete=cluster_name)
    for i in all_nodes:
        i.inject_hostnames(hosts, delete=cluster_name)
    all_nodes[0].run_command("service ganglia-monitor restart; service gmetad restart", silent=True)
    orchestrator.run_command("service ganglia-monitor restart; service gmetad restart", silent=True)


def bootstrap_cluster():
    """
    Runs the necessary boostrap commnands to each of the Seed Node and the other nodes
    """
    for n in all_nodes:
        n.bootstrap()
    inject_hosts_files()


def kill_nodes():
    """
    Runs the kill scripts for all the nodes in the cluster
    """
    log.info("Killing client nodes")
    for n in all_nodes:
        n.kill()


def add_nodes(count=1):
    """
    Adds a node to the cassandra cluster. Refreshes the hosts in all nodes
    :return:
    """
    log.info('Adding %d nodes' % count)
    new_nodes = []
    Node.flavor = env_vars['client_flavor']
    for i in range(count):
        #check if cluster did not previously exist
        if i == 0 and len(all_nodes) == 0:
            # give a floating IPv4 to the first node only
            new_guy = Node(cluster_name, '', len(all_nodes)+1, create=True,  IPv4=True)
        else:
            new_guy = Node(cluster_name, node_type="", number=len(all_nodes)+1, create=True)
        all_nodes.append(new_guy)
        new_nodes.append(new_guy)
        save_cluster()
    for n in new_nodes:
        n.wait_ready()
        #inject host files to everybody
        n.inject_hostnames(get_hosts(private=True), delete=cluster_name)
        n.bootstrap()
        log.info("Node %s is live " % new_guy.name)
    #inform all
    inject_hosts_files()


def remove_nodes(count=1):
    """
    Removes a node from the cassandra cluster. Refreshes the hosts in all nodes
    :return:
    """
    for i in range(count):
        dead_guy = all_nodes.pop()
        log.info("Removing node %s" % dead_guy.name)
        dead_guy.decommission()
        log.info("Client %s is removed" % dead_guy.name)
        save_cluster()
    inject_hosts_files()


def update_hostfiles(servers):
    log.info("updating hostfiles")
    # generate ycsb-specific hosts file text
    host_text = ""
    del servers["cassandra_seednode"]

    #generate the "hosts" text for YCSB
    for key, value in servers.iteritems(): host_text += value+"\n"
    host_text = host_text[:-1]  # remove trailing EOL
    command = "echo '%s' > /opt/hosts;" % host_text
    for c in all_nodes:
        c.run_command(command, silent=True)


def run(params):

    bootstrap_cluster()

    run_type = params['type']

    # generate ycsb-specific hosts file text
    host_text = ""
    servers = params['servers']
    update_hostfiles(servers)

    #choose type of run and do necessary actions
    if run_type=='stress':
        for c in all_nodes:
            load_command = get_script_text(cluster_name, node_type, "run")
            log.info("running stress workload on %s" % c.name)
            c.run_command(load_command, silent=True)
    elif run_type == 'sinusoid':
        global env_vars
        target = int(params['target']) / len(all_nodes)
        offset = int(params['offset']) / len(all_nodes)
        period = int(params['period'])
        threads = int(env_vars['client_threads'])
        for c in all_nodes:
            load_command = "echo '%s' > /opt/hosts;" % host_text
            load_command += get_script_text(cluster_name, node_type, "run_sin") % (target, offset, period, threads)
            #load_command += get_script_text(cluster_name, "", "run_sin") % (target, offset, period)
            log.info("running sinusoid on %s" % c.name)
            c.run_command(load_command, silent=True)
    elif run_type == 'load':
        record_count = int(params['records'])
        start = 0
        step = record_count/len(all_nodes)
        threads = []
        for c in all_nodes:
            load_command = "echo '%s' > /opt/hosts;" % host_text
            load_command += get_script_text(cluster_name, node_type, "load") % (str(record_count), str(step), str(start))
            #load_command += get_script_text(cluster_name, "", "load") % (str(record_count), str(step), str(start))
            log.info("running load phase on %s" % c.name)
            t = Thread(target=c.run_command, args=(load_command,) )
            threads.append(t)
            t.start()
            start += step
        log.info("waiting for load phase to finish in clients")
        for t in threads:
            t.join()


def destroy_all():
    """
    Destroys all the VMs in the cluster (not the orchestrator)
    """
    log.info("Destroying the %s cluster" % cluster_name)
    for n in all_nodes:
        n.destroy()
    remove(save_file)


def get_hosts(string=False, private=False):
    """
    Produces a mapping of hostname-->IP for the nodes in the cluster
    :param include_clients: if False (default) the clients are not included
    :param string: if True the output is a string able to be appended in /etc/hosts
    :return: a dict or a string of hostnames-->IPs
    """
    hosts = dict()
    for i in all_nodes:
        if private:
            hosts[i.name] = i.get_private_addr()
        else:
            hosts[i.name] = i.get_public_addr()
    return hosts


def node_count():
    return len(all_nodes)


def exists():
    if len(all_nodes) == 0:
        return False
    else:
        return True


def get_monitoring_endpoint():
    """
    returns the IP of the node that has the monitoring data we want
    """
    return all_nodes[0].get_public_addr()



# always runs
resume_cluster()

if __name__ == "__main__":
    # add_nodes()
    remove_nodes(1)

