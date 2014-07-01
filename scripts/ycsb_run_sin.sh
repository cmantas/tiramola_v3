#!/bin/sh
#########  YCSB WORKLOAD PARAMS  ########
target=%s
offset=%s
period=%s
threads=200

killall java

echo "
period=$period
target=$target
offset=$offset
recordcount=1000
workload=com.yahoo.ycsb.workloads.CoreWorkload
sinusoidal=true
readallfields=true

readproportion=1
updateproportion=0
scanproportion=0
insertproportion=0

requestdistribution=uniform
hostsFile=/opt/hosts
maxexecutiontime=1000000000
" > my_workload

#keep old run file
mv ycsb_run.log "$(date)_ycsb_run.log"

/etc/YCSB/bin/ycsb run cassandra-cql -P my_workload -threads $threads  -s &> /root/ycsb_run.log &

