#!/bin/bash

MAX_WAIT=300  #5 min

###### check for root privileges ##########
if [ "$(id -u)" != "0" ]; then echo "This script must be run as root" 1>&2;exit 1;fi


function usage(){
	echo "usage: start | clean | clean_start | full_start | status | configure | wait_ready | wait_infinite"
	
}

function check_seed(){

	if ! ping -q -c 1 cassandra_seednode &>/dev/null   ;
	then	
		 echo CTOOL: ERROR - cassandra_seednode not pingable, exiting &>>ctool.log
		exit -1 
	fi
}

function be_seed(){
	#change the gmond.conf file
	echo "Changing the gmond.conf file" &>>ctool.log	 
	sed -i.bak "s/deaf = yes/deaf = no/g" /etc/ganglia/gmond.conf
	my_priv_addr=$(my_ip)
	echo "my address is $my_priv_addr" &>>ctool.log
	configure $my_priv_addr
	echo "(Re)starting Ganglia, gmetad, apache" &>>ctool.log
	service ganglia-monitor restart    &>>ctool.log
	service gmetad restart    &>>ctool.log
	service apache2 restart    &>>ctool.log
}

function my_ip(){
	#look for an IPv4 interface in range 10.0 and use that for the cassandra communication
	let if_count=($(ifconfig | grep eth | wc -l ))-1
	for i in $(seq 0 $if_count)
	do	#look for IPv4 address
		line=$(ifconfig eth$i | grep "inet addr:")
		line=$(echo $line | awk '{print $2}')
		address=$(echo $line | sed 's/addr://g')
		if [[ "$address" == 10.0.* ]] ;
		then 
			my_priv_addr=$address
			echo $my_priv_addr
			break
		fi 

	done
}

function status(){
	jout=$(jps|grep CassandraDaemon)
	if [[ "$jout" != *CassandraDaemon* ]] ;
	then
		echo "not_ready" &>>ctool.log
		return
	fi
	if grep -q "Startup completed! Now serving reads." /var/log/cassandra/system.log;
	then
		echo "ready"  &>>ctool.log
		return
	else
		echo  "not_ready" &>>ctool.log
	fi 
}

function wait_ready(){
	if [ $(status) != "ready" ]; then 
		while [ $(status) != "ready" ]
		do
			sleep 5
		done
	fi
}

function configure(){

	my_priv_addr=$(my_ip)
	echo "configuring cassandra.yaml for my address:$my_priv_addr" >> ctool.log
	#change the listen address of this node
	sed "s/listen_address: .*/listen_address: $my_priv_addr/g"  /etc/cassandra/cassandra.yaml> tmp && mv tmp /etc/cassandra/cassandra.yaml
	#change the rpc_address of this node to 0.0.0.0
	sed "s/rpc_address: .*/rpc_address: 0.0.0.0/g"  /etc/cassandra/cassandra.yaml> tmp && mv tmp /etc/cassandra/cassandra.yaml
	#change the seeds to "cassandra_seednode" 
	sed "s/seeds: .*/seeds: \"cassandra_seednode\"/g"  /etc/cassandra/cassandra.yaml> tmp && mv tmp /etc/cassandra/cassandra.yaml
	check_seed
	#add the jmx server whatever to cassandra-env.sh
	sed -i.bak "s/.*-Djava.rmi.server.hostname=.*/JVM_OPTS=\"\$JVM_OPTS -Djava.rmi.server.hostname=$my_priv_addr\"/g"  /etc/cassandra/cassandra-env.sh
        sed -i.bak "s/*JVM_OPTS=\"\$JVM_OPTS -Djava.rmi.server.hostname=*\"/JVM_OPTS=\"\$JVM_OPTS -Djava.rmi.server.hostname=$my_priv_addr\"/g"  /etc/cassandra/cassandra-env.sh
        #make sure no requests are dropped by using a big timeout       
        sed -i.bak "s/read_request_timeout_in_ms:.*/read_request_timeout_in_ms: 50000/g" /etc/cassandra/cassandra.yaml
        sed -i.bak "s/write_request_timeout_in_ms:.*/write_request_timeout_in_ms: 50000/g" /etc/cassandra/cassandra.yaml
	echo "CTOOL: Done configuring" &>>ctool.log
}

function clean(){
	kill_it
	echo "Removing cassandra files and logs" &>>ctool.log
	#cleaning cassandra files
	rm -rf /var/lib/cassandra/* &>>ctool.log
	rm /var/log/cassandra/system.log &>>ctool.log
	#cleaning ctool rrds
	echo "Removing ganglia rrds" &>>ctool.log
	rm -rf /var/lib/ganglia/rrds/* &>>ctool.log
}

function c_start(){
	if jps |grep CassandraDaemon ;
	then 
		echo Cassandra process already running, status: $(status) &>>ctool.log
		exit
	fi

	if [  "$1" ];
	then
		#delete both log and data files
		clean
	else
		#only delete any previous log files
		echo "deleting previous log files"
		rm /var/log/cassandra/system.log &>>ctool.log
	fi
	chmod -R o+rw /var/lib/cassandra
	check_seed
	echo Starting casandra service, ganglia-monitor &>>ctool.log
	service cassandra start
	service ganglia-monitor restart &>>ctool.
}

function kill_it(){
	CAS_PID=$(jps | grep CassandraDaemon | awk  '{print $1}')
	echo "CTOOL: Killing CassandraDaemon ($CAS_PID)" &>>ctool.log
	kill -9 $CAS_PID &>>ctool.log
}

#configure
configure 
#clean start
c_start 1
#wait ready for a timout
timeout $MAX_WAIT $0 wait_infinite
echo "creating ycsb keyspace"
echo "create keyspace ycsb  WITH REPLICATION = {'class' : 'SimpleStrategy', 'replication_factor': 1 }; use ycsb;  create table usertable (y_id varchar primary key, field0 varchar, field1 varchar, field2 varchar, field3 varchar, field4 varchar, field5 varchar, field6 varchar, field7 varchar, field8 varchar, field9 varchar);" > ycsb_cql.temp
while ! cqlsh < ycsb_cql.temp 2>/dev/null;do sleep 2; done	
rm ycsb_cql.temp
;;	


