#########  YCSB WORKLOAD PARAMS  ########
target=%s
offset=%s
period=%s
threads=200

echo "
period=$period
target=$target
offset=$offset
recordcount=100
operationcount=10000000
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

ycsb run cassandra-cql -P my_workload -threads $threads  -s &> /root/ycsb_run.log &

