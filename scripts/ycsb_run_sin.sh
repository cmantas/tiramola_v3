#########  YCSB WORKLOAD PARAMS  ########
target=%s
offset=%s
period=%s
clientNo=%s
threads=40

ycsb run cassandra-cql \
	-P /etc/YCSB/workloads/workloada\
        -threads $threads -p maxexecutiontime=1000000000 -p hostsFile=/opt/hosts -p operationcount=1000000000 \
        -p recordcount=10000 \
        -p target=$target \
        -p sinusoidal=true \
        -p period=$period \
        -p offset=$offset -s \
	-p clientno=$clientNo \
        &> /root/ycsb_run.log &

