sed -i 's/host = .*/host = clients__1/g' /etc/ganglia/gmond.conf
sed -i 's/name = \"cassandra\"/name = \"clients\"/g' /etc/ganglia/gmond.conf
service ganglia-monitor restart;
