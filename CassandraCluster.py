__author__ = 'cmantas'
from CassandraNode import CassandraNode as Node, get_script_text
from CassandraNode import get_all_nodes
from VM import Timer, get_all_vms
from time import sleep
from json import loads, dumps
from os import remove
from os.path import isfile

orchestrator = None

seeds = []      # the seed node(s) of the casssandra cluster !!! ONLY ONE IS SUPPORTED !!!
nodes = []      # the rest of the nodes of the Cassandra cluster
clients = []    # the clients of the cluster
stash = []

seed_name = "cassandra_seednode"
node_name = "cassandra_node_"
client_name = "cassandra_client_"

save_file = "files/saved_cluster.json"


def create_cluster(worker_count=0, client_count=0):
    """
    Creates a Cassandra Cluster with a single Seed Node and 'worker_count' other nodes
    :param worker_count: the number of the nodes to create-apart from the seednode
    """
    #create the seed node
    seeds.append(Node(seed_name, node_type="SEED", create=True))
    #create the rest of the nodes
    for i in range(worker_count):
        name = node_name+str(len(nodes)+1)
        nodes.append(Node(name, create=True))
    for i in range(client_count):
        name = client_name+str(len(clients)+1)
        clients.append(Node(name, node_type="CLIENT", create=True))
    #wait until everybody is ready
    wait_everybody()
    inject_hosts_files()
    print "CLUSTER: Every node is ready for SSH"
    save_cluster()


def wait_everybody():
    for i in seeds + nodes + clients:
        i.vm.wait_ready()


def bootstrap_cluster():
    """ Runs the necessary boostrap commnands to each of the Seed Node and the other nodes  """
    print "CLUSTER: Running bootstrap scripts"
    #bootstrap the seed node
    seeds[0].bootstrap()
    #bootstrap the rest of the nodes
    for n in nodes+clients:
        n.bootstrap(params={"seednode": seeds[0].vm.get_private_addr()})
    print "CLUSTER: READY!!"


def resume_cluster():
    """
    Re-Creates the cluster representation based on the VMs that already exist on the IaaS
    :param worker_count the number of the nodes to include in the cluster
    """
    find_orhcestrator()
    if not isfile(save_file):
        print "CLUSTER: No existing created cluster"
        return
    saved_cluster = loads(open(save_file, 'r').read())
    saved_nodes = saved_cluster['nodes']
    nodes[:] = []
    seeds[:] = []
    in_seeds, in_nodes, in_clients = get_all_nodes(check_active=True)
    #check that all saved nodes actually exist and exit if not\
    for n in saved_nodes:
        if n not in [i.name for i in in_nodes]:
            print "CLUSTER: ERROR, node %s does actually exist in the cloud, re-create the cluster" % n
            remove(save_file)
            exit(-1)
    for n in in_nodes:
        if n.name not in saved_nodes: in_nodes.remove(n)
    nodes.extend(in_nodes)
    seeds.extend(in_seeds)
    clients.extend(in_clients)


def save_cluster():
    cluster = dict()
    cluster["seeds"] = [s.name for s in seeds]
    cluster["nodes"] = [n.name for n in nodes]
    cluster["clients"] = [c.name for c in clients]
    cluster['note'] = "only the nodes are acually used"
    string = dumps(cluster, indent=3)
    f = open(save_file, 'w+')
    f.write(string)


def kill_clients():
    print "CLUSTER: Killing clients"
    for c in clients: c.kill()


def kill_nodes():
    print "CLUSTER: Killing cassandra nodes"
    for n in seeds+nodes+stash:
        n.kill()


def kill_all():
    # kill 'em all
    kill_clients()
    kill_nodes()


def inject_hosts_files():
    print "CLUSTER: Injectin host files"
    hosts = dict()
    for i in seeds+nodes + clients:
        hosts[i.name] = i.vm.get_private_addr()

    #add the host names to etc/hosts
    orchestrator.inject_hostnames(hosts)
    for i in seeds+nodes+clients:
        i.vm.inject_hostnames(hosts)
    seeds[0].vm.run_command("service ganglia-monitor restart")
    orchestrator.run_command("service ganglia-monitor restart")


def find_orhcestrator():
    vms = get_all_vms()
    for vm in vms:
        if "orchestrator" in vm.name:
            global orchestrator
            orchestrator = vm
            return


def add_node():
    name = node_name+str(len(nodes)+1)
    print "CLUSTER: Adding node %s" % name
    if not len(stash) == 0:
        new_guy = stash[0]
        del stash[0]
    else:
        new_guy = Node(name, create=True)
    nodes.append(new_guy)
    new_guy.vm.wait_ready()
    #inject host files to everybody
    inject_hosts_files()
    new_guy.bootstrap()
    print "CLUSTER: Node %s is live " % (name)
    save_cluster()


def remove_node():
    dead_guy = nodes[-1]
    print "CLUSTER: Removing node %s" % dead_guy
    dead_guy.decommission()
    stash[:] = [nodes.pop()] + stash
    print "CLUSTER: Node %s is removed" % dead_guy
    save_cluster()


def run_load_phase(record_count):
    #first inject the hosts file
    host_text = ""
    for h in seeds+nodes: host_text += h.vm.get_private_addr()+"\n"
    start = 0
    step = record_count/len(clients)
    for c in clients:
        load_command = "echo '%s' > /opt/hosts;" % host_text
        load_command += get_script_text("ycsb_load") % (str(record_count), str(step), str(start), c.name[-1:])
        print "CLUSTER: running load phase on %s" % c.name
        c.vm.run_command(load_command, silent=True)
        start += step


def run_sinusoid(target_total, offset_total, period):
    target = target_total / len(clients)
    offset = offset_total / len(clients)
    #first inject the hosts file
    host_text = ""
    for h in seeds+nodes: host_text += h.vm.get_private_addr()+"\n"
    start = 0
    for c in clients:
        load_command = "echo '%s' > /opt/hosts;" % host_text
        load_command += get_script_text("ycsb_run_sin") % (target, offset, period, c.name[-1:])
        print "CLUSTER: running workload on %s" % c.name
        c.vm.run_command(load_command, silent=True)


def destroy_all():
    for n in seeds+nodes+stash+clients:
        n.vm.destroy()
    remove(save_file)

def cluster_info():
    """
    returns the available nodes and their addresses
    :return:
    """
    rv = orchestrator.name+ "\t:\t"+orchestrator.get_public_addr()+ "\t,\t"+ orchestrator.get_private_addr()+ "\n"
    for n  in seeds+nodes+clients:
        rv += n.name+ "\t:\t"+n.vm.get_public_addr()+"\t,\t"+n.vm.get_private_addr()+ "\n"
    return rv


#=============================== MAIN ==========================



#create_cluster(worker_count=1, client_count=2)

#resume active cluster
resume_cluster()
#kill all previous processes
# kill_all()
# #bootstrap cluster from scratch
# bootstrap_cluster()
# run_load_phase(100000)
# print "waiting 20 seconds for load phase to finish"
# sleep(20)
# run_sinusoid(target_total=200, offset_total=100, period=60)
# print "waiting to add node"
# sleep(30)
# add_node()
# print "waiting to remove node"
# sleep(30)
# remove_node()
#
# print "FINISED (%d seconds)" % timer.stop()


