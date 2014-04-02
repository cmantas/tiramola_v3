CAS_PID=$(jps | grep CassandraDaemon | awk  '{print $1}')
echo "CTOOL: Killing CassandraDaemon ($CAS_PID)"
kill -9 $CAS_PID &>/dev/null
## maybe problematic
killall java
echo '\n\n############  KILLED  ##############' >> ycsb_run.log
