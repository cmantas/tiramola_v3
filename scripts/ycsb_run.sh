#########  YCSB WORKLOAD PARAMS  ########
target=100
offset=0
threads=40
clientNo=%s

ycsb run cassandra-cql \
	-P /etc/YCSB/workloads/workloada\
        -threads $threads -p maxexecutiontime=1000000000 -p hostsFile=/opt/hosts -p operationcount=1000000000 \
        -p recordcount=10000 \
        -p target=$target \
        -p period=60 \
        -p offset=$offset -s \
	-p clientno=$clientNo \
        &> /root/ycsb_run.log &

