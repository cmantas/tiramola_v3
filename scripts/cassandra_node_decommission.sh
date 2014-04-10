#!/bin/sh
nodetool repair -h 127.0.0.1 ycsb
nodetool decommission
#kill cassandra
CAS_PID=$(jps | grep CassandraDaemon | awk  '{print $1}')
echo "CTOOL: Killing CassandraDaemon ($CAS_PID)" >> ctool.log
kill $CAS_PID &>/dev/null
