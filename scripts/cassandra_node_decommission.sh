#!/bin/sh
#nodetool repair -h 127.0.0.1 ycsb
nodetool decommission
#kill cassandra
CAS_PID=$(jps | grep CassandraDaemon | awk  '{print $1}')
echo "CTOOL: Killing CassandraDaemon ($CAS_PID)"
kill $CAS_PID &>/dev/null


#report not alive
gmetric -n alive -v 0 -t int32 -u nodes -d 10000