#!/bin/sh
### RUN THIS FROM PYTHON ONLY, SPECIFYING THE FOLLOWING PARAMS
count=%s
step=%s
start=%s
killall java
	/etc/YCSB/bin/ycsb load cassandra-cql \
		-P /etc/YCSB/workloads/workloada -p port=9042 \
		-threads 100 -s \
		-p hostsFile=/opt/hosts \
		-p recordcount=$count -p insertcount=$step -p insertstart=$start \
		-p opTimeout=30000\
		&> /root/ycsb_load.log

