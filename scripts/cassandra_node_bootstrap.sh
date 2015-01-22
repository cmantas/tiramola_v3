#!/bin/bash

MAX_WAIT=100  #5 min
READ_TIMEOUT=500 #ms

echo "started bootstrap" > bootsrap.log

# check the seednode
    if ! ping -q -c 1 cassandra_seednode &>/dev/null   ;
    then
         echo CTOOL: ERROR - cassandra_seednode not pingable, exiting
        exit -1
    fi

# kill the cassandra process
	CAS_PID=$(jps | grep CassandraDaemon | awk  '{print $1}')
	echo "CTOOL: Killing CassandraDaemon ($CAS_PID)"
	kill $CAS_PID

# clean previous files and logs
	echo "Removing cassandra files and logs"
	#cleaning cassandra files
	rm -rf /var/lib/cassandra/*
	rm /var/log/cassandra/system.log
	#cleaning ganglia rrds
	echo "Removing ganglia rrds"
	rm -rf /var/lib/ganglia/rrds/*


# find my IP
    my_priv_addr=""
    #look for an IPv4 interface in range 10.0 and use that for the cassandra communication
    line=$(ifconfig eth2 | grep "inet addr:")
    line=$(echo $line | awk '{print $2}')
    address=$(echo $line | sed 's/addr://g')
    my_priv_addr=$address
    echo $my_priv_addr
    


# configure cassandra
		################### ADDRESSES ###################
    echo "configuring cassandra.yaml for my address:$my_priv_addr" >> ctool.log
    #change the listen address of this node
    sed -i "s/listen_address: .*/listen_address: $my_priv_addr/g"  /etc/cassandra/cassandra.yaml
    #change the rpc_address (for clients) of this node to 0.0.0.0 (all)
    sed -i "s/rpc_address: .*/rpc_address: 0.0.0.0/g"  /etc/cassandra/cassandra.yaml
    #change the seeds to "cassandra_seednode"
    sed -i "s/seeds: .*/seeds: \"cassandra_seednode\"/g" /etc/cassandra/cassandra.yaml
    #change the rpc address that other nodes can reach you to
		sed -i "s/.*broadcast_rpc_address: .*/broadcast_rpc_address: $my_priv_addr/g"  /etc/cassandra/cassandra.yaml

		##################### cassandra env ##############################
		#disable consistent range movement
		sed -i "/Dconsistent.rangemovement/d" /etc/cassandra/cassandra-env.sh
		echo 'JVM_OPTS="$JVM_OPTS -Dconsistent.rangemovement=false' >> /etc/cassandra/cassandra-env.sh
    #add the jmx server whatever to cassandra-env.sh
    sed -i.bak "s/.*-Djava.rmi.server.hostname=.*/JVM_OPTS=\"\$JVM_OPTS -Djava.rmi.server.hostname=$my_priv_addr\"/g"  /etc/cassandra/cassandra-env.sh
    sed -i.bak "s/*JVM_OPTS=\"\$JVM_OPTS -Djava.rmi.server.hostname=*\"/JVM_OPTS=\"\$JVM_OPTS -Djava.rmi.server.hostname=$my_priv_addr\"/g"  /etc/cassandra/cassandra-env.sh
    #make sure no requests are dropped by using a big timeout
    sed -i "s/read_request_timeout_in_ms:.*/read_request_timeout_in_ms: $READ_TIMEOUT/g" /etc/cassandra/cassandra.yaml
    sed -i "s/write_request_timeout_in_ms:.*/write_request_timeout_in_ms: 30000/g" /etc/cassandra/cassandra.yaml
    #outbound stream traffic
    sed -i "s/.*stream_throughput_outbound_megabits_per_sec:.*/stream_throughput_outbound_megabits_per_sec: 600/g" /etc/cassandra/cassandra.yaml
    #no compression
		sed -i "s/.*internode_compression:.*/internode_compression: none/g" /etc/cassandra/cassandra.yaml

		# TODO maybe not applicable for cassandra 2.1
		#cache on flush
		sed -i "s/.*populate_io_cache_on_flush:.*/populate_io_cache_on_flush: true/g" /etc/cassandra/cassandra.yaml

		#row cache
		sed -i "s/.*row_cache_size_in_mb:.*/row_cache_size_in_mb: 256/g" /etc/cassandra/cassandra.yaml


    #increase the num of tokens
    sed -i "s/num_tokens:.*/num_tokens: 256/g" /etc/cassandra/cassandra.yaml
    echo "CTOOL: Done configuring"


# start cassandra
	chmod -R o+rw /var/lib/cassandra
	echo "Starting casandra service, ganglia-monitor"
	service cassandra start
#(re)start ganglia-monitor
	service ganglia-monitor restart

#wait until ready and try to create keyspace
    echo "Attempting to create ycsb keyspace"
    echo "create keyspace ycsb  WITH REPLICATION = {'class' : 'SimpleStrategy', 'replication_factor': 1 }; use ycsb;  create table usertable (y_id varchar primary key, field0 varchar, field1 varchar, field2 varchar, field3 varchar, field4 varchar, field5 varchar, field6 varchar, field7 varchar, field8 varchar, field9 varchar);" > ycsb_cql.temp
    while ! cqlsh < ycsb_cql.temp 2>/dev/null;do sleep 2; done
    rm ycsb_cql.temp

echo "ended bootstrap" >> bootsrap.log

#report alive in gmetric
gmetric -n alive -v 1 -t int32 -u nodes -d 10000

