### RUN THIS FROM PYTHON ONLY, SPECIFYING THE FOLLOWING PARAMS
count=%s
step=%s
start=%s
client_no=%s

function load(){
	/etc/YCSB/bin/ycsb load cassandra-cql \
		-P /etc/YCSB/workloads/workloada -p port=9042 \
		-threads 20 -s \
		-p hostsFile=/opt/hosts \
		-p recordcount=$count -p insertcount=$step -p insertstart=$start \
		-p clientno=$client_no\
		&> /root/ycsb_load.log
	echo "

==============  DONE  =====================" >> ycsb_load.log
}

load &

