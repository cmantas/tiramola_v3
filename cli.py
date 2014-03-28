__author__ = 'cmantas'
import sys
from CassandraCluster import *

args = sys.argv


if args[1] == "load_data":
    record_count = int(args[2])
    print "CLI: Loading %d records in the cluster" % record_count
    run_load_phase(record_count)
elif args[1] == "run_sinusoid":
    args = args[2:]
    for i in range(len(args)):
        if args[i] == "target":
            target = int(args[i+1])
            i += 1
        elif args[i] == "period":
            period = int(args[i+1])
            i += 1
        elif args[i] == "offset":
            offset = int(args[i+1])
            i += 1
    print "CLI: running sinusoid for target=%d, offset=%d, period=%d" % (target, offset, period)
    run_sinusoid(target, offset, period)
elif args[1] == "create_cluster":
    args = args[2:]
    for i in range(len(args)):
        if args[i] == "nodes":
            nodes = int(args[i+1])
            i += 1
        elif args[i] == "clients":
            clients = int(args[i+1])
            i += 1
    print "CLI: creating cluster with %d nodes and %d clients" % (nodes, clients)
    create_cluster(nodes-1, clients)
elif args[1] == "kill_workload":
    kill_clients()
elif args[1] == "kill_nodes":
    kill_nodes()
elif args[1] == "cluster":
    print "\n\n===================================   CLUSTER   ============================================\n"
    print cluster_info()
elif args[1] == "bootstrap_cluster":
    bootstrap_cluster()
elif args[1] == "destroy_all":
    destroy_all()
else:
    print """==============   USAGE   ==================
tiramola cluster  (lists all the nodes)
tiramola create_cluster nodes 2 clients 2
tiramola bootstrap_cluster
tiramola load_data 100000
tiramola run_sinusoid target 100 offset 80 period 60
tiramola kill_workload
tiramola destroy all"""
