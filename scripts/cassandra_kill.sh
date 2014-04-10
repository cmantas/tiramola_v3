CAS_PID=$(jps | grep CassandraDaemon | awk  '{print $1}')
echo "CTOOL: Killing CassandraDaemon ($CAS_PID)"
kill -9 $CAS_PID &>/dev/null
## maybe problematic
killall java



################ debug #################3
echo "Removing cassandra files and logs" &>>ctool.log
#cleaning cassandra files
rm -rf /var/lib/cassandra/* &>>ctool.log
rm /var/log/cassandra/system.log &>>ctool.log
#cleaning ctool rrds
echo "Removing ganglia rrds" &>>ctool.log
rm -rf /var/lib/ganglia/rrds/* &>>ctool.log





echo '

############  KILLED  ##############' >> ycsb_run.log
